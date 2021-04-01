from pathlib import Path
import pkg_resources

from nkssg.utils import get_config_by_list


class Themes:
    def __init__(self, config):
        self.dirs = []

        themes_dir = config['base_dir'] / 'themes'

        theme = get_config_by_list(config, ['theme', 'child'])
        if theme is not None:
            theme_dir = themes_dir / theme
            if theme_dir.exists():
                self.dirs.append(theme_dir)
            else:
                print(theme + ' is not found')

        theme = get_config_by_list(config, ['theme', 'name'])
        if theme is not None:
            theme_dir = themes_dir / theme
            if theme_dir.exists():
                self.dirs.append(theme_dir)
            else:
                print(theme + ' is not found')

        if not self.dirs:
            theme_dir = config["PKG_DIR"] / 'themes' / 'default'
            self.dirs.append(theme_dir)

