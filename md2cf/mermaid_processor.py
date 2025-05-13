import hashlib
import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

CACHE_DIR = Path(".cache/md2cf_mermaid")


def check_mmdc() -> bool:
    if shutil.which("mmdc") is None:
        return False
    return True


def contains_mermaid(content: str) -> bool:
    return "```mermaid" in content


def run_mmdc(input_path: Path, output_md_path: Path, output_img_dir: Path) -> bool:
    abs_input_path = input_path.resolve()
    abs_output_md_path = output_md_path.resolve()

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
        subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            cwd=abs_input_path.parent,
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError, Exception):
        return False


def find_attachments(output_img_dir: Path) -> List[Path]:
    attachments = []
    abs_output_img_dir = output_img_dir.resolve()
    if abs_output_img_dir.exists() and abs_output_img_dir.is_dir():
        for item in abs_output_img_dir.iterdir():
            if item.is_file() and item.suffix.lower() == ".png":
                attachments.append(item.resolve())
    return attachments


def process_file_for_mermaid(
    original_file_path: Path,
) -> Optional[Tuple[Path, List[Path]]]:
    try:
        abs_original_file_path = original_file_path.resolve()
        with open(abs_original_file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None

    if not contains_mermaid(content):
        return None

    if not check_mmdc():
        return None

    try:
        relative_path = abs_original_file_path.relative_to(Path.cwd())
    except ValueError:
        path_hash = hashlib.sha1(str(abs_original_file_path).encode()).hexdigest()[:10]
        relative_path = Path(f"abs_path_hash_{path_hash}") / abs_original_file_path.stem

    cache_subdir = (
        CACHE_DIR
        / relative_path
        / f"{original_file_path.stem}-{hashlib.sha1(str(abs_original_file_path).encode()).hexdigest()[:5]}"
    )

    output_md_path = cache_subdir / original_file_path.name
    output_img_dir = cache_subdir

    try:
        cache_subdir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None

    if run_mmdc(abs_original_file_path, output_md_path, output_img_dir):
        attachments = find_attachments(output_img_dir)
        if not output_md_path.exists():
            return None
        return output_md_path.resolve(), attachments
    else:
        return None
