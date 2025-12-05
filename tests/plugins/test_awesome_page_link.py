import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import shutil

from nkssg.structure.config import Config
from nkssg.structure.pages import Page
from nkssg.structure.singles import Singles
from nkssg.structure.site import Site
from nkssg.plugins.awesome_page_link import AwesomePageLinkPlugin


@pytest.fixture
def mock_config(tmp_path):
    """Fixture for a mock Config object."""
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
    """Fixture to create a mock Page (Single or Archive) with content."""
    def _create_mock_page(content, src_path_name="post.md", url="/post/test-post/"):
        page = MagicMock(spec=Page)
        page.content = content # Page content (HTML/Markdown)
        page.src_path = mock_config.docs_dir / src_path_name
        page.url = url
        page.src_path.parent.mkdir(parents=True, exist_ok=True)
        return page
    return _create_mock_page

@pytest.fixture
def mock_singles_and_site(mock_config, create_mock_page):
    """Fixture for a mock Singles collection and Site object."""
    # Create some dummy pages for resolution
    page_a = create_mock_page("Content for page A", "page_a.md", "/page/a/")
    page_b = create_mock_page("Content for page B", "sub/page_b.md", "/sub/page/b/")
    page_c = create_mock_page("Content for page C", "page_c.md", "/page/c/")

    # Mock Singles collection
    singles = MagicMock(spec=Singles)
    singles.config = mock_config
    singles.__iter__.return_value = [page_a, page_b, page_c]
    
    # Simulate src_paths and file_ids mapping
    singles.src_paths = {
        page.src_path.relative_to(mock_config.docs_dir).as_posix(): page
        for page in [page_a, page_b, page_c]
    }
    singles.file_ids = {
        "page_a": page_a,
        "page_b_id": page_b, # Example of different file_id
    }

    # Mock Site object
    site = MagicMock(spec=Site)
    site.config = mock_config
    site.singles = singles
    site.archives = [] # Not testing archives specifically here

    return singles, site


def test_relative_path_link_with_keyword_is_resolved(mock_config, mock_singles_and_site, create_mock_page):
    """
    Test that a relative path link with the keyword is resolved to the correct URL.
    """
    singles, site = mock_singles_and_site
    
    # Create a page with a relative link to 'page_a.md?'
    original_content = f'<p>Link to <a href="page_a.md?">Page A</a></p>'
    test_page = create_mock_page(original_content, "current_page.md")
    singles.__iter__.return_value = [test_page, singles.src_paths['page_a.md']] # Ensure page_a is in singles

    plugin = AwesomePageLinkPlugin()
    plugin.config = {}
    plugin.site = site # Plugin needs site reference
    plugin.after_update_urls(site)

    # Assert href is rewritten to the correct URL
    assert test_page.content == '<p>Link to <a href="/page/a/">Page A</a></p>'


def test_id_based_link_with_keyword_is_resolved(mock_config, mock_singles_and_site, create_mock_page):
    """
    Test that an ID-based link with the keyword is resolved to the correct URL.
    """
    singles, site = mock_singles_and_site

    # Create a page with an ID-based link to ':page_b_id?'
    original_content = f'<p>Link to <a href=":page_b_id?">Page B</a></p>'
    test_page = create_mock_page(original_content, "current_page.md")
    singles.__iter__.return_value = [test_page, singles.file_ids['page_b_id']]

    plugin = AwesomePageLinkPlugin()
    plugin.config = {}
    plugin.site = site
    plugin.after_update_urls(site)

    # Assert href is rewritten to the correct URL
    assert test_page.content == '<p>Link to <a href="/sub/page/b/">Page B</a></p>'


def test_link_without_keyword_is_ignored(mock_config, mock_singles_and_site, create_mock_page):
    """
    Test that a link without the keyword is not processed.
    """
    singles, site = mock_singles_and_site

    # Create a page with a normal link
    original_content = f'<p>Link to <a href="external.html">External</a></p>'
    test_page = create_mock_page(original_content, "current_page.md")
    singles.__iter__.return_value = [test_page]

    plugin = AwesomePageLinkPlugin()
    plugin.config = {}
    plugin.site = site
    plugin.after_update_urls(site)

    # Assert content remains unchanged
    assert test_page.content == original_content


def test_strip_paths_option_works(mock_config, mock_singles_and_site, create_mock_page):
    """
    Test that the strip_paths configuration correctly modifies the link source.
    """
    singles, site = mock_singles_and_site
    # Create a dummy page for resolution that has 'posts/' in its path
    page_x = create_mock_page("Content for page X", "posts/page_x.md", "/posts/x/")
    singles.src_paths["posts/page_x.md"] = page_x
    singles.__iter__.return_value = [page_x]
    # Create a page with a link that should be stripped, now from 'docs/'
    original_content = f'<p>Link to <a href="docs/posts/page_x.md?">Page X</a></p>'
    test_page = create_mock_page(original_content, "current_page.md")
    singles.__iter__.return_value = [test_page, page_x]
    plugin = AwesomePageLinkPlugin()
    plugin.config = {'strip_paths': ['docs/']}
    plugin.site = site
    plugin.after_update_urls(site)
    # Assert href is rewritten correctly, expecting it to resolve to the full URL
    assert test_page.content == '<p>Link to <a href="/posts/x/">Page X</a></p>'


def test_non_existent_id_link_raises_error(mock_config, mock_singles_and_site, create_mock_page):
    """
    Test that an ID-based link to a non-existent ID raises a ValueError.
    """
    singles, site = mock_singles_and_site

    original_content = f'<p>Link to <a href=":non_existent_id?">Non Existent</a></p>'
    test_page = create_mock_page(original_content, "current_page.md")
    singles.__iter__.return_value = [test_page]

    plugin = AwesomePageLinkPlugin()
    plugin.config = {}
    plugin.site = site
    
    with pytest.raises(ValueError, match=r'File ID "non_existent_id" is not found on .*'):
        plugin.after_update_urls(site)


def test_non_existent_path_link_is_not_resolved_and_keeps_original(mock_config, mock_singles_and_site, create_mock_page):
    """
    Test that a path link to a non-existent file is not resolved and keeps its original href.
    """
    singles, site = mock_singles_and_site

    original_content = f'<p>Link to <a href="non_existent_file.md?">Non Existent File</a></p>'
    test_page = create_mock_page(original_content, "current_page.md")
    singles.__iter__.return_value = [test_page]

    plugin = AwesomePageLinkPlugin()
    plugin.config = {}
    plugin.site = site
    plugin.after_update_urls(site)

    # The current plugin behavior for non-existent path links is to return the path
    # with the keyword and suffix removed.
    assert test_page.content == '<p>Link to <a href="non_existent_file.md">Non Existent File</a></p>'
