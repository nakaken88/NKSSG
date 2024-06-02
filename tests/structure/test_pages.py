from pathlib import Path
import pytest

from nkssg.config import Config
from nkssg.structure.pages import Page


@pytest.mark.parametrize("input, expected", [
    ('sample', 'sample'),       # unchange (no _)
    ('_10_sample', 'sample'),   # drop prefix
    ('_sample', '_sample'),     # unchange (one _)
    ('_sample_', '_sample_'),   # unchange (end with _, no suffix)
    ('_a_b_c', 'b_c'),          # case three _
    ('_a_b_', 'b_'),            # case three _ (end with _)
    ('a_b_c', 'a_b_c'),         # unchange (not start with _)
    ('_!@#_a b c', 'a b c'),    # special words
    ('__sample', '_sample'),    # start __
    ('___sample', '__sample'),  # start ___
    ('_____', '____'),          # only _
    ('', ''),                   # no words
])
def test_clean_name(input, expected):
    assert Page.clean_name(input) == expected


@pytest.mark.parametrize("dirty_slug, expected", [
    ('sample', 'sample'),       # unchange
    ('a b c', 'a-b-c'),         # space
    ('Sample', 'sample'),       # upper case
    ('A of C', 'a-of-c'),       # space + upper case
    ('a  b   c', 'a--b---c'),   # multi space
    ('a!b@c', 'a!b@c'),         # special words
])
def test_to_slug(dirty_slug, expected):
    assert Page.to_slug(dirty_slug) == expected


@pytest.mark.parametrize("dest_path, expected", [
    ('index.html', '/'),                # site top
    ('a/b/c/index.html', '/a/b/c/'),    # normal page
    ('sample.html', '/sample.html'),    # x.html in top
    ('a/b/c.html', '/a/b/c.html'),      # x.html in sub folder
    ('A/B/C/index.html', '/a/b/c/'),    # upper case
    ('a b/index.html', '/a%20b/'),      # path with space
    ('a//b//c/index.html', '/a/b/c/'),  # multiple slashes
    ('folder/', '/folder/'),            # folder in root
    ('a/subfolder/', '/a/subfolder/'),  # nested folder in root
])
def test_get_url_from_dest(dest_path, expected):
    page = Page()
    assert page._get_url_from_dest(dest_path) == expected


@pytest.mark.parametrize("dest_path", [
    (''),  # empty string
])
def test_get_url_from_dest_error(dest_path):
    page = Page()
    page.dest_path = ''
    with pytest.raises(ValueError):
        page._get_url_from_dest(dest_path)


@pytest.mark.parametrize("url, expected", [
    ('/', 'index.html'),                           # site top
    ('/a/b/c/', 'a/b/c/index.html'),               # normal page
    ('/sample.html', 'sample.html'),               # x.html in top
    ('/a/b/c.html', 'a/b/c.html'),                 # x.html in sub folder
    ('/A/B/C/', 'A/B/C/index.html'),               # upper case
    ('/a%20b/', 'a b/index.html'),                 # path with space
    ('/a//b///c/', 'a/b/c/index.html'),            # multiple slashes
    ('/folder/', 'folder/index.html'),             # folder in root
    ('/a/subfolder/', 'a/subfolder/index.html'),   # nested folder in root
])
def test_get_dest_from_url(url, expected):
    page = Page()
    assert page._get_dest_from_url(url) == Path(expected)


@pytest.mark.parametrize(
    "site_url, use_abs_url, rel_url, expected_abs_url, expected_url",
    [
        # site_url is not empty
        ('http://example.com', False, '/path/to/page',
         'http://example.com/path/to/page', '/path/to/page'),
        ('http://example.com', True, '/path/to/page',
         'http://example.com/path/to/page', 'http://example.com/path/to/page'),
        # site_url is empty
        ('', False, '/path/to/page', '/path/to/page', '/path/to/page'),
        ('', True, '/path/to/page', '/path/to/page', '/path/to/page'),
    ]
)
def test_url_setup(
        site_url, use_abs_url, rel_url, expected_abs_url, expected_url):

    config = Config()
    config.site.site_url = site_url
    config.use_abs_url = use_abs_url

    page = Page()
    page.rel_url = rel_url
    page._url_setup(config)

    assert page.abs_url == expected_abs_url
    assert page.url == expected_url
