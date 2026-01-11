import datetime
from pathlib import Path, PurePath
import pytest
import shutil
from unittest.mock import MagicMock, patch
import builtins
import re
import jinja2

from nkssg.structure.config import Config
from nkssg.structure.pages import Page
from nkssg.structure.singles import Single, Singles
from nkssg.structure.archives import Archive
from nkssg.structure.themes import Themes


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


class TestGetDate:
    @pytest.fixture
    def get_date_single(self, tmp_path):
        """Fixture for creating a Single object for _get_date tests."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        
        original_docs_dir = Single.docs_dir
        Single.docs_dir = docs_dir

        cfg = Config()
        cfg.docs_dir = docs_dir
        cfg.post_type.update({'post': {}})
        
        def _maker(filename: str, meta_date: str = None, meta_modified: str = None):
            post_dir = docs_dir / "post"
            post_dir.mkdir(exist_ok=True, parents=True)
            
            file_path = post_dir / filename
            
            front_matter = "---\n"
            if meta_date:
                front_matter += f"date: {meta_date}\n"
            if meta_modified:
                front_matter += f"modified: {meta_modified}\n"
            front_matter += "---\n"
            
            file_path.write_text(front_matter, encoding="utf-8")
            
            s = Single(file_path, cfg)
            s.meta, _ = Single.parse_front_matter(file_path)
            return s
            
        yield _maker

        Single.docs_dir = original_docs_dir

    @pytest.mark.parametrize("filename", ["20231026.md", "2023-10-26.md"])
    def test_date_from_filename(self, get_date_single, filename):
        """Tests that date is correctly parsed from a date-only filename."""
        single = get_date_single(filename)
        cdate, _ = single._get_date()
        assert cdate == datetime.datetime(2023, 10, 26)

    def test_date_from_front_matter_overrides_filename(self, get_date_single):
        """Tests that front matter date takes precedence over filename date."""
        single = get_date_single("2023-10-26.md", meta_date="2024-01-01")
        cdate, _ = single._get_date()
        assert cdate == datetime.datetime(2024, 1, 1)

    def test_date_fallback_to_file_creation_time(self, get_date_single):
        """Tests that date falls back to file creation time when not in filename or meta."""
        known_date = datetime.datetime(2022, 5, 5)
        single = get_date_single("my-post-without-date.md")
        
        # Manually set the initial date (which simulates file creation time)
        single.date = known_date
        
        cdate, _ = single._get_date()
        assert cdate == known_date

    def test_modified_date_from_front_matter(self, get_date_single):
        """Tests that modified date is correctly read from front matter."""
        single = get_date_single("2023-10-26.md", meta_modified="2023-11-15 10:00")
        _, mdate = single._get_date()
        assert mdate == datetime.datetime(2023, 11, 15, 10, 0)

    def test_modified_date_is_at_least_creation_date(self, get_date_single):
        """Tests that modified date cannot be older than the creation date."""
        # Here, filename date (Oct 26) is newer than meta modified date (Oct 1)
        single = get_date_single("2023-10-26.md", meta_modified="2023-10-01")
        cdate, mdate = single._get_date()
        assert cdate == datetime.datetime(2023, 10, 26)
        assert mdate == cdate # mdate should be bumped up to cdate


class TestSingleTemplateLookup:
    @pytest.fixture
    def single_for_template_lookup(self, tmp_path, config):
        """
        Fixture to create a Single object for template lookup tests.
        Returns the Single object, and a mock Themes object.
        """
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        
        original_docs_dir = Single.docs_dir
        Single.docs_dir = docs_dir

        # Ensure a post_type exists for the Single object
        config.post_type.update({'post': {}})

        # Create a dummy file for the Single object
        post_dir = docs_dir / "post"
        post_dir.mkdir(exist_ok=True)
        src_file = post_dir / "test-post.md"
        src_file.touch()

        single = Single(src_file, config)
        single.meta = {} # Clear meta to control template override
        single.post_type = 'post' # Ensure post_type is set

        mock_themes = MagicMock(spec=Themes)
        
        yield single, config, mock_themes

        Single.docs_dir = original_docs_dir

    @pytest.mark.parametrize("config_mode, meta_template, available_templates, expected_template", [
        # Draft mode takes precedence
        ('draft', None, ['draft.html', 'single-post.html'], 'draft.html'),
        ('draft', 'my-custom.html', ['draft.html', 'my-custom.html'], 'draft.html'),
        
        # meta.template takes precedence if not in draft mode
        ('build', 'my-custom.html', ['my-custom.html', 'single-post.html'], 'my-custom.html'),
        ('build', 'my-custom.html', ['single-post.html'], 'single-post.html'), # meta.template not found
        
        # single-{post_type}.html
        ('build', None, ['single-post.html', 'single.html'], 'single-post.html'),
        
        # single.html
        ('build', None, ['single.html', 'main.html'], 'single.html'),
        
        # main.html
        ('build', None, ['main.html'], 'main.html'),
        
        # None found
        ('build', None, [], None),
        ('build', 'non-existent.html', [], None),
    ])
    def test_lookup_template_hierarchy(self, single_for_template_lookup, 
                                       config_mode, meta_template, available_templates, expected_template):
        """
        Tests the template lookup hierarchy based on config mode, meta.template,
        and available templates in the theme.
        """
        single, config, mock_themes = single_for_template_lookup
        config.mode = config_mode
        if meta_template:
            single.meta['template'] = meta_template

        # Configure the mock themes.lookup_template to simulate which templates are "found"
        def mock_lookup_template_side_effect(search_list, full_path=False):
            for tpl in search_list:
                if tpl in available_templates:
                    return tpl # Return the name as it would be found by Themes.lookup_template
            return None
        
        mock_themes.lookup_template.side_effect = mock_lookup_template_side_effect

        result = single.lookup_template(config, mock_themes)
        assert result == expected_template


class TestSinglesDuplicateDetection:
    def test_setup_file_ids_raises_on_duplicate(self, config):
        """
        Tests that _setup_file_ids raises ValueError on duplicate file IDs.
        """
        mock_plugins = MagicMock()
        singles = Singles(config, mock_plugins)

        # Create two different Single objects that resolve to the same file_id
        s1 = MagicMock(spec=Single)
        s1.file_id = "duplicate-id"
        s1.__str__.return_value = "Single(src='post/a.md')"

        s2 = MagicMock(spec=Single)
        s2.file_id = "duplicate-id"
        s2.__str__.return_value = "Single(src='post/b.md')"

        singles.pages = [s1, s2]

        with pytest.raises(ValueError, match="Duplicate file ID detected"):
            singles._setup_file_ids()

    def test_setup_dest_path_raises_on_duplicate(self, config):
        """
        Tests that setup_dest_path raises ValueError on duplicate destination paths.
        """
        mock_plugins = MagicMock()
        singles = Singles(config, mock_plugins)

        # Create two different Single objects that resolve to the same dest_path
        s1 = MagicMock(spec=Single)
        s1.dest_path = Path("public/dupe/path/index.html")
        s1.__str__.return_value = "Single(src='post/a.md')"

        s2 = MagicMock(spec=Single)
        s2.dest_path = Path("public/dupe/path/index.html")
        s2.__str__.return_value = "Single(src='post/b.md')"

        singles.pages = [s1, s2]

        with pytest.raises(ValueError, match="Duplicate Dest Path"):
            singles.setup_dest_path()

    def test_singles_draft_mode_initialization(self, tmp_path):
        """
        Tests that when in 'draft' mode, Singles correctly initializes
        by collecting only the specified draft file.
        """
        # Setup config for draft mode
        config = Config(base_dir=tmp_path)
        config.mode = 'draft'
        config.docs_dir = tmp_path / 'docs'
        config.docs_dir.mkdir()
        
        # Manually add the 'post' post_type to the config, as the Site class isn't running
        config.post_type.update({'post': {}})
        
        # Create a dummy draft file
        draft_content_dir = config.docs_dir / 'post'
        draft_content_dir.mkdir()
        dummy_draft_file = draft_content_dir / 'my-draft-post.md'
        dummy_draft_file.touch()
        
        config.draft_path = dummy_draft_file
        
        # Create other files that should NOT be collected in draft mode
        (config.docs_dir / 'page').mkdir()
        (config.docs_dir / 'page' / 'about.md').touch()

        original_docs_dir = Single.docs_dir
        try:
            # Reset the class variable to ensure it's set by the current config
            Single.docs_dir = ''
            
            mock_plugins = MagicMock()
            singles = Singles(config, mock_plugins)

            assert len(singles.pages) == 1
            assert singles.pages[0].abs_src_path == dummy_draft_file
            
            # Ensure do_action is called for draft mode
            mock_plugins.do_action.assert_called_with('after_initialize_singles', target=singles)
        finally:
            # Restore the class variable to prevent side effects
            Single.docs_dir = original_docs_dir

class TestSingleImageProcessing:
    @pytest.fixture
    def image_test_single(self, tmp_path, mocker):
        """
        Fixture to create a Single object for image processing tests.
        Mocks necessary components like file existence.
        """
        base_dir = tmp_path
        docs_dir = base_dir / 'docs'
        docs_dir.mkdir()
        
        public_dir = base_dir / 'public'
        public_dir.mkdir()

        original_docs_dir = Single.docs_dir
        Single.docs_dir = docs_dir

        cfg = Config(base_dir=base_dir) # Explicitly set base_dir
        cfg.docs_dir = docs_dir
        cfg.public_dir = public_dir
        cfg.static_dir = base_dir / 'static'
        cfg.post_type.update({'post': {}})
        cfg.site.site_url = 'http://example.com'

        # Create a dummy file for the Single object
        (docs_dir / 'post').mkdir(exist_ok=True)
        (docs_dir / 'post' / 'test-image.md').touch()

        # Dummy image files for existence checks
        # Absolute paths are relative to base_dir, not docs_dir
        (base_dir / 'images').mkdir(exist_ok=True)
        (base_dir / 'images' / 'local-img.jpg').touch()
        
        cfg.static_dir.mkdir(exist_ok=True)
        (cfg.static_dir / 'static-img.png').touch()

        single = Single(docs_dir / 'post' / 'test-image.md', cfg)
        single.date = datetime.datetime(2023, 10, 26, 10, 30)
        single.abs_src_path = docs_dir / 'post' / 'test-image.md'

        mocker.patch('builtins.print')

        yield single, cfg, public_dir

        Single.docs_dir = original_docs_dir

    def test_get_image_no_image_meta(self, image_test_single):
        """Tests _get_image when no 'image' key is in meta."""
        single, config, _ = image_test_single
        single.meta = {}
        assert single._get_image(config) == {}

    def test_get_image_empty_src_in_meta(self, image_test_single):
        """Tests _get_image when 'image' key is present but 'src' is empty."""
        single, config, _ = image_test_single
        single.meta = {'image': {'alt': 'some alt'}}
        assert single._get_image(config) == {}

    def test_get_image_external_url(self, image_test_single):
        """Tests _get_image when src is an external URL."""
        single, config, _ = image_test_single
        external_url = 'https://example.com/external.jpg'
        single.meta = {'image': {'src': external_url, 'alt': 'External'}}
        expected_image = {'src': external_url, 'alt': 'External'}
        assert single._get_image(config) == expected_image

    def test_get_image_absolute_local_path_exists(self, image_test_single):
        """Tests _get_image with an absolute local src path that exists."""
        single, config, public_dir = image_test_single
        src = '/images/local-img.jpg'
        single.meta = {'image': {'src': src}}
        
        result = single._get_image(config)
        
        expected_old_path = config.base_dir / 'images' / 'local-img.jpg'
        expected_new_path = public_dir / 'thumb' / '2023' / '10' / 'local-img.jpg'
        expected_rel_url = '/thumb/2023/10/local-img.jpg'
        expected_abs_url = f"{config.site.site_url}{expected_rel_url}"

        assert result['src'] == expected_abs_url
        assert result['url'] == expected_abs_url
        assert result['rel_url'] == expected_rel_url
        assert result['old_path'] == expected_old_path
        assert result['new_path'] == expected_new_path
        assert 'alt' not in result

    def test_get_image_absolute_local_path_not_exists(self, image_test_single):
        """Tests _get_image with an absolute local src path that does NOT exist."""
        single, config, _ = image_test_single
        src = '/images/non-existent.jpg'
        single.meta = {'image': {'src': src}}
        
        result = single._get_image(config)
        
        assert result == {}
        builtins.print.assert_called_once()
        assert "Warning: Image path" in builtins.print.call_args[0][0]
        assert "non-existent.jpg" in builtins.print.call_args[0][0]

    def test_get_image_relative_local_path_exists(self, image_test_single):
        """Tests _get_image with a relative local src path that exists."""
        single, config, public_dir = image_test_single
        # To make 'local-img.jpg' relative to 'docs/post/test-image.md',
        # we need to go up one level then into 'images'
        single.abs_src_path = config.docs_dir / 'post' / 'some-post.md'
        # The image exists at base_dir / images, so we go up from docs/post
        src = '../../images/local-img.jpg'
        single.meta = {'image': {'src': src, 'caption': 'A caption'}}
        
        result = single._get_image(config)
        
        expected_old_path = config.base_dir / 'images' / 'local-img.jpg'
        expected_new_path = public_dir / 'thumb' / '2023' / '10' / 'local-img.jpg'
        expected_rel_url = '/thumb/2023/10/local-img.jpg'
        expected_abs_url = f"{config.site.site_url}{expected_rel_url}"

        assert result['src'] == expected_abs_url
        assert result['url'] == expected_abs_url
        assert result['rel_url'] == expected_rel_url
        # Resolve both paths to their canonical form before comparing
        assert result['old_path'].resolve() == expected_old_path.resolve()
        assert result['new_path'].resolve() == expected_new_path.resolve()
        assert result['caption'] == 'A caption'

    def test_get_image_simple_static_path_handled(self, image_test_single):
        """
        Tests _get_image with a simple, non-nested static path, verifying it's
        correctly recognized as static and its URL is generated directly.
        """
        single, config, public_dir = image_test_single
        # Use a simple static directory for this test
        config.static_dir = config.base_dir / 'static'
        config.static_dir.mkdir(exist_ok=True)
        
        src = f'/{config.static_dir.name}/static-img.png' # e.g. /static/static-img.png
        
        static_image_path = config.static_dir / 'static-img.png'
        static_image_path.touch()
        
        single.meta = {'image': {'src': src}}
        config.use_abs_url = False

        result = single._get_image(config)

        # After the fix, the URL should be the direct static path, not a thumbnail path.
        expected_rel_url = src
        expected_old_path = static_image_path

        assert result['url'] == expected_rel_url
        assert result['rel_url'] == expected_rel_url
        assert result['old_path'] == expected_old_path
        assert 'new_path' not in result # Verify thumbnail path is not generated

    def test_get_image_static_dir_path_correctly_handled(self, image_test_single):
        """
        Tests _get_image with a static-like path (potentially nested),
        verifying it's recognized as static and its URL is generated directly
        without thumbnail processing.
        """
        single, config, public_dir = image_test_single
        
        # Simulate a nested static directory
        nested_static_path = 'assets/static'
        config.static_dir = config.base_dir / nested_static_path
        config.static_dir.mkdir(parents=True, exist_ok=True)
        
        # The src URL should match the relative path from base_dir
        src = f'/{nested_static_path}/my-static-img.png'
        
        # Ensure the dummy static file exists at the correct location
        static_image_path = config.static_dir / 'my-static-img.png'
        static_image_path.touch()

        single.meta = {'image': {'src': src}}
        config.use_abs_url = False

        result = single._get_image(config)

        # The final URL should be the direct path to the static asset
        expected_rel_url = src
        expected_old_path = static_image_path

        assert result['url'] == expected_rel_url
        assert result['rel_url'] == expected_rel_url
        assert result['src'] == expected_rel_url
        assert result['old_path'].resolve() == expected_old_path.resolve()
        assert 'new_path' not in result # Thumbnail path should not be set for static images

    def test_get_image_use_abs_url_false(self, image_test_single):
        """Tests _get_image when config.use_abs_url is False."""
        single, config, _ = image_test_single
        config.use_abs_url = False
        src = '/images/local-img.jpg'
        single.meta = {'image': {'src': src}}

        result = single._get_image(config)

        expected_rel_url = '/thumb/2023/10/local-img.jpg'
        assert result['url'] == expected_rel_url
        assert result['src'] == expected_rel_url
        assert result['abs_url'] == f"{config.site.site_url}{expected_rel_url}" # abs_url is still set


class TestSingleInitializationAndPathParsing:

    @pytest.fixture(autouse=True)
    def setup_single_docs_dir(self, tmp_path):
        """Fixture to ensure Single.docs_dir is clean before and after tests."""
        original_docs_dir = Single.docs_dir
        Single.docs_dir = tmp_path / "docs" # Set a consistent docs_dir for tests
        Single.docs_dir.mkdir(exist_ok=True)
        yield
        Single.docs_dir = original_docs_dir

    @pytest.fixture
    def mock_config_for_single_init(self, tmp_path):
        """Mock Config object for Single initialization tests."""
        cfg = Config(base_dir=tmp_path)
        cfg.docs_dir = tmp_path / "docs"
        cfg.post_type.update({'article': {}, 'page': {}})
        return cfg

    def test_single_init_success(self, mock_config_for_single_init):
        """Tests successful initialization of Single object with valid path."""
        config = mock_config_for_single_init
        
        # Create dummy file structure
        (config.docs_dir / 'article').mkdir()
        src_file = config.docs_dir / 'article' / 'my-post.md'
        src_file.touch()

        single = Single(src_file, config)

        assert single.abs_src_path == src_file
        assert single.src_path == Path('article/my-post.md')
        assert single.id == PurePath('/docs/article/my-post.md')
        assert single.post_type == 'article'
        assert single.src_dir == Path('article')
        assert single.filename == 'my-post'
        assert single.ext == 'md'
        # Check archive_type default
        assert single.archive_type == 'section'

    def test_abs_src_path_setter_success(self, mock_config_for_single_init):
        """Tests successful assignment of abs_src_path and derived attributes."""
        config = mock_config_for_single_init
        
        (config.docs_dir / 'page').mkdir()
        src_file = config.docs_dir / 'page' / 'about.html'
        src_file.touch()

        single = Single(src_file, config) # Initial setup

        # Change abs_src_path to a new valid path
        new_src_file = config.docs_dir / 'article' / 'another-post.md'
        new_src_file.parent.mkdir(exist_ok=True)
        new_src_file.touch()

        single.abs_src_path = new_src_file

        assert single.abs_src_path == new_src_file
        assert single.src_path == Path('article/another-post.md')
        assert single.id == PurePath('/docs/article/another-post.md')
        assert single.post_type == 'article'
        assert single.src_dir == Path('article')
        assert single.filename == 'another-post'
        assert single.ext == 'md'

    def test_abs_src_path_setter_not_descendant_raises_value_error(self, mock_config_for_single_init, tmp_path):
        """Tests that assigning abs_src_path not descendant of Single.docs_dir raises ValueError."""
        config = mock_config_for_single_init
        
        src_file = config.docs_dir / 'page' / 'about.html'
        src_file.parent.mkdir(exist_ok=True)
        src_file.touch()

        single = Single(src_file, config)

        # Attempt to assign a path outside docs_dir
        outside_path = tmp_path / 'outside' / 'file.txt'
        outside_path.parent.mkdir(exist_ok=True)
        outside_path.touch()

        expected_error_msg = f"The path '{outside_path}' must be a descendant of the docs dir '{Single.docs_dir}'."
        with pytest.raises(ValueError, match=re.escape(expected_error_msg)):
            single.abs_src_path = outside_path

    def test_single_init_from_root_index_file(self, mock_config_for_single_init):
        """Tests initialization for an index file directly under a post type."""
        config = mock_config_for_single_init
        
        (config.docs_dir / 'article').mkdir(exist_ok=True)
        src_file = config.docs_dir / 'article' / 'index.md'
        src_file.touch()

        single = Single(src_file, config)

        assert single.abs_src_path == src_file
        assert single.src_path == Path('article/index.md')
        assert single.id == PurePath('/docs/article/index.md')
        assert single.post_type == 'article'
        assert single.src_dir == Path('article')
        assert single.filename == 'index'
        assert single.ext == 'md'
        assert single.is_root is True

    def test_single_init_from_nested_file(self, mock_config_for_single_init):
        """Tests initialization for a file in a nested directory."""
        config = mock_config_for_single_init
        
        (config.docs_dir / 'article' / '2023' / '10').mkdir(parents=True, exist_ok=True)
        src_file = config.docs_dir / 'article' / '2023' / '10' / 'nested-post.md'
        src_file.touch()

        single = Single(src_file, config)

        assert single.abs_src_path == src_file
        assert single.src_path == Path('article/2023/10/nested-post.md')
        assert single.id == PurePath('/docs/article/2023/10/nested-post.md')
        assert single.post_type == 'article'
        assert single.src_dir == Path('article/2023/10')
        assert single.filename == 'nested-post'
        assert single.ext == 'md'
        assert single.is_root is False


class TestJinja2ShortcodesInContent:
    @pytest.fixture
    def single_with_jinja_content(self, tmp_path):
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        
        original_docs_dir = Single.docs_dir
        Single.docs_dir = docs_dir

        cfg = Config()
        cfg.docs_dir = docs_dir
        cfg.post_type.update({'post': {}})
        
        post_dir = docs_dir / "post"
        post_dir.mkdir()
        
        content_with_jinja = """
---
title: My Shortcode Post
---
Hello, {{ mypage.title }}! The year is {{ config.now.year }}.
"""
        src_file = post_dir / "test-shortcode.md"
        src_file.write_text(content_with_jinja, encoding="utf-8")

        single = Single(src_file, cfg)
        single.meta, doc_content = Single.parse_front_matter(src_file)
        single.title = single.meta.get('title', 'Default Title')
        single.content = doc_content
        single.slug = 'my-shortcode-post'
        single.date = datetime.datetime(2023, 1, 1)
        cfg.now = datetime.datetime(2023, 5, 15)

        yield single, cfg

        Single.docs_dir = original_docs_dir


    def test_jinja2_shortcode_in_content_rendering(self, single_with_jinja_content, mocker):
        single, config = single_with_jinja_content

        test_env = jinja2.Environment(loader=jinja2.FileSystemLoader(single.abs_src_path.parent))
        test_env.globals.update({
            'config': config,
            'mypage': single
        })
        config.env = test_env

        mock_themes = mocker.MagicMock()
        mock_themes.lookup_template.return_value = "single.html"
        
        dummy_theme_path = single.abs_src_path.parent.parent / "dummy_theme"
        (dummy_theme_path / "import").mkdir(parents=True, exist_ok=True)
        (dummy_theme_path / "import" / "short-code.html").touch()
        mock_themes.dirs = [dummy_theme_path]

        mock_archives = mocker.MagicMock()
        mock_singles_container = mocker.MagicMock()
        mock_singles_container.config = config
        # Configure plugins.do_action to return the original content to prevent it from being overwritten by a mock.
        mock_plugins = mocker.MagicMock()
        mock_plugins.do_action.side_effect = lambda *args, **kwargs: kwargs.get('target')
        mock_singles_container.plugins = mock_plugins

        mock_main_template_object = mocker.MagicMock()
        mock_main_template_object.render.return_value = "FINAL RENDERED HTML"
        mock_shortcode_template_object = mocker.MagicMock()

        def get_template_side_effect(template_name, parent=None):
            if template_name == "single.html":
                return mock_main_template_object
            elif template_name == "import/short-code.html":
                return mock_shortcode_template_object
            pytest.fail(f"Unexpected template requested: {template_name}")

        with patch.object(config.env, 'get_template', side_effect=get_template_side_effect) as mock_get_template:
            single.update_html(mock_singles_container, mock_archives, mock_themes)

            # This is the core assertion for shortcode rendering.
            expected_rendered_content = "Hello, My Shortcode Post! The year is 2023."
            assert single.content.strip() == expected_rendered_content   

            assert single.html == "FINAL RENDERED HTML"

            # Ensure the main template was called with the correctly rendered content.
            main_render_context = mock_main_template_object.render.call_args[0][0]
            assert main_render_context['mypage'].content.strip() == expected_rendered_content

            # Check that get_template was called for both the main and imported templates.
            assert mock_get_template.call_count == 2
            mock_get_template.assert_any_call("single.html")
            mock_get_template.assert_any_call("import/short-code.html", None)


class TestGetSummary:
    @pytest.mark.parametrize("content, meta_summary, expected", [
        # Basic HTML stripping
        (
            "<p>This is <b>content</b>.</p>\nHere is more.",
            None,
            "This is content.Here is more."
        ),
        # Stripping script and style tags
        (
            "Content with <script>alert('xss');</script> and <style>body{color:red}</style> tags.",
            None,
            "Content with  and  tags."
        ),
        # Replacing special characters
        (
            "Path is /a/b/c. It's a quote \" and backslash \\.",
            None,
            "Path is  a b c. It s a quote   and backslash  ."
        ),
        # Truncation
        (
            "This is a very long string designed to test the truncation functionality of the summary generation. It should be cut off at exactly 110 characters, not before and not after. Let's see if it works as expected.",
            None,
            "This is a very long string designed to test the truncation functionality of the summary generation. It should "
        ),
        # Using meta.summary (should ignore content and truncation)
        (
            "This content should be ignored.",
            "This is a custom summary from the front matter.",
            "This is a custom summary from the front matter."
        ),
        # Empty content
        (
            "",
            None,
            ""
        )
    ])
    def test_get_summary_scenarios(self, single_obj, content, meta_summary, expected):
        """Tests the _get_summary method with various scenarios."""
        single_obj.content = content
        if meta_summary:
            single_obj.meta['summary'] = meta_summary
        
        summary = single_obj._get_summary()
        
        assert summary == expected


class TestSinglesSetup:
    def test_setup_prev_next_page(self, config):
        """
        Tests that _setup_prev_next_page correctly links adjacent pages.
        """
        mock_plugins = MagicMock()
        singles = Singles(config, mock_plugins)  # pages is initially empty

        # Create three mock pages
        page1 = MagicMock(spec=Single, name="Page 1")
        page2 = MagicMock(spec=Single, name="Page 2")
        page3 = MagicMock(spec=Single, name="Page 3")
        singles.pages = [page1, page2, page3]

        singles._setup_prev_next_page()

        # Check links for Page 1
        assert page1.prev_page is None
        assert page1.next_page is page2

        # Check links for Page 2
        assert page2.prev_page is page1
        assert page2.next_page is page3

        # Check links for Page 3
        assert page3.prev_page is page2
        assert page3.next_page is None

    def test_setup_prev_next_page_with_single_page(self, config):
        """
        Tests that _setup_prev_next_page works correctly with only one page.
        """
        mock_plugins = MagicMock()
        singles = Singles(config, mock_plugins)  # pages is initially empty

        page1 = MagicMock(spec=Single, name="Page 1")
        singles.pages = [page1]

        singles._setup_prev_next_page()

        # Check links for the single page
        assert page1.prev_page is None
        assert page1.next_page is None

