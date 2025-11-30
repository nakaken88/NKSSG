import unittest
from unittest.mock import MagicMock, patch

from nkssg.structure.config import Config
from nkssg.structure.plugins import Plugins, BasePlugin


class DummyPluginA(BasePlugin):
    def on_test_action(self, target, **kwargs):
        target['value'] += 1
        return target


class DummyPluginB(BasePlugin):
    def on_test_action(self, target, **kwargs):
        target['value'] *= 2
        return target


class DummyPluginC(BasePlugin):
    # This plugin doesn't return target
    def on_test_action(self, target, **kwargs):
        target['value'] += 10


class DummyPluginD(BasePlugin):
    # This plugin doesn't have the action
    def on_another_action(self, target, **kwargs):
        target['value'] = 0
        return target


class TestPlugins(unittest.TestCase):

    def _create_mock_entry_point(self, name, plugin_class):
        ep = MagicMock()
        ep.name = name
        ep.load.return_value = plugin_class
        return ep

    @patch('nkssg.structure.plugins.entry_points')
    def test_plugin_loading(self, mock_entry_points):
        """Test that plugins are loaded correctly based on config."""
        mock_entry_points.return_value = [
            self._create_mock_entry_point('plugin_a', DummyPluginA),
            self._create_mock_entry_point('plugin_b', DummyPluginB),
        ]

        config = Config()
        config.update({'plugins': {'plugin_a': {}}})
        plugin_manager = Plugins(config)

        self.assertIn('plugin_a', plugin_manager.plugins)
        self.assertIsInstance(plugin_manager.plugins['plugin_a'], DummyPluginA)
        self.assertNotIn('plugin_b', plugin_manager.plugins)

    @patch('nkssg.structure.plugins.entry_points')
    @patch('builtins.print')
    def test_missing_plugin_warning(self, mock_print, mock_entry_points):
        """Test that a warning is printed for a missing plugin."""
        mock_entry_points.return_value = []

        config = Config()
        config.update({'plugins': {'non_existent_plugin': {}}})
        Plugins(config)

        mock_print.assert_called_with('Warning: non_existent_plugin plugin is not found')

    @patch('nkssg.structure.plugins.entry_points')
    def test_do_action_execution_order(self, mock_entry_points):
        """Test that do_action executes plugins in the specified order."""
        mock_entry_points.return_value = [
            self._create_mock_entry_point('plugin_a', DummyPluginA),
            self._create_mock_entry_point('plugin_b', DummyPluginB),
        ]

        # Config order is what matters
        config_data = {
            'plugins': {
                'plugin_a': {},
                'plugin_b': {},
            }
        }
        config = Config()
        config.update(config_data)
        # To preserve insertion order for the test
        config.plugins = config_data['plugins']

        plugin_manager = Plugins(config)
        
        initial_target = {'value': 10}
        # (10 + 1) * 2 = 22
        result = plugin_manager.do_action('on_test_action', target=initial_target)
        self.assertEqual(result['value'], 22)

    @patch('nkssg.structure.plugins.entry_points')
    def test_do_action_no_return(self, mock_entry_points):
        """Test that the original target is returned if a plugin returns None."""
        mock_entry_points.return_value = [
            self._create_mock_entry_point('plugin_c', DummyPluginC),
        ]
        config = Config()
        config.update({'plugins': {'plugin_c': {}}})
        plugin_manager = Plugins(config)
        
        initial_target = {'value': 5}
        # Plugin C adds 10 but doesn't return, so the modified dict is passed.
        # But since it returns None, the `or target` logic should return the original.
        # Let's see if the object is modified in place.
        result = plugin_manager.do_action('on_test_action', target=initial_target)
        self.assertEqual(result['value'], 15)
        self.assertIs(result, initial_target) # It should be the same object

    @patch('nkssg.structure.plugins.entry_points')
    def test_do_action_no_method(self, mock_entry_points):
        """Test that plugins without the action method are skipped."""
        mock_entry_points.return_value = [
            self._create_mock_entry_point('plugin_d', DummyPluginD),
        ]
        config = Config()
        config.update({'plugins': {'plugin_d': {}}})
        plugin_manager = Plugins(config)

        initial_target = {'value': 100}
        result = plugin_manager.do_action('on_test_action', target=initial_target)
        self.assertEqual(result['value'], 100)

    @patch('nkssg.structure.plugins.entry_points')
    def test_do_action_with_kwargs(self, mock_entry_points):
        """Test that kwargs are passed correctly to plugin actions."""
        # We need a plugin that accepts kwargs
        class KwargPlugin(BasePlugin):
            def on_test_action(self, target, **kwargs):
                target['extra'] = kwargs.get('extra_data')
                return target

        mock_entry_points.return_value = [
            self._create_mock_entry_point('kwarg_plugin', KwargPlugin)
        ]
        config = Config()
        config.update({'plugins': {'kwarg_plugin': {}}})
        plugin_manager = Plugins(config)

        initial_target = {'value': 1}
        extra = "some_extra_info"
        result = plugin_manager.do_action('on_test_action', target=initial_target, extra_data=extra)

        self.assertEqual(result['extra'], extra)
