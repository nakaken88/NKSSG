import pytest
from unittest.mock import MagicMock, patch

from nkssg.plugins.select_pages import SelectPagesPlugin
from nkssg.structure.config import Config
from nkssg.structure.singles import Singles, Single
from nkssg.structure.plugins import Plugins

@pytest.fixture
def plugin():
    """Provides a fresh instance of the plugin for each test."""
    return SelectPagesPlugin()

@pytest.fixture
def singles_with_pages():
    """Provides a Singles object populated with 10 dummy pages."""
    # Patch the method that reads from the filesystem during initialization
    with patch.object(Singles, 'get_pages_from_docs_directory', return_value=[]):
        mock_plugins = MagicMock(spec=Plugins)
        singles = Singles(Config(), mock_plugins)
        
    # Now, manually set the pages for the test
    singles.pages = [MagicMock(spec=Single) for _ in range(10)]
    return singles

def test_not_serve_mode(plugin, singles_with_pages):
    """Test that the plugin does nothing if not in 'serve' mode."""
    singles_with_pages.config['mode'] = 'build'
    plugin.config = {'start': 2, 'end': 5}
    
    initial_pages = list(singles_with_pages.pages)
    result_singles = plugin.after_initialize_singles(singles_with_pages)
    
    assert len(result_singles.pages) == 10
    assert result_singles.pages == initial_pages

def test_serve_mode_no_config(plugin, singles_with_pages):
    """Test that nothing changes in 'serve' mode with default config."""
    singles_with_pages.config['mode'] = 'serve'
    plugin.config = {}  # No start, end, or step

    initial_pages = list(singles_with_pages.pages)
    result_singles = plugin.after_initialize_singles(singles_with_pages)

    assert len(result_singles.pages) == 10
    assert result_singles.pages == initial_pages

def test_serve_mode_with_start(plugin, singles_with_pages):
    """Test slicing with only 'start' specified."""
    singles_with_pages.config['mode'] = 'serve'
    plugin.config = {'start': 5}

    original_pages = list(singles_with_pages.pages)
    result_singles = plugin.after_initialize_singles(singles_with_pages)
    
    assert len(result_singles.pages) == 5
    assert result_singles.pages == original_pages[5:]

def test_serve_mode_with_end(plugin, singles_with_pages):
    """Test slicing with only 'end' specified."""
    singles_with_pages.config['mode'] = 'serve'
    plugin.config = {'end': 3}

    original_pages = list(singles_with_pages.pages)
    result_singles = plugin.after_initialize_singles(singles_with_pages)

    assert len(result_singles.pages) == 3
    assert result_singles.pages == original_pages[:3]

def test_serve_mode_with_start_and_end(plugin, singles_with_pages):
    """Test slicing with both 'start' and 'end'."""
    singles_with_pages.config['mode'] = 'serve'
    plugin.config = {'start': 2, 'end': 8}

    original_pages = list(singles_with_pages.pages)
    result_singles = plugin.after_initialize_singles(singles_with_pages)

    assert len(result_singles.pages) == 6
    assert result_singles.pages == original_pages[2:8]

def test_serve_mode_with_step(plugin, singles_with_pages):
    """Test slicing with 'step'."""
    singles_with_pages.config['mode'] = 'serve'
    plugin.config = {'step': 2}

    original_pages = list(singles_with_pages.pages)
    result_singles = plugin.after_initialize_singles(singles_with_pages)
    
    assert len(result_singles.pages) == 5
    assert result_singles.pages == original_pages[::2]

def test_serve_mode_with_all_parameters(plugin, singles_with_pages):
    """Test slicing with start, end, and step."""
    singles_with_pages.config['mode'] = 'serve'
    plugin.config = {'start': 1, 'end': 9, 'step': 3}

    original_pages = list(singles_with_pages.pages)
    result_singles = plugin.after_initialize_singles(singles_with_pages)

    assert len(result_singles.pages) == 3
    assert result_singles.pages == original_pages[1:9:3]
