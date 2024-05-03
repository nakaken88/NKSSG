import pkg_resources

from nkssg.utils import get_config_by_list


class Plugins():
    def __init__(self, config):

        if get_config_by_list(config, ['plugin_is_ready']) is not None:
            config['plugins'] = config['active_plugins']
            self.plugins = config['active_plugins']
            return

        self.plugins = {}

        installed_plugins = pkg_resources.iter_entry_points(group='nkssg.plugins')
        self.installed_plugins = {plugin.name: plugin for plugin in installed_plugins}

        plugins = get_config_by_list(config, ['plugins'])
        if plugins is None:
            config['plugin_is_ready'] = True
            config['active_plugins'] = {}
            return

        for plugin_name in plugins:
            plugin_config = {}

            if isinstance(plugin_name, dict):
                for key, value in plugin_name.items():
                    plugin_name = key
                    plugin_config = value
                    break

            if plugin_name in self.installed_plugins:
                Plugin = self.installed_plugins[plugin_name].load()
                plugin = Plugin()
                plugin.config = plugin_config
                self.plugins[plugin_name] = plugin

            else:
                print('Warning: ' + plugin_name + ' plugin is not found')

        config['plugins'] = self.plugins
        config['active_plugins'] = self.plugins
        config['plugin_is_ready'] = True

    def do_action(self, action_name, target=None, **kwargs):

        for plugin in self.plugins.values():
            method = getattr(plugin, action_name, None)

            if callable(method):
                target = method(target, **kwargs) or target

        return target


class BasePlugin():
    def __init__(self):
        self.config = {}
