from pathlib import Path

from ruamel.yaml import YAML

from nkssg.config import Config


class Themes:
    def __init__(self, config: Config):

        self.dirs = []
        self.cnf = {}

        self.load_theme(config, 'name')
        self.load_theme(config, 'child')

        if not self.dirs:
            self.set_default_theme(config)

        config.theme['updated'] = True

    def load_theme(self, config: Config, path):
        theme = config.theme.get(path)
        if theme:
            theme_dir = config.themes_dir / Path(theme)
            if theme_dir.exists():
                self.dirs.append(theme_dir)
                self.load_theme_config(theme_dir, theme)

            elif not config.theme.get('updated'):
                print(f"{theme} is not found")

    def load_theme_config(self, theme_dir: Path, theme_name):
        cnf_path = theme_dir / Path(theme_name + '.yml')
        try:
            cnf = YAML(typ='safe').load(cnf_path) or {}
            self.cnf = {**self.cnf, **cnf}
        except Exception as e:
            print(f"Failed to load config for {theme_name}: {e}")

    def set_default_theme(self, config: Config):
        default_theme_name = 'default'
        default_theme_dir = config["PKG_DIR"] / 'themes' / default_theme_name
        config.theme['name'] = default_theme_name
        self.dirs.append(default_theme_dir)
        self.load_theme_config(default_theme_dir, default_theme_name)
