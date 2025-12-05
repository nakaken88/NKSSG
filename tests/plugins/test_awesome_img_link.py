import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import shutil

from nkssg.structure.config import Config
from nkssg.structure.singles import Singles, Single
from nkssg.plugins.awesome_img_link import AwesomeImgLinkPlugin


@pytest.fixture
def mock_config(tmp_path):
    """Fixture for a mock Config object with necessary paths."""
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
    """Fixture to create a mock Single page with a given HTML content."""
    def _create_mock_page(html_content, src_path_name="post.md"):
        page = MagicMock(spec=Single)
        page.html = html_content
        page.src_path = mock_config.docs_dir / src_path_name
        page.dest_dir = mock_config.public_dir / page.src_path.stem
        page.dest_dir.mkdir(exist_ok=True)
        page.imgs = [] # Ensure imgs list is initialized
        return page
    return _create_mock_page

@pytest.fixture
def mock_singles(mock_config, create_mock_page):
    """Fixture for a mock Singles collection."""
    singles = MagicMock(spec=Singles)
    singles.config = mock_config
    return singles


def test_image_with_keyword_is_processed_and_copied(mock_config, mock_singles, create_mock_page):
    """
    Test that an image with the keyword is processed (src rewritten)
    and copied to the public directory.
    """
    # Setup: Create a dummy image file in docs
    image_dir_in_docs = mock_config.docs_dir / "images"
    image_dir_in_docs.mkdir()
    dummy_image_path_src = image_dir_in_docs / "dummy.png"
    dummy_image_path_src.touch()

    # Create a page with an image link ending with '?'
    html_content = f'<p>Some text</p><img src="/images/dummy.png?"><p>More text</p>'
    page = create_mock_page(html_content)
    mock_singles.__iter__.return_value = [page] # Make Singles iterable

    # 1. Test after_update_singles_html
    plugin = AwesomeImgLinkPlugin()
    plugin.config = {}
    plugin.after_update_singles_html(mock_singles)

    # Assert HTML src is rewritten
    assert page.html == '<p>Some text</p><img src="./dummy.png"><p>More text</p>'
    # Assert page.imgs contains correct info
    assert len(page.imgs) == 1
    assert page.imgs[0]['old_path'] == mock_config.docs_dir / "images" / "dummy.png"
    assert page.imgs[0]['new_path'] == page.dest_dir / "dummy.png"

    # 2. Test after_output_singles
    # Mock site to pass to after_output_singles
    site = MagicMock()
    site.config = mock_config
    site.singles = mock_singles # Assume singles is already updated with page.imgs

    plugin.after_output_singles(site)

    # Assert image is copied to the destination
    expected_copied_image_path = page.dest_dir / "dummy.png"
    assert expected_copied_image_path.exists()


def test_image_without_keyword_is_ignored(mock_config, mock_singles, create_mock_page):
    """
    Test that an image without the keyword is not processed or copied.
    """
    # Create a page with an image link without '?'
    original_html_content = f'<p>Some text</p><img src="/images/dummy.png"><p>More text</p>'
    page = create_mock_page(original_html_content)
    mock_singles.__iter__.return_value = [page]

    plugin = AwesomeImgLinkPlugin()
    plugin.config = {}
    plugin.after_update_singles_html(mock_singles)

    # Assert HTML content is unchanged
    assert page.html == original_html_content
    # Assert no image info is added
    assert not hasattr(page, 'imgs') or len(page.imgs) == 0

    # Ensure no image is copied by after_output_singles (implicitly, as no imgs were processed)
    site = MagicMock()
    site.config = mock_config
    site.singles = mock_singles
    plugin.after_output_singles(site)
    
    expected_copied_image_path = page.dest_dir / "dummy.png"
    assert not expected_copied_image_path.exists() # Should not exist


def test_relative_path_image_is_processed(mock_config, mock_singles, create_mock_page):
    """
    Test that an image referenced by a relative path from the page's source
    is processed (src rewritten) and copied to the public directory.
    """
    # Setup: Create a directory structure similar to docs/post/2021/img/sample.png
    post_dir_in_docs = mock_config.docs_dir / "post" / "2021"
    image_dir_in_docs = post_dir_in_docs / "img"
    image_dir_in_docs.mkdir(parents=True)
    dummy_image_path_src = image_dir_in_docs / "sample.png"
    dummy_image_path_src.touch()

    # Create a page (20210401.md) in post_dir_in_docs
    # with an image link using a relative path './img/sample.png?'
    html_content = f'<p>Image: <img src="./img/sample.png?"></p>'
    page = create_mock_page(html_content, src_path_name="post/2021/20210401.md")
    # Adjust dest_dir for the mock page to reflect the actual output structure
    # For permalink /%Y/%m/%d/, it would be public/post/2021/04/01/
    page.dest_dir = mock_config.public_dir / "post" / "2021" / "04" / "01"
    page.dest_dir.mkdir(parents=True, exist_ok=True)


    mock_singles.__iter__.return_value = [page] # Make Singles iterable

    # 1. Test after_update_singles_html
    plugin = AwesomeImgLinkPlugin()
    plugin.config = {}
    plugin.after_update_singles_html(mock_singles)

    # Assert HTML src is rewritten to ./sample.png
    assert page.html == '<p>Image: <img src="./sample.png"></p>'
    # Assert page.imgs contains correct info
    assert len(page.imgs) == 1
    assert page.imgs[0]['old_path'] == dummy_image_path_src
    assert page.imgs[0]['new_path'] == page.dest_dir / "sample.png"

    # 2. Test after_output_singles
    site = MagicMock()
    site.config = mock_config
    site.singles = mock_singles

    plugin.after_output_singles(site)

    # Assert image is copied to the destination
    expected_copied_image_path = page.dest_dir / "sample.png"
    assert expected_copied_image_path.exists()





def test_non_existent_source_image_is_handled(mock_config, mock_singles, create_mock_page, capsys):
    """
    Test that if the source image does not exist, an error is logged but
    the process does not crash.
    """
    # No dummy image created in docs, so it won't exist

    html_content = f'<img src="/non_existent_images/notfound.gif?">'
    page = create_mock_page(html_content)
    mock_singles.__iter__.return_value = [page]

    plugin = AwesomeImgLinkPlugin()
    plugin.config = {}
    plugin.after_update_singles_html(mock_singles)

    # The HTML should still be rewritten, as that's done first
    assert page.html == '<img src="./notfound.gif">'
    assert len(page.imgs) == 1

    site = MagicMock()
    site.config = mock_config
    site.singles = mock_singles
    
    plugin.after_output_singles(site)
    
    # Assert that an error message was printed to stdout
    captured = capsys.readouterr()
    assert "is not found" in captured.out
    
    # Assert that the non-existent image was not copied
    expected_copied_image_path = page.dest_dir / "notfound.gif"
    assert not expected_copied_image_path.exists()
