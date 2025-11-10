import datetime
from pathlib import Path
import pytest
import shutil

from nkssg.structure.config import Config
from nkssg.structure.pages import Page
from nkssg.structure.singles import Single
from nkssg.structure.archives import Archive


@pytest.fixture
def config():
    """Returns a default Config object with a dummy docs_dir."""
    original_docs_dir = Single.docs_dir
    # Use a dummy path for docs_dir to isolate tests and prevent side-effects
    Single.docs_dir = Path('docs')

    cfg = Config()
    cfg.docs_dir = Single.docs_dir
    cfg.update({'post_type': {'sample': {}}})

    yield cfg

    # Teardown to restore the original class variable
    Single.docs_dir = original_docs_dir


@pytest.fixture
def single_obj(config):
    """Returns a default Single object for testing."""
    dummy_path = config.docs_dir / 'sample' / '_10_sample post.md'
    single = Single(dummy_path, config)
    single.date = datetime.datetime(2001, 2, 3, 4, 5, 6)
    single.slug = 'sample-slug'
    return single


def create_mock_archives(single, path_parts):
    """Helper function to attach a mock archive hierarchy to a single object."""
    p = Archive(None, '/')
    for part in ['section', *path_parts]:
        c = Archive(p, part)
        c.slug = Page.to_slug(Page.clean_name(c.id.name))
        c.parent = p
        p = c
    single.archive_list = [c]
    return single


@pytest.mark.parametrize("permalink, expected", [
    ("/fix/", "/fix/"),
    ("/%Y/%m/%d/", "/2001/02/03/"),
    ("/pre/%Y/%m/%d/", "/pre/2001/02/03/"),
    ("/%Y%m%d/%H%M%S/", "/20010203/040506/"),
    ("/{slug}/", "/sample-slug/"),
    ("/{filename}/", "/sample-post/"),
])
def test_get_url_from_permalink_simple(single_obj, permalink, expected):
    result = single_obj.get_url_from_permalink(permalink, None, False)
    assert result == expected


@pytest.mark.parametrize("permalink, expected", [
    ("/%Y/%m/%d/", "/sample/2001/02/03/"),
    ("/{slug}/", "/sample/sample-slug/"),
])
def test_get_url_from_permalink_prefix(single_obj, permalink, expected):
    result = single_obj.get_url_from_permalink(permalink, 'sample', True)
    assert result == expected


SECTION_PATH_PARTS_STR = 'sample/dir1/_200_dir2/_xx_dir3'

@pytest.mark.parametrize("permalink, expected", [
    ("/{sample_top}/{slug}/", "/dir1/sample-post/"),
    ("/{sample_last}/{slug}/", "/dir3/sample-post/"),
    ("/{sample_all}/{slug}/", "/dir1/dir2/dir3/sample-post/"),
    ("/{sample_top}/{filename}/", "/dir1/sample-post/"),
])
def test_get_url_from_permalink_section_normal(config, permalink, expected):
    path_parts = SECTION_PATH_PARTS_STR.split('/')
    dummy_path = Path(config.docs_dir, *path_parts, 'sample post.md')
    single = Single(dummy_path, config)
    single.title = single._get_title()
    single.name = single._get_name()
    single.slug = single._get_slug('sample')

    single = create_mock_archives(single, path_parts)

    result = single.get_url_from_permalink(permalink, None, False)
    assert result == expected


@pytest.mark.parametrize("permalink, expected", [
    ("/{sample_all}/{slug}/", "/dir1/dir2/dir3/"),
])
def test_get_url_from_permalink_section_index(config, permalink, expected):
    path_parts = SECTION_PATH_PARTS_STR.split('/')
    dummy_path = Path(config.docs_dir, *path_parts, 'index.md')
    single = Single(dummy_path, config)
    single.title = single._get_title()
    single.name = single._get_name()
    single.slug = single._get_slug('sample')

    single = create_mock_archives(single, path_parts)

    result = single.get_url_from_permalink(permalink, None, False)
    assert result == expected


@pytest.mark.parametrize("permalink, expected", [
    ("/{sample_all}/{slug}/", "/new_sample/"),
])
def test_get_url_from_permalink_section_top(config, permalink, expected):
    config.post_type['sample']['slug'] = 'new_sample'
    dummy_path = Path(config.docs_dir, 'sample', 'index.md')
    single = Single(dummy_path, config)
    single.title = single._get_title()
    single.name = single._get_name()
    single.slug = single._get_slug('sample')

    single = create_mock_archives(single, ['sample'])

    result = single.get_url_from_permalink(permalink, 'new_sample', True)
    assert result == expected


def test_parse_front_matter_full(tmp_path):
    content = """---
title: Test Title
date: 2023-01-01
tags: [tag1, tag2]
---
This is the content.
"""
    file_path = tmp_path / "test.md"
    file_path.write_text(content, encoding="utf-8")

    meta, doc = Single.parse_front_matter(file_path)

    assert meta == {"title": "Test Title", "date": datetime.date(2023, 1, 1), "tags": ["tag1", "tag2"]}
    assert doc == "\nThis is the content.\n"

def test_parse_front_matter_no_front_matter(tmp_path):
    content = "This is content without front matter."
    file_path = tmp_path / "test.md"
    file_path.write_text(content, encoding="utf-8")

    meta, doc = Single.parse_front_matter(file_path)

    assert meta == {}
    assert doc == "This is content without front matter."

def test_parse_front_matter_empty_front_matter(tmp_path):
    content = """---
---
This is the content.
"""
    file_path = tmp_path / "test.md"
    file_path.write_text(content, encoding="utf-8")

    meta, doc = Single.parse_front_matter(file_path)

    assert meta == {}
    assert doc == "\nThis is the content.\n"

def test_parse_front_matter_invalid_yaml(tmp_path):
    content = """---
title: : invalid:
---
This is the content.
"""
    file_path = tmp_path / "test.md"
    file_path.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match="YAML parsing error"):
        Single.parse_front_matter(file_path)

def test_parse_front_matter_file_not_found():
    non_existent_path = Path("non_existent_file.md")
    with pytest.raises(FileNotFoundError, match="File not found"):
        Single.parse_front_matter(non_existent_path)


@pytest.mark.parametrize(
    "front_matter_content, is_future, is_expired, expected_is_draft",
    [
        # Explicit draft flag
        ("draft: true", False, False, True),
        ("draft: false", False, False, False),
        ("draft: 'true'", False, False, True),
        ("draft: 'false'", False, False, False),
        # Status flags
        ("status: draft", False, False, True),
        ("status: pending", False, False, True),
        ("status: private", False, False, True),
        ("status: publish", False, False, False),
        # Future/Expired flags
        ("", True, False, True),  # is_future = True
        ("", False, True, True),  # is_expired = True
        # Normal post
        ("", False, False, False),
        # Combined: draft: false overrides future/expired
        ("draft: false", True, True, False),
        # Combined: status: publish does NOT override future/expired
        ("status: publish", True, True, True),
    ]
)
def test_is_draft(tmp_path, config, front_matter_content, is_future, is_expired, expected_is_draft):
    content = f"---\n{front_matter_content}\n---\nThis is content."
    file_path = tmp_path / "test_post.md"
    file_path.write_text(content, encoding="utf-8")

    original_docs_dir = Single.docs_dir
    Single.docs_dir = tmp_path
    
    dummy_post_type_dir = tmp_path / "sample"
    dummy_post_type_dir.mkdir(exist_ok=True)
    final_file_path = dummy_post_type_dir / file_path.name
    shutil.copy(file_path, final_file_path)

    single = Single(final_file_path, config)
    
    single.meta, _ = Single.parse_front_matter(final_file_path)
    single.status = single.meta.get('status', 'publish')
    single.is_future = is_future
    single.is_expired = is_expired
    
    result = single._is_draft()

    assert result == expected_is_draft
    
    # Restore original docs_dir
    Single.docs_dir = original_docs_dir
