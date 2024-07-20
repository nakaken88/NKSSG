from importlib.metadata import entry_points

from nkssg.structure.config import Config


class Plugins():
    def __init__(self, config: Config):

        self.plugins = {}
        self.installed_plugins = {
            plugin.name: plugin
            for plugin in entry_points(group='nkssg.plugins')
        }

        for plugin_name, plugin_config in config.plugins.items():

            if plugin_name in self.installed_plugins:
                Plugin = self.installed_plugins[plugin_name].load()
                plugin: BasePlugin = Plugin()
                plugin.config = plugin_config
                self.plugins[plugin_name] = plugin
            else:
                print('Warning: ' + plugin_name + ' plugin is not found')

    def do_action(self, action_name, target=None, **kwargs):

        for plugin in self.plugins.values():
            method = getattr(plugin, action_name, None)

            if callable(method):
                target = method(target, **kwargs) or target

        return target


class BasePlugin():
    def __init__(self):
        self.config = {}
