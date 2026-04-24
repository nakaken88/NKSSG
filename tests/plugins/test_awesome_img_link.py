import pytest
from unittest.mock import MagicMock

from nkssg.structure.config import Config
from nkssg.structure.singles import Singles, Single
from nkssg.plugins.awesome_img_link import AwesomeImgLinkPlugin


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
    def _create_mock_page(html_content, src_path_name="post.md"):
        page = MagicMock(spec=Single)
        page.html = html_content
        page.src_path = mock_config.docs_dir / src_path_name
        page.dest_dir = mock_config.public_dir / page.src_path.stem
        page.dest_dir.mkdir(exist_ok=True)
        page.imgs = []
        return page
    return _create_mock_page

@pytest.fixture
def mock_singles(mock_config, create_mock_page):
    singles = MagicMock(spec=Singles)
    singles.config = mock_config
    return singles


def test_image_with_keyword_is_processed_and_copied(mock_config, mock_singles, create_mock_page):
    image_dir_in_docs = mock_config.docs_dir / "images"
    image_dir_in_docs.mkdir()
    dummy_image_path_src = image_dir_in_docs / "dummy.png"
    dummy_image_path_src.touch()

    html_content = '<p>Some text</p><img src="/images/dummy.png?"><p>More text</p>'
    page = create_mock_page(html_content)
    mock_singles.__iter__.return_value = [page]

    # 1. Test after_update_singles_html
    plugin = AwesomeImgLinkPlugin()
    plugin.config = {}
    plugin.after_update_singles_html(mock_singles)

    assert page.html == '<p>Some text</p><img src="./dummy.png"><p>More text</p>'
    assert len(page.imgs) == 1
    assert page.imgs[0]['old_path'] == mock_config.docs_dir / "images" / "dummy.png"
    assert page.imgs[0]['new_path'] == page.dest_dir / "dummy.png"

    # 2. Test after_output_singles
    site = MagicMock()
    site.config = mock_config
    site.singles = mock_singles

    plugin.after_output_singles(site)

    assert (page.dest_dir / "dummy.png").exists()


def test_image_without_keyword_is_ignored(mock_config, mock_singles, create_mock_page):
    original_html_content = '<p>Some text</p><img src="/images/dummy.png"><p>More text</p>'
    page = create_mock_page(original_html_content)
    mock_singles.__iter__.return_value = [page]

    plugin = AwesomeImgLinkPlugin()
    plugin.config = {}
    plugin.after_update_singles_html(mock_singles)

    assert page.html == original_html_content
    assert not hasattr(page, 'imgs') or len(page.imgs) == 0

    site = MagicMock()
    site.config = mock_config
    site.singles = mock_singles
    plugin.after_output_singles(site)

    assert not (page.dest_dir / "dummy.png").exists()


def test_relative_path_image_is_processed(mock_config, mock_singles, create_mock_page):
    post_dir_in_docs = mock_config.docs_dir / "post" / "2021"
    image_dir_in_docs = post_dir_in_docs / "img"
    image_dir_in_docs.mkdir(parents=True)
    dummy_image_path_src = image_dir_in_docs / "sample.png"
    dummy_image_path_src.touch()

    html_content = '<p>Image: <img src="./img/sample.png?"></p>'
    page = create_mock_page(html_content, src_path_name="post/2021/20210401.md")
    # Adjust dest_dir for the mock page to reflect the actual output structure
    # For permalink /%Y/%m/%d/, it would be public/post/2021/04/01/
    page.dest_dir = mock_config.public_dir / "post" / "2021" / "04" / "01"
    page.dest_dir.mkdir(parents=True, exist_ok=True)

    mock_singles.__iter__.return_value = [page]

    # 1. Test after_update_singles_html
    plugin = AwesomeImgLinkPlugin()
    plugin.config = {}
    plugin.after_update_singles_html(mock_singles)

    assert page.html == '<p>Image: <img src="./sample.png"></p>'
    assert len(page.imgs) == 1
    assert page.imgs[0]['old_path'] == dummy_image_path_src
    assert page.imgs[0]['new_path'] == page.dest_dir / "sample.png"

    # 2. Test after_output_singles
    site = MagicMock()
    site.config = mock_config
    site.singles = mock_singles

    plugin.after_output_singles(site)

    assert (page.dest_dir / "sample.png").exists()


def test_non_existent_source_image_is_handled(mock_config, mock_singles, create_mock_page, capsys):
    html_content = '<img src="/non_existent_images/notfound.gif?">'
    page = create_mock_page(html_content)
    mock_singles.__iter__.return_value = [page]

    plugin = AwesomeImgLinkPlugin()
    plugin.config = {}
    plugin.after_update_singles_html(mock_singles)

    assert page.html == '<img src="./notfound.gif">'
    assert len(page.imgs) == 1

    site = MagicMock()
    site.config = mock_config
    site.singles = mock_singles

    plugin.after_output_singles(site)

    captured = capsys.readouterr()
    assert "is not found" in captured.out

    assert not (page.dest_dir / "notfound.gif").exists()


def test_draft_mode_skips_processing(mock_config, mock_singles, create_mock_page):
    mock_config.get.side_effect = lambda key, default=None: {
        'mode': 'draft',
        'keyword': '?',
        'strip_paths': []
    }.get(key, default)

    html_content = '<img src="/images/dummy.png?">'
    page = create_mock_page(html_content)
    mock_singles.__iter__.return_value = [page]

    plugin = AwesomeImgLinkPlugin()
    plugin.config = {}
    plugin.after_update_singles_html(mock_singles)

    assert page.html == html_content
