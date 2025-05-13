import hashlib
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import chardet
import mistune
import yaml
from yaml.parser import ParserError

from md2cf import mermaid_processor
from md2cf.confluence_renderer import ConfluenceRenderer, RelativeLink
from md2cf.ignored_files import GitRepository


class Page(object):
    def __init__(
        self,
        title: Optional[str],
        body: str,
        content_type: Optional[str] = "page",
        attachments: Optional[List[Path]] = None,
        file_path: Optional[Path] = None,
        page_id: str = None,
        parent_id: str = None,
        parent_title: str = None,
        space: str = None,
        labels: Optional[List[str]] = None,
        relative_links: Optional[List[RelativeLink]] = None,
    ):
        self.title = title
        self.original_title = None
        self.body = body
        self.content_type = content_type
        self.file_path = file_path
        self.attachments = attachments
        if self.attachments is None:
            self.attachments: List[Path] = list()
        self.relative_links = relative_links
        if self.relative_links is None:
            self.relative_links: List[RelativeLink] = list()
        self.page_id = page_id
        self.parent_id = parent_id
        self.parent_title = parent_title
        self.space = space
        self.labels = labels

    def get_content_hash(self):
        return hashlib.sha1(self.body.encode()).hexdigest()

    def __repr__(self):
        return "Page({})".format(
            ", ".join(
                [
                    "{}={}".format(name, repr(value))
                    for name, value in [
                        ["title", self.title],
                        ["file_path", self.file_path],
                        ["page_id", self.page_id],
                        ["parent_id", self.parent_id],
                        ["parent_title", self.parent_title],
                        ["space", self.space],
                        [
                            "body",
                            (
                                f"{self.body[:40]}..."
                                if len(self.body) > 40
                                else self.body
                            ),
                        ],
                    ]
                ]
            )
        )


def find_non_empty_parent_path(
    current_dir: Path, folder_data: Dict[Path, Dict[str, Any]], default: Path
) -> Path:
    for parent in current_dir.parents:
        if parent in folder_data and folder_data[parent]["n_files"]:
            return parent
    return default.absolute()


def get_pages_from_directory(
    file_path: Path,
    collapse_single_pages: bool = False,
    skip_empty: bool = False,
    collapse_empty: bool = False,
    beautify_folders: bool = False,
    use_pages_file: bool = False,
    strip_header: bool = False,
    remove_text_newlines: bool = False,
    use_mdignore: bool = True,
    enable_relative_links: bool = False,
) -> List[Page]:
    """
    Collect a list of markdown files recursively under the file_path directory.

    :param file_path: The starting path from which to search
    :param collapse_single_pages:
    :param skip_empty:
    :param collapse_empty:
    :param beautify_folders:
    :param use_pages_file:
    :param strip_header:
    :param remove_text_newlines:
    :param use_mdignore: Use .mdignore files to skip unwanted markdown in directory
      search
    :param enable_relative_links: extract all relative links and replace them with
      placeholders
    :return: A list of paths to the markdown files to upload.
    """
    processed_pages = list()
    base_path = file_path.resolve()
    folder_data = dict()
    git_repo = GitRepository(file_path, use_mdignore=use_mdignore)

    for current_path, directories, file_names in os.walk(file_path):
        current_path = Path(current_path).resolve()

        if git_repo.is_ignored(current_path):
            continue

        dir_content_file_name = f"_{current_path.name}.md"
        dir_content_page_data: Optional[Page] = None
        dir_content_file_path: Optional[Path] = None

        if dir_content_file_name in file_names:
            dir_content_file_path = current_path / dir_content_file_name
            if not git_repo.is_ignored(dir_content_file_path):
                dir_content_page_data = get_page_data_from_file_path(
                    dir_content_file_path,
                    strip_header=strip_header,
                    remove_text_newlines=remove_text_newlines,
                    enable_relative_links=enable_relative_links,
                )
                dir_content_page_data.file_path = dir_content_file_path

        markdown_files: List[Path] = [
            Path(current_path, file_name)
            for file_name in file_names
            if file_name.lower().endswith(".md")
        ]
        # Filter out ignored files
        markdown_files = [
            path for path in markdown_files if not git_repo.is_ignored(path)
        ]

        if dir_content_file_path and dir_content_file_path in markdown_files:
            markdown_files.remove(dir_content_file_path)

        folder_data[current_path] = {"n_files": len(markdown_files), "title": None}

        # we'll capture title and path of the parent folder for this folder:
        folder_parent_title = None
        folder_parent_path = None

        # title for this folder's page (as parent of its children):
        parent_page_title = None
        # title for the folder (same as above except when collapsing):
        folder_title = None

        if current_path != base_path:
            # TODO: add support for .pages file to read folder title
            if skip_empty or collapse_empty:
                folder_parent_path = find_non_empty_parent_path(
                    current_path, folder_data, default=file_path
                )
            else:
                folder_parent_path = current_path.parent

            folder_parent_title = folder_data[folder_parent_path]["title"]
            parent_page_title = current_path.name
            if len(markdown_files) == 1 and collapse_single_pages:
                parent_page_title = folder_parent_title
                folder_title = None
            else:
                if collapse_empty:
                    parent_page_title = str(
                        current_path.relative_to(folder_parent_path)
                    )
                if beautify_folders:
                    parent_page_title = (
                        current_path.name.replace("-", " ")
                        .replace("_", " ")
                        .capitalize()
                    )
                folder_title = parent_page_title
        if use_pages_file and ".pages" in file_names:
            with open(current_path.joinpath(".pages")) as pages_fp:
                pages_file_contents = yaml.safe_load(pages_fp)
            if "title" in pages_file_contents:
                parent_page_title = pages_file_contents["title"]
                folder_title = parent_page_title

        if dir_content_page_data and dir_content_page_data.title:
            folder_title = dir_content_page_data.title
            is_parent_title_default_or_none = (
                parent_page_title == current_path.name
                or (
                    beautify_folders
                    and parent_page_title
                    == current_path.name.replace("-", " ")
                    .replace("_", " ")
                    .capitalize()
                )
                or parent_page_title is None
            )
            if is_parent_title_default_or_none or (
                use_pages_file and ".pages" not in file_names
            ):
                parent_page_title = dir_content_page_data.title

        folder_data[current_path]["title"] = folder_title

        if (
            folder_title is not None
            and (markdown_files or directories or dir_content_page_data)
            and not (skip_empty and not markdown_files and not dir_content_page_data)
            and not (
                collapse_empty and not markdown_files and not dir_content_page_data
            )
        ):

            page_body = ""
            page_labels = None
            page_file_path_for_dir_page = None
            current_page_relative_links = None
            current_page_attachments = None

            if dir_content_page_data:
                page_body = dir_content_page_data.body
                page_labels = dir_content_page_data.labels
                page_file_path_for_dir_page = dir_content_page_data.file_path
                current_page_relative_links = dir_content_page_data.relative_links
                current_page_attachments = dir_content_page_data.attachments

            processed_pages.append(
                Page(
                    title=folder_title,
                    parent_title=folder_parent_title,
                    body=page_body,
                    file_path=page_file_path_for_dir_page,
                    labels=page_labels,
                    relative_links=current_page_relative_links,
                    attachments=current_page_attachments,
                )
            )

        for markdown_file in sorted(markdown_files):
            page_data = get_page_data_from_file_path(
                markdown_file,
                strip_header=strip_header,
                remove_text_newlines=remove_text_newlines,
                enable_relative_links=enable_relative_links,
            )
            if page_data is None:  # Skip if page data could not be retrieved
                continue
            if (
                collapse_single_pages and len(markdown_files) == 1 and not directories
            ):  # Collapse this folder
                page_data.parent_title = folder_data[current_path]["parent_title"]
            else:
                page_data.parent_title = parent_page_title
            processed_pages.append(page_data)

            # This replaces the title for the current folder with the title for the
            # document we just parsed, so things below this folder will be correctly
            # parented to the collapsed document.
            if len(markdown_files) == 1 and collapse_single_pages:
                folder_data[current_path]["title"] = processed_pages[-1].title

    return processed_pages


def get_page_data_from_file_path(
    file_path: Union[str, Path],
    strip_header: bool = False,
    remove_text_newlines: bool = False,
    enable_relative_links: bool = False,
) -> Page:
    if not isinstance(file_path, Path):
        file_path = Path(file_path)

    processed_mermaid_info = mermaid_processor.process_file_for_mermaid(file_path)
    mermaid_attachments: List[Path] = []
    current_file_to_read = file_path
    is_reading_cached_mermaid_output = False

    if processed_mermaid_info:
        processed_md_path, mermaid_attachments = processed_mermaid_info
        current_file_to_read = processed_md_path
        is_reading_cached_mermaid_output = True

    markdown_lines_from_current_file: Optional[List[str]] = None
    try:
        with open(current_file_to_read, encoding="utf-8") as file_handle:
            markdown_lines_from_current_file = file_handle.readlines()
    except Exception as e:
        # Log the error trying to read the primary file (original or cached)
        print(f"Warning: Error reading {current_file_to_read}: {e}")

        if (
            is_reading_cached_mermaid_output
        ):  # Fallback to original if cached read failed
            print(f"Falling back to original file: {file_path}")
            try:
                with open(
                    file_path, encoding="utf-8"
                ) as file_handle:  # Try UTF-8 first
                    markdown_lines_from_current_file = file_handle.readlines()
                mermaid_attachments = (
                    []
                )  # Reset mermaid attachments as we are using original
                current_file_to_read = file_path
                is_reading_cached_mermaid_output = False  # No longer reading cached
            except (
                UnicodeDecodeError
            ):  # Fallback to chardet if UTF-8 fails for original
                try:
                    with open(file_path, "rb") as file_handle_rb:
                        detected_encoding = chardet.detect(file_handle_rb.read())[
                            "encoding"
                        ]
                    if detected_encoding:
                        with open(
                            file_path, encoding=detected_encoding
                        ) as file_handle_enc:
                            markdown_lines_from_current_file = (
                                file_handle_enc.readlines()
                            )
                        mermaid_attachments = []
                        current_file_to_read = file_path
                        is_reading_cached_mermaid_output = False
                    else:
                        print(f"Warning: Could not detect encoding for {file_path}")
                        markdown_lines_from_current_file = None  # Indicate failure
                except Exception as fallback_e:
                    print(
                        f"Warning: Error reading {file_path} even after fallback: {fallback_e}"
                    )
                    markdown_lines_from_current_file = None  # Indicate failure
            except Exception as fallback_e:
                print(
                    f"Warning: Error reading {file_path} after fallback: {fallback_e}"
                )
                markdown_lines_from_current_file = None  # Indicate failure
        else:  # Original file read failed (not reading cached version)
            if isinstance(e, UnicodeDecodeError):
                try:
                    with open(file_path, "rb") as file_handle_rb:
                        detected_encoding = chardet.detect(file_handle_rb.read())[
                            "encoding"
                        ]
                    if detected_encoding:
                        with open(
                            file_path, encoding=detected_encoding
                        ) as file_handle_enc:
                            markdown_lines_from_current_file = (
                                file_handle_enc.readlines()
                            )
                    else:
                        print(f"Warning: Could not detect encoding for {file_path}")
                        markdown_lines_from_current_file = None
                except Exception as chardet_e:
                    print(
                        f"Warning: Error reading {file_path} with detected encoding: {chardet_e}"
                    )
                    markdown_lines_from_current_file = None
            else:
                # For other errors (PermissionError, etc.), just mark as failed
                markdown_lines_from_current_file = None

    # If reading failed at all stages, return None
    if markdown_lines_from_current_file is None:
        print(f"Error: Could not read content from {file_path}")
        return None

    frontmatter_data = get_document_frontmatter(markdown_lines_from_current_file)

    lines_for_mistune_rendering: List[str]
    if "frontmatter_end_line" in frontmatter_data:
        lines_for_mistune_rendering = markdown_lines_from_current_file[
            frontmatter_data["frontmatter_end_line"] :
        ]
    else:
        lines_for_mistune_rendering = markdown_lines_from_current_file

    renderer = ConfluenceRenderer(
        use_xhtml=True,
        strip_header=strip_header,
        remove_text_newlines=remove_text_newlines,
        enable_relative_links=enable_relative_links,
    )
    confluence_mistune = mistune.Markdown(renderer=renderer)
    confluence_content = confluence_mistune("".join(lines_for_mistune_rendering))

    page_title_from_renderer = renderer.title
    attachments_from_renderer = (
        renderer.attachments
    )  # These are Path objects, potentially relative
    relative_links_from_renderer = renderer.relative_links

    page = Page(
        title=page_title_from_renderer,
        body=confluence_content,
        attachments=None,  # Will be populated below
        relative_links=relative_links_from_renderer,
    )

    if "title" in frontmatter_data:
        page.title = frontmatter_data["title"]
    if "labels" in frontmatter_data:
        if isinstance(frontmatter_data["labels"], list):
            page.labels = [str(label) for label in frontmatter_data["labels"]]
        else:
            # Use print for user-facing warnings/errors in document processing
            print(
                f"Warning: labels section in frontmatter of {file_path} must be a list of strings, but got {type(frontmatter_data['labels'])}. Ignoring labels."
            )
            # Optionally: raise TypeError("the labels section in the frontmatter must be a list of strings")

    if not page.title:
        page.title = file_path.stem

    page.file_path = file_path

    # --- Attachment Path Resolution and Deduplication ---
    unique_resolved_paths_map: Dict[str, Path] = {}

    # 1. Add Mermaid attachments (already absolute paths from cache)
    for m_att_path in mermaid_attachments:
        resolved_path_str = str(m_att_path.resolve())
        if resolved_path_str not in unique_resolved_paths_map:
            unique_resolved_paths_map[resolved_path_str] = m_att_path

    # 2. Process attachments found by the renderer (mistune) from markdown content
    if attachments_from_renderer:
        for (
            renderer_att_path_obj
        ) in (
            attachments_from_renderer
        ):  # This is a Path object from MD link (e.g. Path("./image.png"))
            resolved_path: Optional[Path] = None

            if renderer_att_path_obj.is_absolute():
                resolved_path = renderer_att_path_obj.resolve()
            else:  # Relative path
                # Determine the base path for resolving the relative link
                # If we read from a cached mermaid file, relative links inside *that file* might point to:
                #   a) The mermaid-generated images (which are in the same cache dir)
                #   b) Other original relative images (which should be resolved relative to the *original* file)
                if is_reading_cached_mermaid_output:
                    # Tentatively resolve relative to the *cached* file's directory
                    tentative_resolve_in_cache = current_file_to_read.parent.joinpath(
                        renderer_att_path_obj
                    ).resolve()

                    # Check if this resolved path matches one of the known mermaid attachments (which are already absolute)
                    is_mermaid_generated_image = False
                    for m_att in mermaid_attachments:
                        if tentative_resolve_in_cache == m_att.resolve():
                            resolved_path = tentative_resolve_in_cache
                            is_mermaid_generated_image = True
                            break

                    if not is_mermaid_generated_image:
                        # If it's not a mermaid image, it must be relative to the ORIGINAL file path
                        if file_path:
                            resolved_path = file_path.parent.joinpath(
                                renderer_att_path_obj
                            ).resolve()
                        # else: Cannot resolve relative path if original file_path is None (e.g. stdin) - handled below

                else:  # Not reading cached output, so resolve relative to the original file path
                    if file_path:
                        resolved_path = file_path.parent.joinpath(
                            renderer_att_path_obj
                        ).resolve()
                    # else: Cannot resolve relative path if original file_path is None (e.g. stdin) - handled below

            # Add the resolved path to the map if it's valid and unique
            if resolved_path:
                resolved_path_str = str(resolved_path)
                if resolved_path_str not in unique_resolved_paths_map:
                    unique_resolved_paths_map[resolved_path_str] = resolved_path
            elif not renderer_att_path_obj.is_absolute() and file_path is None:
                # Handle relative paths when no file_path (e.g., stdin) - try resolving against CWD as fallback
                try:
                    resolved_cwd = Path.cwd().joinpath(renderer_att_path_obj).resolve()
                    resolved_cwd_str = str(resolved_cwd)
                    if resolved_cwd_str not in unique_resolved_paths_map:
                        unique_resolved_paths_map[resolved_cwd_str] = resolved_cwd
                        print(
                            f"Warning: Resolved relative attachment '{renderer_att_path_obj}' against CWD for content likely from stdin."
                        )
                except Exception as cwd_e:
                    print(
                        f"Warning: Could not resolve relative attachment '{renderer_att_path_obj}' from stdin against CWD: {cwd_e}"
                    )
            # else: Could not resolve the path (e.g., relative path from stdin and CWD resolve failed, or absolute path failed resolve)
            # Optionally log a warning here if resolved_path is None after checks

    # Assign the list of unique, resolved Path objects to the page
    page.attachments = list(unique_resolved_paths_map.values())

    return page


def get_page_data_from_lines(
    markdown_lines: List[str],
    strip_header: bool = False,
    remove_text_newlines: bool = False,
    enable_relative_links: bool = False,
) -> Page:
    frontmatter = get_document_frontmatter(markdown_lines)
    if "frontmatter_end_line" in frontmatter:
        markdown_lines = markdown_lines[frontmatter["frontmatter_end_line"] :]

    page = parse_page(
        markdown_lines,
        strip_header=strip_header,
        remove_text_newlines=remove_text_newlines,
        enable_relative_links=enable_relative_links,
    )

    if "title" in frontmatter:
        page.title = frontmatter["title"]

    if "labels" in frontmatter:
        if isinstance(frontmatter["labels"], list):
            page.labels = [str(label) for label in frontmatter["labels"]]
        else:
            raise TypeError(
                "the labels section in the frontmatter " "must be a list of strings"
            )
    return page


def parse_page(
    markdown_lines: List[str],
    strip_header: bool = False,
    remove_text_newlines: bool = False,
    enable_relative_links: bool = False,
) -> Page:
    renderer = ConfluenceRenderer(
        use_xhtml=True,
        strip_header=strip_header,
        remove_text_newlines=remove_text_newlines,
        enable_relative_links=enable_relative_links,
    )
    confluence_mistune = mistune.Markdown(renderer=renderer)
    confluence_content = confluence_mistune("".join(markdown_lines))

    page = Page(
        title=renderer.title,
        body=confluence_content,
        attachments=renderer.attachments,
        relative_links=renderer.relative_links,
    )

    return page


def get_document_frontmatter(markdown_lines: List[str]) -> Dict[str, Any]:
    frontmatter_yaml = ""
    frontmatter_end_line = 0
    if markdown_lines and markdown_lines[0] == "---\n":
        for index, line in enumerate(markdown_lines[1:]):
            if line == "---\n":
                frontmatter_end_line = index + 2
                break
            else:
                frontmatter_yaml += line
    frontmatter = None
    if frontmatter_yaml and frontmatter_end_line:
        try:
            frontmatter = yaml.safe_load(frontmatter_yaml)
        except ParserError:
            pass
    if isinstance(frontmatter, dict):
        frontmatter["frontmatter_end_line"] = frontmatter_end_line
    else:
        frontmatter = {}

    return frontmatter
