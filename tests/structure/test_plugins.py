import pytest
from unittest.mock import MagicMock

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


def _create_mock_entry_point(name, plugin_class):
    ep = MagicMock()
    ep.name = name
    ep.load.return_value = plugin_class
    return ep


class TestPlugins:

    def test_plugin_loading(self, mocker):
        mock_entry_points = mocker.patch('nkssg.structure.plugins.entry_points')
        mock_entry_points.return_value = [
            _create_mock_entry_point('plugin_a', DummyPluginA),
            _create_mock_entry_point('plugin_b', DummyPluginB),
        ]

        config = Config()
        config.update({'plugins': {'plugin_a': {}}})
        plugin_manager = Plugins(config)

        assert 'plugin_a' in plugin_manager.plugins
        assert isinstance(plugin_manager.plugins['plugin_a'], DummyPluginA)
        assert 'plugin_b' not in plugin_manager.plugins

    def test_missing_plugin_warning(self, mocker):
        mock_entry_points = mocker.patch('nkssg.structure.plugins.entry_points')
        mock_print = mocker.patch('builtins.print')
        mock_entry_points.return_value = []

        config = Config()
        config.update({'plugins': {'non_existent_plugin': {}}})
        Plugins(config)

        mock_print.assert_called_with('Warning: non_existent_plugin plugin is not found')

    def test_do_action_execution_order(self, mocker):
        mock_entry_points = mocker.patch('nkssg.structure.plugins.entry_points')
        mock_entry_points.return_value = [
            _create_mock_entry_point('plugin_a', DummyPluginA),
            _create_mock_entry_point('plugin_b', DummyPluginB),
        ]

        config = Config()
        config.update({'plugins': {'plugin_a': {}, 'plugin_b': {}}})
        plugin_manager = Plugins(config)

        initial_target = {'value': 10}
        result = plugin_manager.do_action('on_test_action', target=initial_target)
        assert result['value'] == 22  # (10 + 1) * 2

    def test_do_action_no_return(self, mocker):
        mock_entry_points = mocker.patch('nkssg.structure.plugins.entry_points')
        mock_entry_points.return_value = [
            _create_mock_entry_point('plugin_c', DummyPluginC),
        ]
        config = Config()
        config.update({'plugins': {'plugin_c': {}}})
        plugin_manager = Plugins(config)

        initial_target = {'value': 5}
        result = plugin_manager.do_action('on_test_action', target=initial_target)
        # in-place changes are preserved even when the plugin returns None
        assert result['value'] == 15
        assert result is initial_target

    def test_do_action_no_method(self, mocker):
        mock_entry_points = mocker.patch('nkssg.structure.plugins.entry_points')
        mock_entry_points.return_value = [
            _create_mock_entry_point('plugin_d', DummyPluginD),
        ]
        config = Config()
        config.update({'plugins': {'plugin_d': {}}})
        plugin_manager = Plugins(config)

        initial_target = {'value': 100}
        result = plugin_manager.do_action('on_test_action', target=initial_target)
        assert result['value'] == 100

    def test_do_action_with_kwargs(self, mocker):
        class KwargPlugin(BasePlugin):
            __test__ = False  # prevent pytest from collecting this as a test class
            def on_test_action(self, target, **kwargs):
                target['extra'] = kwargs.get('extra_data')
                return target

        mock_entry_points = mocker.patch('nkssg.structure.plugins.entry_points')
        mock_entry_points.return_value = [
            _create_mock_entry_point('kwarg_plugin', KwargPlugin)
        ]
        config = Config()
        config.update({'plugins': {'kwarg_plugin': {}}})
        plugin_manager = Plugins(config)

        initial_target = {'value': 1}
        result = plugin_manager.do_action('on_test_action', target=initial_target, extra_data='some_extra_info')

        assert result['extra'] == 'some_extra_info'
