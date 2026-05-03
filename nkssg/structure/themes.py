import logging
from pathlib import Path
from ruamel.yaml import YAML
import nkssg
from nkssg.structure.config import Config


class Themes:
    def __init__(self, config: Config):

        self.dirs: list[Path] = []
        self.cnf = {}

        self.load_theme(config, 'name')
        self.load_theme(config, 'child')

        if not self.dirs:
            self.set_default_theme(config)

        config.theme['updated'] = True
        self._template_cache = self._build_template_cache()

    def _build_template_cache(self):
        cache = {}
        for d in reversed(self.dirs):
            for f in d.glob('**/*'):
                if f.is_file():
                    rel = str(f.relative_to(d)).replace('\\', '/')
                    abs_ = str(f).replace('\\', '/')
                    cache[f.name] = (rel, abs_)
        return cache

    def load_theme(self, config: Config, path):
        theme = config.theme.get(path)
        if theme:
            theme_dir = config.themes_dir / Path(theme)
            if theme_dir.exists():
                self.dirs.insert(0, theme_dir)
                self.load_theme_config(theme_dir, theme)

            elif not config.theme.get('updated'):
                logging.warning(f"{theme} is not found")

    def load_theme_config(self, theme_dir: Path, theme_name):
        cnf_path = theme_dir / Path(theme_name + '.yml')
        try:
            cnf = YAML(typ='safe').load(cnf_path) or {}
            self.cnf = {**self.cnf, **cnf}
        except Exception as e:
            logging.warning(f"Failed to load config for {theme_name}: {e}")

    def set_default_theme(self, config: Config):
        default_theme_name = 'default'
        package_dir = Path(nkssg.__file__).parent
        default_theme_dir = package_dir / 'themes' / default_theme_name
        config.theme['name'] = default_theme_name
        self.dirs.append(default_theme_dir)
        self.load_theme_config(default_theme_dir, default_theme_name)

    def lookup_template(self, search_list: list[str], full_path=False):
        for search in search_list:
            if search in self._template_cache:
                rel, abs_ = self._template_cache[search]
                return abs_ if full_path else rel
        return ''
