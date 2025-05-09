from pathlib import Path

import md2cf.document as doc
from test_package.utils import FakePage

ROOT_GITIGNORE = """.git
"""


def test_page_get_content_hash():
    p = doc.Page(title="test title", body="test content")

    assert p.get_content_hash() == "1eebdf4fdc9fc7bf283031b93f9aef3338de9052"


def test_get_pages_from_directory(fs):
    fs.create_file("/root-folder/root-folder-file.md")
    fs.create_dir("/root-folder/empty-dir")
    fs.create_file("/root-folder/parent/child/child-file.md")

    result = doc.get_pages_from_directory(Path("/root-folder"))
    assert result == [
        FakePage(
            title="root-folder-file",
            file_path=Path("/root-folder/root-folder-file.md", parent_title=None),
        ),
        FakePage(title="parent", file_path=None, parent_title=None),
        FakePage(title="child", file_path=None, parent_title="parent"),
        FakePage(
            title="child-file",
            file_path=Path("/root-folder/parent/child/child-file.md"),
            parent_title="child",
        ),
    ]


def test_get_pages_from_directory_use_pages(fs):
    fs.create_file("/root-folder/.mdignore", contents=ROOT_GITIGNORE)
    fs.create_dir("/root-folder/.git")
    fs.create_dir("/root-folder/.git/refs")
    fs.create_file("/root-folder/.git/refs/test.md")
    fs.create_file("/root-folder/root-folder-file.md")
    fs.create_dir("/root-folder/empty-dir")
    fs.create_file("/root-folder/parent/child/child-file.md")

    result = doc.get_pages_from_directory(
        Path("/root-folder"), use_pages_file=True, enable_relative_links=True
    )
    print(result)
    assert result == [
        FakePage(
            title="root-folder-file",
            file_path=Path("/root-folder/root-folder-file.md", parent_title=None),
        ),
        FakePage(title="parent", file_path=None, parent_title=None),
        FakePage(title="child", file_path=None, parent_title="parent"),
        FakePage(
            title="child-file",
            file_path=Path("/root-folder/parent/child/child-file.md"),
            parent_title="child",
        ),
    ]


def test_get_pages_from_directory_collapse_single_pages(fs):
    fs.create_file("/root-folder/root-folder-file.md")
    fs.create_file("/root-folder/parent/child/child-file.md")

    result = doc.get_pages_from_directory(
        Path("/root-folder"), collapse_single_pages=True
    )
    assert result == [
        FakePage(
            title="root-folder-file",
            file_path=Path("/root-folder/root-folder-file.md", parent_title=None),
        ),
        FakePage(title="parent", file_path=None, parent_title=None),
        FakePage(
            title="child-file",
            file_path=Path("/root-folder/parent/child/child-file.md"),
            parent_title="parent",
        ),
    ]


def test_get_pages_from_directory_collapse_single_pages_no_non_empty_parent(fs):
    fs.create_file("/root-folder/parent/child/child-file.md")

    result = doc.get_pages_from_directory(
        Path("/root-folder"), collapse_single_pages=True
    )
    assert result == [
        FakePage(
            title="parent",
        ),
        FakePage(
            title="child-file",
            file_path=Path("/root-folder/parent/child/child-file.md"),
            parent_title="parent",
        ),
    ]


def test_get_pages_from_directory_skip_empty(fs):
    fs.create_file("/root-folder/root-folder-file.md")
    fs.create_file("/root-folder/parent/child/child-file.md")

    result = doc.get_pages_from_directory(Path("/root-folder"), skip_empty=True)
    assert result == [
        FakePage(
            title="root-folder-file",
            file_path=Path("/root-folder/root-folder-file.md", parent_title=None),
        ),
        FakePage(
            title="child",
            file_path=None,
            parent_title=None,
        ),
        FakePage(
            title="child-file",
            file_path=Path("/root-folder/parent/child/child-file.md"),
            parent_title="child",
        ),
    ]


def test_get_pages_from_directory_skip_empty_no_non_empty_parent(fs):
    fs.create_file("/root-folder/parent/child/child-file.md")

    result = doc.get_pages_from_directory(Path("/root-folder"), skip_empty=True)
    assert result == [
        FakePage(
            title="child",
            file_path=None,
            parent_title=None,
        ),
        FakePage(
            title="child-file",
            file_path=Path("/root-folder/parent/child/child-file.md"),
            parent_title="child",
        ),
    ]


def test_get_pages_from_directory_collapse_empty(fs):
    fs.create_file("/root-folder/root-folder-file.md")
    fs.create_file("/root-folder/parent/child/child-file.md")

    result = doc.get_pages_from_directory(Path("/root-folder"), collapse_empty=True)
    assert result == [
        FakePage(
            title="root-folder-file",
            file_path=Path("/root-folder/root-folder-file.md", parent_title=None),
        ),
        FakePage(
            title="parent/child",
            file_path=None,
            parent_title=None,
        ),
        FakePage(
            title="child-file",
            file_path=Path("/root-folder/parent/child/child-file.md"),
            parent_title="parent/child",
        ),
    ]


def test_get_pages_from_directory_collapse_empty_no_non_empty_parent(fs):
    fs.create_file("/root-folder/parent/child/child-file.md")

    result = doc.get_pages_from_directory(Path("/root-folder"), collapse_empty=True)
    assert result == [
        FakePage(
            title="parent/child",
            file_path=None,
            parent_title=None,
        ),
        FakePage(
            title="child-file",
            file_path=Path("/root-folder/parent/child/child-file.md"),
            parent_title="parent/child",
        ),
    ]


def test_get_pages_from_directory_beautify_folders(fs):
    fs.create_file("/root-folder/ugly-folder/another_yucky_folder/child-file.md")

    result = doc.get_pages_from_directory(Path("/root-folder"), beautify_folders=True)
    assert result == [
        FakePage(
            title="Ugly folder",
        ),
        FakePage(
            title="Another yucky folder",
        ),
        FakePage(
            title="child-file",
            file_path=Path(
                "/root-folder/ugly-folder/another_yucky_folder/child-file.md"
            ),
            parent_title="Another yucky folder",
        ),
    ]


def test_get_pages_from_directory_with_pages_file_multi_level(fs):
    fs.create_file("/root-folder/sub-folder-a/some-page.md")
    fs.create_file("/root-folder/sub-folder-b/some-page.md")
    fs.create_file("/root-folder/sub-folder-a/.pages", contents='title: "Folder A"')
    fs.create_file("/root-folder/sub-folder-b/.pages", contents='title: "Folder B"')

    result = doc.get_pages_from_directory(Path("/root-folder"), use_pages_file=True)
    assert result == [
        FakePage(
            title="Folder A",
        ),
        FakePage(
            title="some-page",
            file_path=Path("/root-folder/sub-folder-a/some-page.md"),
            parent_title="Folder A",
        ),
        FakePage(
            title="Folder B",
        ),
        FakePage(
            title="some-page",
            file_path=Path("/root-folder/sub-folder-b/some-page.md"),
            parent_title="Folder B",
        ),
    ]


def test_get_pages_from_directory_with_pages_file_single_level(fs):
    fs.create_file("/root-folder/some-page.md")
    fs.create_file("/root-folder/.pages", contents='title: "Root folder"')

    result = doc.get_pages_from_directory(Path("/root-folder"), use_pages_file=True)
    assert result == [
        FakePage(
            title="Root folder",
        ),
        FakePage(
            title="some-page",
            file_path=Path("/root-folder/some-page.md"),
            parent_title="Root folder",
        ),
    ]


def test_get_document_frontmatter():
    source_markdown = """---
title: This is a title
labels:
  - label1
  - label2
---
# This is normal markdown content

Yep.
"""

    assert doc.get_document_frontmatter(source_markdown.splitlines(keepends=True)) == {
        "title": "This is a title",
        "labels": ["label1", "label2"],
        "frontmatter_end_line": 6,
    }


def test_get_document_frontmatter_only_first():
    source_markdown = """---
title: This is a title
---
# This is normal markdown content

---

With other triple dashes!

Yep.
"""

    assert doc.get_document_frontmatter(source_markdown.splitlines(keepends=True)) == {
        "title": "This is a title",
        "frontmatter_end_line": 3,
    }


def test_get_document_frontmatter_no_closing():
    source_markdown = """---
# This is normal markdown content

Yep.
"""

    assert doc.get_document_frontmatter(source_markdown.splitlines(keepends=True)) == {}


def test_get_document_frontmatter_extra_whitespace():
    source_markdown = """

---
title: This is a title
---
# This is normal markdown content

Yep.
"""

    assert doc.get_document_frontmatter(source_markdown.splitlines(keepends=True)) == {}


def test_get_document_frontmatter_empty():
    source_markdown = """---
---
# This is normal markdown content

Yep.
"""

    assert doc.get_document_frontmatter(source_markdown.splitlines(keepends=True)) == {}


def test_get_pages_from_directory_with_underscore_dirname_md(fs):
    fs.create_file("/root-folder/_root-folder.md", contents="# Root Folder Content\nThis is the main content for the root folder.")
    fs.create_file("/root-folder/page1.md", contents="# Page 1 Content")
    fs.create_dir("/root-folder/sub-folder")
    fs.create_file("/root-folder/sub-folder/_sub-folder.md", contents="# Sub Folder Content\nDetails for sub-folder.")
    fs.create_file("/root-folder/sub-folder/page2.md", contents="# Page 2 Content")
    fs.create_dir("/root-folder/sub-folder/another-sub")
    fs.create_file("/root-folder/sub-folder/another-sub/page3.md", contents="# Page 3 Content")

    result = doc.get_pages_from_directory(Path("/root-folder"))

    expected_data = [
        {
            "title": "Root Folder Content",
            "body": "<h1>Root Folder Content</h1>\n<p>This is the main content for the root folder.</p>\n",
            "file_path": "/root-folder/_root-folder.md",
            "parent_title": None,
        },
        {
            "title": "Page 1 Content",
            "body": "<h1>Page 1 Content</h1>\n",
            "file_path": "/root-folder/page1.md",
            "parent_title": "Root Folder Content",
        },
        {
            "title": "Sub Folder Content",
            "body": "<h1>Sub Folder Content</h1>\n<p>Details for sub-folder.</p>\n",
            "file_path": "/root-folder/sub-folder/_sub-folder.md",
            "parent_title": "Root Folder Content",
        },
        {
            "title": "Page 2 Content",
            "body": "<h1>Page 2 Content</h1>\n",
            "file_path": "/root-folder/sub-folder/page2.md",
            "parent_title": "Sub Folder Content",
        },
        {
            "title": "another-sub",
            "body": "",
            "file_path": None,
            "parent_title": "Sub Folder Content",
        },
        {
            "title": "Page 3 Content",
            "body": "<h1>Page 3 Content</h1>\n",
            "file_path": "/root-folder/sub-folder/another-sub/page3.md",
            "parent_title": "another-sub",
        },
    ]

    expected_pages = [
        FakePage(
            title=d["title"],
            body=d["body"],
            file_path=Path(d["file_path"]) if d["file_path"] else None,
            parent_title=d["parent_title"],
        )
        for d in expected_data
    ]

    assert len(result) == len(expected_pages)

    core_fields = ['title', 'parent_title', 'body', 'file_path', 'labels']

    def get_comparable_item(page_obj, is_fake_page=False):
        if is_fake_page:
            data_source = getattr(page_obj, 'attrs_to_compare', None)
            if data_source is None:
                data_source = page_obj

            data = {}
            for field in core_fields:
                value = getattr(data_source, field, None) if not isinstance(data_source, dict) else data_source.get(field)

                if field == 'body' and value is None:
                    data[field] = ""
                elif field == 'labels' and value is None:
                    data[field] = None
                else:
                    data[field] = value
            return data
        else:
            data = {field: getattr(page_obj, field, None) for field in core_fields}
            return data

    result_comparable = sorted([get_comparable_item(p) for p in result], key=lambda x: (str(x.get('parent_title') or ''), str(x.get('title') or '')))
    expected_comparable = sorted([get_comparable_item(p, is_fake_page=True) for p in expected_pages], key=lambda x: (str(x.get('parent_title') or ''), str(x.get('title') or '')))

    assert result_comparable == expected_comparable
