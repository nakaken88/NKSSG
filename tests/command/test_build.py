import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from nkssg.command.build import build
from nkssg.structure.config import Config


@pytest.fixture
def mock_config():
    """Fixture to create a mock Config object."""
    config = MagicMock(spec=Config)
    mock_public_dir = MagicMock(spec=Path)
    mock_public_dir.exists.return_value = False
    config.public_dir = mock_public_dir
    return config


@patch('nkssg.command.build.Site')
@patch('nkssg.command.build.shutil')
def test_build_function_calls_site_methods_and_creates_public_dir(
    mock_shutil, MockSite, mock_config
):
    """
    Test that the build function correctly orchestrates the Site methods
    and creates the public directory.
    """
    mock_site_instance = MockSite.return_value
    
    build(mock_config, clean=False)

    MockSite.assert_called_once_with(mock_config)
    mock_site_instance.setup.assert_called_once()
    mock_site_instance.update.assert_called_once()
    mock_site_instance.output.assert_called_once()

    mock_config.public_dir.mkdir.assert_called_once_with(exist_ok=True)
    mock_shutil.rmtree.assert_not_called()


@patch('nkssg.command.build.Site')
@patch('nkssg.command.build.shutil')
def test_build_function_cleans_public_dir_when_clean_is_true(
    mock_shutil, MockSite, mock_config
):
    """
    Test that the build function removes the public directory when clean=True.
    """
    mock_config.public_dir.exists.return_value = True
    mock_site_instance = MockSite.return_value

    build(mock_config, clean=True)

    mock_shutil.rmtree.assert_called_once_with(mock_config.public_dir)
    mock_config.public_dir.mkdir.assert_called_once_with(exist_ok=True)
    
    MockSite.assert_called_once_with(mock_config)
    mock_site_instance.setup.assert_called_once()
    mock_site_instance.update.assert_called_once()
    mock_site_instance.output.assert_called_once()


@patch('nkssg.command.build.Site')
@patch('nkssg.command.build.shutil')
def test_build_function_does_not_remove_public_dir_if_not_exists_and_clean_is_true(
    mock_shutil, MockSite, mock_config
):
    """
    Test that the build function does not try to remove public_dir
    if it doesn't exist, even when clean=True.
    """
    mock_config.public_dir.exists.return_value = False
    mock_site_instance = MockSite.return_value

    build(mock_config, clean=True)

    mock_shutil.rmtree.assert_not_called()
    mock_config.public_dir.mkdir.assert_called_once_with(exist_ok=True)

    MockSite.assert_called_once_with(mock_config)
    mock_site_instance.setup.assert_called_once()
    mock_site_instance.update.assert_called_once()
    mock_site_instance.output.assert_called_once()
