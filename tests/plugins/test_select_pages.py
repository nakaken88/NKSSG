import pytest
from unittest.mock import MagicMock, patch

from nkssg.plugins.select_pages import SelectPagesPlugin
from nkssg.structure.config import Config
from nkssg.structure.singles import Singles, Single
from nkssg.structure.plugins import Plugins

@pytest.fixture
def plugin():
    return SelectPagesPlugin()

@pytest.fixture
def singles_with_pages():
    # Patch the method that reads from the filesystem during initialization
    with patch.object(Singles, 'get_pages_from_docs_directory', return_value=[]):
        mock_plugins = MagicMock(spec=Plugins)
        singles = Singles(Config(), mock_plugins)

    singles.pages = [MagicMock(spec=Single) for _ in range(10)]
    return singles

def test_not_serve_mode(plugin, singles_with_pages):
    singles_with_pages.config['mode'] = 'build'
    plugin.config = {'start': 2, 'end': 5}

    initial_pages = list(singles_with_pages.pages)
    result_singles = plugin.after_initialize_singles(singles_with_pages)

    assert len(result_singles.pages) == 10
    assert result_singles.pages == initial_pages

def test_serve_mode_no_config(plugin, singles_with_pages):
    singles_with_pages.config['mode'] = 'serve'
    plugin.config = {}

    initial_pages = list(singles_with_pages.pages)
    result_singles = plugin.after_initialize_singles(singles_with_pages)

    assert len(result_singles.pages) == 10
    assert result_singles.pages == initial_pages

def test_serve_mode_with_start(plugin, singles_with_pages):
    singles_with_pages.config['mode'] = 'serve'
    plugin.config = {'start': 5}

    original_pages = list(singles_with_pages.pages)
    result_singles = plugin.after_initialize_singles(singles_with_pages)

    assert len(result_singles.pages) == 5
    assert result_singles.pages == original_pages[5:]

def test_serve_mode_with_end(plugin, singles_with_pages):
    singles_with_pages.config['mode'] = 'serve'
    plugin.config = {'end': 3}

    original_pages = list(singles_with_pages.pages)
    result_singles = plugin.after_initialize_singles(singles_with_pages)

    assert len(result_singles.pages) == 3
    assert result_singles.pages == original_pages[:3]

def test_serve_mode_with_start_and_end(plugin, singles_with_pages):
    singles_with_pages.config['mode'] = 'serve'
    plugin.config = {'start': 2, 'end': 8}

    original_pages = list(singles_with_pages.pages)
    result_singles = plugin.after_initialize_singles(singles_with_pages)

    assert len(result_singles.pages) == 6
    assert result_singles.pages == original_pages[2:8]

def test_serve_mode_with_step(plugin, singles_with_pages):
    singles_with_pages.config['mode'] = 'serve'
    plugin.config = {'step': 2}

    original_pages = list(singles_with_pages.pages)
    result_singles = plugin.after_initialize_singles(singles_with_pages)

    assert len(result_singles.pages) == 5
    assert result_singles.pages == original_pages[::2]

def test_serve_mode_with_all_parameters(plugin, singles_with_pages):
    singles_with_pages.config['mode'] = 'serve'
    plugin.config = {'start': 1, 'end': 9, 'step': 3}

    original_pages = list(singles_with_pages.pages)
    result_singles = plugin.after_initialize_singles(singles_with_pages)

    assert len(result_singles.pages) == 3
    assert result_singles.pages == original_pages[1:9:3]
