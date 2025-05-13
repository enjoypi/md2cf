import hashlib
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

# Cache directory for mermaid processing outputs relative to the workspace root
CACHE_DIR = Path(".cache/md2cf_mermaid")

logger = logging.getLogger(__name__)
# Configure basic logging
# Keep basic config simple unless specific needs arise
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def check_mmdc() -> bool:
    """Check if mmdc command exists."""
    if shutil.which("mmdc") is None:
        logger.warning(
            "mmdc command not found. Mermaid diagrams will not be processed. "
            "Install @mermaid-js/mermaid-cli via npm: npm install -g @mermaid-js/mermaid-cli"
        )
        return False
    return True


def contains_mermaid(content: str) -> bool:
    """Check if the markdown content contains mermaid code blocks."""
    # Simple check for ```mermaid opening fence
    return "```mermaid" in content


def run_mmdc(input_path: Path, output_md_path: Path, output_img_dir: Path) -> bool:
    """Run the mmdc command to convert the markdown file."""
    # Ensure paths are absolute for clarity and robustness
    abs_input_path = input_path.resolve()
    abs_output_md_path = output_md_path.resolve()
    # output_img_dir is effectively abs_output_md_path.parent now,
    # as mmdc without -O outputs images to the same dir as the -o file.

    command = [
        "mmdc",
        "-i",
        str(abs_input_path),
        "-o",
        str(abs_output_md_path),
        "--outputFormat",
        "png",
        "--scale",
        "4",
        "--width",
        "1600",
    ]

    try:
        logger.info(
            f"Running mmdc for {abs_input_path} (output to: {abs_output_md_path.parent})"
        )
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            cwd=abs_input_path.parent,  # Run mmdc in the context of the input file's directory
        )
        logger.debug(f"mmdc stdout:\n{result.stdout}")
        logger.debug(f"mmdc stderr:\n{result.stderr}")
        logger.info(f"Successfully processed {abs_input_path} with mmdc.")
        return True
    except FileNotFoundError:
        logger.error(
            "mmdc command not found during execution. Please ensure it is installed and in PATH."
        )
        return False
    except subprocess.CalledProcessError as e:
        logger.error(f"mmdc command failed for {abs_input_path}:")
        logger.error(f"Command: {' '.join(command)}")
        logger.error(f"Return code: {e.returncode}")
        logger.error(f"Stdout: {e.stdout}")
        logger.error(f"Stderr: {e.stderr}")
        return False
    except Exception as e:
        logger.error(
            f"An unexpected error occurred while running mmdc for {abs_input_path}: {e}"
        )
        return False


def find_attachments(output_img_dir: Path) -> List[Path]:
    """Find generated PNG files in the output image directory."""
    # This directory is now the PARENT directory of the output markdown file
    attachments = []
    abs_output_img_dir = output_img_dir.resolve()
    if abs_output_img_dir.exists() and abs_output_img_dir.is_dir():
        for item in abs_output_img_dir.iterdir():
            if item.is_file() and item.suffix.lower() == ".png":
                attachments.append(item.resolve())  # Return absolute paths
    return attachments


def process_file_for_mermaid(
    original_file_path: Path,
) -> Optional[Tuple[Path, List[Path]]]:
    """
    Processes a markdown file for Mermaid diagrams if mmdc is available.

    Reads the file, checks for mermaid content, runs mmdc if found,
    and returns the path to the processed markdown file and a list of
    generated attachment paths (absolute).

    Returns None if no mermaid content is found, mmdc is not available,
    or an error occurs during processing.
    """
    try:
        abs_original_file_path = original_file_path.resolve()
        with open(abs_original_file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        logger.error(f"Error reading file {abs_original_file_path}: {e}")
        return None

    if not contains_mermaid(content):
        logger.debug(f"No mermaid content found in {abs_original_file_path}.")
        return None

    if not check_mmdc():
        # Warning already logged by check_mmdc
        return None

    # Create a unique subdirectory in the cache based on the original file path
    try:
        # Use resolved path relative to CWD for cache structure
        relative_path = abs_original_file_path.relative_to(Path.cwd())
    except ValueError:  # If the file is not under CWD (e.g. absolute path elsewhere)
        # Fallback to using a hash of the full path
        path_hash = hashlib.sha1(str(abs_original_file_path).encode()).hexdigest()[:10]
        # Combine hash with filename stem for better readability in cache
        relative_path = Path(f"abs_path_hash_{path_hash}") / abs_original_file_path.stem

    cache_subdir = (
        CACHE_DIR
        / relative_path
        / f"{original_file_path.stem}-{hashlib.sha1(str(abs_original_file_path).encode()).hexdigest()[:5]}"
    )

    output_md_path = cache_subdir / original_file_path.name
    # Images will be placed directly in cache_subdir by mmdc (either via -O or implicitly)
    output_img_dir = cache_subdir

    try:
        cache_subdir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create cache directory {cache_subdir}: {e}")
        return None

    if run_mmdc(abs_original_file_path, output_md_path, output_img_dir):
        # find_attachments now searches output_img_dir (which is cache_subdir)
        attachments = find_attachments(output_img_dir)
        if not output_md_path.exists():
            logger.error(
                f"mmdc ran successfully but output file {output_md_path} was not created."
            )
            return None
        logger.info(
            f"Mermaid processing successful for {abs_original_file_path}. Output: {output_md_path}, Attachments: {len(attachments)}"
        )
        # Return absolute paths
        return output_md_path.resolve(), attachments
    else:
        logger.warning(
            f"Mermaid processing failed for {abs_original_file_path}. Continuing without conversion."
        )
        # Clean up potentially incomplete cache dir? Maybe not, keep for debugging.
        return None
