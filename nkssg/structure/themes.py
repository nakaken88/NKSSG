from pathlib import Path

from ruamel.yaml import YAML

from nkssg.utils import get_config_by_list


class Themes:
    def __init__(self, config):
        self.dirs = []
        self.cnf = {}

        themes_dir = config['base_dir'] / 'themes'

        theme = get_config_by_list(config, ['theme', 'child'])
        if theme is not None:
            theme_dir = themes_dir / theme
            if theme_dir.exists():
                self.dirs.append(theme_dir)
                cnf_path = theme_dir / (theme + '.yml')
                if cnf_path.exists():
                    cnf = YAML(typ='safe').load(cnf_path) or {}
                    self.cnf = cnf
            else:
                print(theme + ' is not found')

        theme = get_config_by_list(config, ['theme', 'name'])
        if theme is not None:
            theme_dir = themes_dir / theme
            if theme_dir.exists():
                self.dirs.append(theme_dir)
                cnf_path = theme_dir / (theme + '.yml')
                if cnf_path.exists():
                    cnf = YAML(typ='safe').load(cnf_path) or {}
                    self.cnf = {**cnf, **self.cnf}
            else:
                print(theme + ' is not found')

        if not self.dirs:
            if config.get('theme') is None:
                config['theme'] = {'name': 'default'}
            elif config['theme'].get('name') is None:
                config['theme']['name'] = 'default'

            theme_dir = config["PKG_DIR"] / 'themes' / 'default'
            self.dirs.append(theme_dir)

            cnf_path = theme_dir / 'default.yml'
            cnf = YAML(typ='safe').load(cnf_path) or {}
            self.cnf = cnf
