import pytest
from unittest.mock import MagicMock

from nkssg.structure.config import Config
from nkssg.structure.pages import Page
from nkssg.structure.singles import Singles
from nkssg.structure.site import Site
from nkssg.plugins.awesome_page_link import AwesomePageLinkPlugin


@pytest.fixture
def mock_config(tmp_path):
    config = MagicMock(spec=Config)
    config.docs_dir = tmp_path / "docs"
    config.public_dir = tmp_path / "public"
    config.docs_dir.mkdir()
    config.public_dir.mkdir()
    config.get.side_effect = lambda key, default=None: {
        'mode': 'build',
        'keyword': '?',
        'strip_paths': []
    }.get(key, default)
    return config

@pytest.fixture
def create_mock_page(mock_config):
    def _create_mock_page(content, src_path_name="post.md", url="/post/test-post/"):
        page = MagicMock(spec=Page)
        page.content = content
        page.src_path = mock_config.docs_dir / src_path_name
        page.url = url
        page.src_path.parent.mkdir(parents=True, exist_ok=True)
        return page
    return _create_mock_page

@pytest.fixture
def mock_singles_and_site(mock_config, create_mock_page):
    page_a = create_mock_page("Content for page A", "page_a.md", "/page/a/")
    page_b = create_mock_page("Content for page B", "sub/page_b.md", "/sub/page/b/")
    page_c = create_mock_page("Content for page C", "page_c.md", "/page/c/")

    singles = MagicMock(spec=Singles)
    singles.config = mock_config
    singles.__iter__.return_value = [page_a, page_b, page_c]

    singles.src_paths = {
        page.src_path.relative_to(mock_config.docs_dir).as_posix(): page
        for page in [page_a, page_b, page_c]
    }
    singles.file_ids = {
        "page_a": page_a,
        "page_b_id": page_b,
    }

    site = MagicMock(spec=Site)
    site.config = mock_config
    site.singles = singles
    site.archives = []

    return singles, site


def test_relative_path_link_with_keyword_is_resolved(mock_config, mock_singles_and_site, create_mock_page):
    singles, site = mock_singles_and_site

    original_content = '<p>Link to <a href="page_a.md?">Page A</a></p>'
    test_page = create_mock_page(original_content, "current_page.md")
    singles.__iter__.return_value = [test_page, singles.src_paths['page_a.md']]

    plugin = AwesomePageLinkPlugin()
    plugin.config = {}
    plugin.site = site
    plugin.after_update_urls(site)

    assert test_page.content == '<p>Link to <a href="/page/a/">Page A</a></p>'


def test_id_based_link_with_keyword_is_resolved(mock_config, mock_singles_and_site, create_mock_page):
    singles, site = mock_singles_and_site

    original_content = '<p>Link to <a href=":page_b_id?">Page B</a></p>'
    test_page = create_mock_page(original_content, "current_page.md")
    singles.__iter__.return_value = [test_page, singles.file_ids['page_b_id']]

    plugin = AwesomePageLinkPlugin()
    plugin.config = {}
    plugin.site = site
    plugin.after_update_urls(site)

    assert test_page.content == '<p>Link to <a href="/sub/page/b/">Page B</a></p>'


def test_link_without_keyword_is_ignored(mock_config, mock_singles_and_site, create_mock_page):
    singles, site = mock_singles_and_site

    original_content = '<p>Link to <a href="external.html">External</a></p>'
    test_page = create_mock_page(original_content, "current_page.md")
    singles.__iter__.return_value = [test_page]

    plugin = AwesomePageLinkPlugin()
    plugin.config = {}
    plugin.site = site
    plugin.after_update_urls(site)

    assert test_page.content == original_content


def test_strip_paths_option_works(mock_config, mock_singles_and_site, create_mock_page):
    singles, site = mock_singles_and_site
    page_x = create_mock_page("Content for page X", "posts/page_x.md", "/posts/x/")
    singles.src_paths["posts/page_x.md"] = page_x

    original_content = '<p>Link to <a href="docs/posts/page_x.md?">Page X</a></p>'
    test_page = create_mock_page(original_content, "current_page.md")
    singles.__iter__.return_value = [test_page, page_x]

    plugin = AwesomePageLinkPlugin()
    plugin.config = {'strip_paths': ['docs/']}
    plugin.site = site
    plugin.after_update_urls(site)

    assert test_page.content == '<p>Link to <a href="/posts/x/">Page X</a></p>'


def test_non_existent_id_link_raises_error(mock_config, mock_singles_and_site, create_mock_page):
    singles, site = mock_singles_and_site

    original_content = '<p>Link to <a href=":non_existent_id?">Non Existent</a></p>'
    test_page = create_mock_page(original_content, "current_page.md")
    singles.__iter__.return_value = [test_page]

    plugin = AwesomePageLinkPlugin()
    plugin.config = {}
    plugin.site = site

    with pytest.raises(ValueError, match=r'File ID "non_existent_id" is not found on .*'):
        plugin.after_update_urls(site)


def test_non_existent_path_link_is_not_resolved_and_keeps_original(mock_config, mock_singles_and_site, create_mock_page):
    singles, site = mock_singles_and_site

    original_content = '<p>Link to <a href="non_existent_file.md?">Non Existent File</a></p>'
    test_page = create_mock_page(original_content, "current_page.md")
    singles.__iter__.return_value = [test_page]

    plugin = AwesomePageLinkPlugin()
    plugin.config = {}
    plugin.site = site
    plugin.after_update_urls(site)

    # The current plugin behavior for non-existent path links is to return the path
    # with the keyword and suffix removed.
    assert test_page.content == '<p>Link to <a href="non_existent_file.md">Non Existent File</a></p>'


def test_draft_mode_skips_processing(mock_config, mock_singles_and_site, create_mock_page):
    singles, site = mock_singles_and_site
    site.config.get.side_effect = lambda key, default=None: {
        'mode': 'draft',
        'keyword': '?',
        'strip_paths': []
    }.get(key, default)

    original_content = '<p>Link to <a href="page_a.md?">Page A</a></p>'
    test_page = create_mock_page(original_content, "current_page.md")
    singles.__iter__.return_value = [test_page]

    plugin = AwesomePageLinkPlugin()
    plugin.config = {}
    plugin.after_update_urls(site)

    assert test_page.content == original_content
