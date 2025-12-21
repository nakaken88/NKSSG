import datetime
from pathlib import Path
import pytest
import shutil
from unittest.mock import MagicMock

from nkssg.structure.config import Config
from nkssg.structure.pages import Page
from nkssg.structure.singles import Single, Singles
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
    content = """
---
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
    content = """
---
---
This is the content.
"""
    file_path = tmp_path / "test.md"
    file_path.write_text(content, encoding="utf-8")

    meta, doc = Single.parse_front_matter(file_path)

    assert meta == {}
    assert doc == "\nThis is the content.\n"

def test_parse_front_matter_invalid_yaml(tmp_path):
    content = """
---
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


def test_singles_initialization_and_collection(site_fixture):
    """
    Tests that the Singles class correctly initializes and collects pages
    from a dummy file structure, respecting post_type, doc_ext, and exclude rules.
    Refactored to use site_fixture.
    """
    config = site_fixture

    # Ensure Single.docs_dir is correctly set for the fixture context
    original_docs_dir = Single.docs_dir
    Single.docs_dir = config.docs_dir

    try:
        mock_plugins = MagicMock()

        singles = Singles(config, mock_plugins)

        # Expected files from site_fixture:
        # - my-test-post.md (post)
        # - first-post.md (post)
        # - about.html (page)
        # Excluded:
        # - _draft.md (post, excluded by pattern)
        # - notes.txt (page, invalid extension)

        assert len(singles.pages) == 3, "Should collect 3 valid pages"

        collected_paths = {str(p.src_path) for p in singles.pages}
        expected_paths = {
            str(Path("post") / "my-test-post.md"),
            str(Path("post") / "first-post.md"),
            str(Path("page") / "about.html")
        }
        assert collected_paths == expected_paths

        # Check that the after_initialize_singles action was called
        mock_plugins.do_action.assert_called_with('after_initialize_singles', target=singles)
    finally:
        # Teardown
        Single.docs_dir = original_docs_dir


@pytest.mark.parametrize("filename, meta_title, expected_title", [
    ('my-post.md', None, 'my-post'),
    ('my-post.md', 'A Custom Title', 'A Custom Title'),
    ('index.md', None, 'sample'),
    ('_10_my-post.md', None, 'my-post'),
])
def test_title_and_name_logic(config, tmp_path, filename, meta_title, expected_title):
    """
    Tests that _get_title correctly derives the title from filename or meta,
    and that _get_name correctly mirrors the title.
    """
    original_docs_dir = Single.docs_dir
    docs_dir = tmp_path / 'docs'
    post_type_dir = docs_dir / 'sample'
    post_type_dir.mkdir(parents=True, exist_ok=True)
    file_path = post_type_dir / filename
    file_path.touch()

    Single.docs_dir = docs_dir
    config.docs_dir = docs_dir

    single = Single(file_path, config)
    if meta_title:
        single.meta['title'] = meta_title

    # Test _get_title
    title = single._get_title()
    assert title == expected_title

    # Test _get_name (which should be the same as the title)
    single.title = title
    assert single._get_name() == expected_title

    Single.docs_dir = original_docs_dir


@pytest.mark.parametrize("name, meta_slug, expected_slug", [
    ('A Sample Post', None, 'a-sample-post'),
    ('A Sample Post', 'custom-slug', 'custom-slug'),
    ('日本語のタイトル', None, '日本語のタイトル'),
    ('日本語のタイトル', 'nihongo-no-taitoru', 'nihongo-no-taitoru'),
])
def test_get_slug_logic(config, tmp_path, name, meta_slug, expected_slug):
    """
    Tests that _get_slug correctly generates a slug from the name,
    and that a slug in the front matter takes precedence.
    """
    original_docs_dir = Single.docs_dir
    docs_dir = tmp_path / 'docs'
    post_type_dir = docs_dir / 'sample'
    post_type_dir.mkdir(parents=True, exist_ok=True)
    dummy_path = post_type_dir / 'dummy.md'
    dummy_path.touch()

    Single.docs_dir = docs_dir
    config.docs_dir = docs_dir

    single = Single(dummy_path, config)
    single.name = name  # Set name directly for this test
    if meta_slug:
        single.meta['slug'] = meta_slug

    assert single._get_slug('sample') == expected_slug

    Single.docs_dir = original_docs_dir


# --- Tests for __lt__ (sorting) method ---

@pytest.fixture
def create_single(tmp_path):
    """
    Fixture to create a Single object with a consistent setup for sorting tests.
    """
    docs_dir = tmp_path / 'docs'
    docs_dir.mkdir()
    
    original_docs_dir = Single.docs_dir
    Single.docs_dir = docs_dir

    cfg = Config()
    cfg.docs_dir = docs_dir
    cfg.update({'post_type': {'post': {'archive_type': 'date'}, 'page': {}}})

    def _maker(post_type: str, path_parts: list, order: int = None, date: datetime.datetime = None):
        if post_type not in cfg.post_type:
            new_pt_config = cfg.post_type.copy()
            new_pt_config[post_type] = {}
            cfg.post_type.update(new_pt_config)
        
        file_path = docs_dir.joinpath(post_type, *path_parts)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()
        
        s = Single(file_path, cfg)
        
        if order is not None:
            s.meta['order'] = order
        if date:
            s.date = date
        
        s._archive_type = cfg.post_type.get(post_type, {}).get('archive_type', 'section')
        
        return s

    yield _maker

    Single.docs_dir = original_docs_dir


def test_single_lt_by_post_type_index(create_single):
    """Tests sorting by post_type_index (post vs page)."""
    s_post = create_single('post', ['post1.md'])
    s_page = create_single('page', ['page1.md'])

    assert s_post < s_page
    assert not (s_page < s_post)


def test_single_lt_by_order_for_section_archive(create_single):
    """Tests sorting by 'order' metadata for a non-date archive type."""
    # Use 'page' which has archive_type='section' by default
    s1 = create_single('page', ['page1.md'], order=10)
    s2 = create_single('page', ['page2.md'], order=5)
    s3 = create_single('page', ['page3.md'], order=-1)
    s4 = create_single('page', ['page4.md']) # No order, defaults to 0

    assert s2 < s1 # 5 < 10
    assert s3 < s4 # -1 < 0
    assert s4 < s2 # 0 < 5

    # Test tie-breaking with src_path when order is the same
    s5 = create_single('page', ['b.md'], order=5)
    s6 = create_single('page', ['a.md'], order=5)
    assert s6 < s5


def test_single_lt_by_date_for_date_archive(create_single):
    """Tests sorting by date (desc) when archive_type is 'date'."""
    # Use 'post' which has archive_type='date'
    d_new = datetime.datetime(2023, 1, 2)
    d_old = datetime.datetime(2023, 1, 1)

    s1 = create_single('post', ['old.md'], date=d_old)
    s2 = create_single('post', ['new.md'], date=d_new)
    
    assert s2 < s1 # Newer date comes first

    # Fallback to src_path if dates are identical
    s3 = create_single('post', ['b.md'], date=d_new)
    s4 = create_single('post', ['a.md'], date=d_new)
    assert s4 < s3


def test_single_lt_order_is_ignored_for_date_archive(create_single):
    """Tests that 'order' is ignored for date archives."""
    d_new = datetime.datetime(2023, 1, 2)
    d_old = datetime.datetime(2023, 1, 1)

    # s2 has a higher order, but should still come first due to newer date
    s1 = create_single('post', ['old.md'], date=d_old, order=1)
    s2 = create_single('post', ['new.md'], date=d_new, order=99)

    assert s2 < s1


def test_single_lt_by_src_dir_for_section_archive(create_single):
    """Tests sorting by src_dir for non-date archives."""
    s1 = create_single('page', ['dir_a', 'post.md'])
    s2 = create_single('page', ['dir_b', 'post.md'])

    assert s1 < s2

def test_single_lt_by_filename_for_section_archive(create_single):
    """Tests sorting by filename (index first) for non-date archives."""
    s_index = create_single('page', ['common', 'index.md'])
    s_another = create_single('page', ['common', 'another.md'])
    s_zoo = create_single('page', ['common', 'zoo.md'])

    assert s_index < s_another
    assert s_index < s_zoo
    assert s_another < s_zoo


# --- Tests for update_url method ---

@pytest.fixture
def url_test_single(tmp_path):
    """Fixture to create a Single object for URL generation tests."""

    docs_dir = tmp_path / 'docs'

    original_docs_dir = Single.docs_dir
    Single.docs_dir = docs_dir

    cfg = Config()
    cfg.docs_dir = docs_dir
    cfg.public_dir = tmp_path / 'public'

    def _maker(post_type, filename, permalink=None, meta_url=None, add_prefix=True):

        # This config setup is specific to this test run
        pt_config = cfg.post_type.get(post_type, {})
        if permalink:
            pt_config['permalink'] = permalink

        pt_config['add_prefix_to_url'] = add_prefix
        cfg.post_type.update({post_type: pt_config})

        file_path = docs_dir / post_type / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()

        s = Single(file_path, cfg)

        s.slug = 'my-test-slug'
        s.name = 'my test slug'
        s.date = datetime.datetime(2023, 10, 26)

        if meta_url:
            s.meta['url'] = meta_url

        return s, cfg

    yield _maker

    Single.docs_dir = original_docs_dir


def test_update_url_with_meta_url(url_test_single):
    """Tests that url from front matter is prioritized."""

    single, config = url_test_single('post', 'test.md', meta_url='/custom/path/')

    single.update_url(config)

    assert single.rel_url == '/custom/path/'
    assert single.dest_path == Path('custom/path/index.html')


def test_update_url_with_permalink_default_prefix(url_test_single):
    """Tests that url is generated from permalink, respecting the default prefix."""
    # add_prefix defaults to True, so '/post/' should be prepended.

    single, config = url_test_single('post', 'test.md', permalink='/%Y/{slug}/')

    single.update_url(config)

    assert single.rel_url == '/post/2023/my-test-slug/'
    assert single.dest_path == Path('post/2023/my-test-slug/index.html')


def test_update_url_with_permalink_no_prefix(url_test_single):
    """Tests that url is generated from permalink without a prefix when configured."""

    single, config = url_test_single('post', 'test.md', permalink='/%Y/{slug}/', add_prefix=False)

    single.update_url(config)

    assert single.rel_url == '/2023/my-test-slug/'
    assert single.dest_path == Path('2023/my-test-slug/index.html')


class TestGetCleanDate:
    @pytest.mark.parametrize("input_date, expected_datetime", [
        # Already a datetime object
        (datetime.datetime(2023, 1, 1, 12, 30), datetime.datetime(2023, 1, 1, 12, 30)),
        # A date object (should be converted to datetime at midnight)
        (datetime.date(2023, 2, 15), datetime.datetime(2023, 2, 15, 0, 0)),
        # String with HH:MM
        ("2023-03-20 08:45", datetime.datetime(2023, 3, 20, 8, 45)),
        # String with H:MM (non-zero-padded)
        ("2023-03-20 8:45", datetime.datetime(2023, 3, 20, 8, 45)),
        # None or other invalid types should return epoch
        (None, datetime.datetime.fromtimestamp(0)),
        (12345, datetime.datetime.fromtimestamp(0)),
        ("An invalid string", datetime.datetime.fromtimestamp(0)),
        # Invalid date string format
        ("2023/03/20 08:45", datetime.datetime.fromtimestamp(0)), # Wrong separator
    ])
    def test_get_clean_date_various_formats(self, single_obj, input_date, expected_datetime):
        """Tests _get_clean_date with various valid and invalid input formats."""
        cleaned_date = single_obj._get_clean_date(input_date)
        assert cleaned_date == expected_datetime

    def test_get_clean_date_invalid_string_prints_warning(self, single_obj, mocker):
        """Tests that an invalid date string prints a warning to the console."""
        mock_print = mocker.patch('builtins.print')
        single_obj._get_clean_date("2023-99-99 12:00") # An invalid date that still matches the format
        
        mock_print.assert_called_once()
        # Check that the error message contains the problematic date value and the file id
        call_args, _ = mock_print.call_args
        assert "2023-99-99 12:00" in call_args[0]
        assert str(single_obj.id) in call_args[0]

