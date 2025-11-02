from dataclasses import dataclass, field
import datetime
from pathlib import Path
from typing import Any

import jinja2
from ruamel.yaml import YAML, YAMLError


@dataclass
class BaseConfig:
    extras: dict[str, Any] = field(default_factory=dict)

    def __getitem__(self, k):
        if k in self.__dict__:
            return self.__dict__[k]
        elif k in self.extras:
            return self.extras[k]
        else:
            raise KeyError(f"{k} not found in {self.__class__.__name__}.")

    def get(self, k, default=None):
        if k in self.__dict__:
            return self.__dict__[k]
        elif k in self.extras:
            return self.extras[k]
        else:
            return default

    def __setitem__(self, k, v):
        if k in self.__dict__:
            self.__dict__[k] = v
        else:
            self.extras[k] = v

    def update(self, myDict: dict):
        for k, v in myDict.items():
            self.__setitem__(k, v)


@dataclass
class SiteConfig(BaseConfig):

    site_name: str = 'Site Title'
    site_url: str = ''
    site_desc: str = ''
    site_image: str = ''
    language: str = 'en'

    site_url_original: str = ''

    def update(self, myDict: dict):
        super().update(myDict)

        self.site_url_original = self.site_url
        self.site_url = self.site_url.rstrip('/')
        self.site_image = self.site_image.replace(self.site_url, '')


@dataclass
class PostTypeConfig(BaseConfig):

    permalink: str = r'/{slug}/'
    archive_type: str = 'section'
    slug: str = ''
    add_prefix_to_url: bool = True
    limit: int = 0


class PostTypeConfigManager(dict[str, PostTypeConfig]):

    def update(self, d: dict):
        for k, v in d.items():
            if k not in self:
                self[k] = PostTypeConfig()

            self[k].update(v)

            archive_type = self[k].archive_type
            archive_type = archive_type.lower()
            if archive_type not in ['date', 'simple', 'none']:
                archive_type = 'section'
            self[k].archive_type = archive_type


@dataclass
class TermConfig(BaseConfig):

    name: str = ''
    slug: str = ''
    desc: str = ''
    label: str = ''
    parent: str = ''


@dataclass
class TaxonomyConfig(BaseConfig):

    name: str = ''
    slug: str = ''
    desc: str = ''
    label: str = ''
    limit: int = 0
    terms: dict[str, TermConfig] = field(default_factory=dict)

    def update(self, d: dict):
        for k, v in d.items():
            if k == 'term':
                self.update_terms(v)
            else:
                super().update({k: v})

    def update_terms(self, term_config_list, parent=''):
        for term_config in term_config_list:
            if isinstance(term_config, dict):
                name = term_config.get('name', '')
            else:
                try:
                    name = str(term_config)
                except ValueError as e:
                    raise ValueError(
                        f"Invalid data for term: {term_config}") from e

            if not name:
                raise ValueError('term config must have name')

            term = self.terms.get(name, TermConfig(name=name, parent=parent))
            self.terms[name] = term

            if isinstance(term_config, dict):
                for k, v in term_config.items():
                    if k != 'term':
                        term.update({k: v})

                if 'term' in term_config:
                    self.update_terms(term_config['term'], term.name)


class TaxonomyConfigManager(dict[str, TaxonomyConfig]):

    def update(self, d: dict):
        for k, v in d.items():
            if k not in self:
                self[k] = TaxonomyConfig()

            self[k].update(v)


@dataclass
class Config(BaseConfig):

    site: SiteConfig = field(default_factory=SiteConfig)

    plugins: dict = field(default_factory=lambda: {
        'autop': {},
        'awesome-page-link': {},
        'awesome-img-link': {},
        'select-pages': {}
    })

    _dir_types: list[str] = field(default_factory=lambda: [
        'docs', 'public', 'static', 'themes'
    ])
    base_dir: Path = Path()
    docs_dir: Path = Path()
    public_dir: Path = Path()
    static_dir: Path = Path()
    themes_dir: Path = Path()

    doc_ext: list[str] = field(default_factory=lambda: [
        'md', 'markdown', 'html', 'htm', 'txt'
    ])
    extra_pages: list[str] = field(default_factory=lambda: [
        'home.html', '404.html', 'sitemap.html', 'sitemap.xml'
    ])

    markdown: dict = field(default_factory=dict)

    exclude: list = field(default_factory=list)

    post_type: PostTypeConfigManager
    post_type = field(default_factory=PostTypeConfigManager)

    theme: dict = field(default_factory=dict)

    taxonomy: TaxonomyConfigManager
    taxonomy = field(default_factory=TaxonomyConfigManager)

    use_abs_url: bool = True

    now = datetime.datetime.now()

    env: jinja2.Environment = jinja2.Environment()

    def __post_init__(self):
        default_dirs = {dir_type: dir_type for dir_type in self._dir_types}
        self.base_dir = Path.cwd()
        self.set_directory_path(default_dirs)

    def set_directory_path(self, data: dict):
        for k, v in data.items():
            dir_key = f'{k}_dir'
            self.update({dir_key: self.base_dir / Path(v)})

    def _update_from_yaml_string(self, yaml_content: str):
        yaml = YAML(typ='safe')
        try:
            data = yaml.load(yaml_content)
            if data:
                self.update(data)
        except YAMLError as e:
            raise ValueError(f"The YAML format is incorrect: {e}")

    def _update_from_yaml_file(self, yaml_file_path: Path):
        try:
            yaml_content = yaml_file_path.read_text(encoding='utf-8')
            self._update_from_yaml_string(yaml_content)
        except FileNotFoundError:
            msg = f"The YAML file was not found: {yaml_file_path}"
            raise FileNotFoundError(msg)
        except Exception as e:
            msg = f"An error occurred while loading the config file: {e}"     
            raise Exception(msg)

    @classmethod
    def from_file(cls, yaml_file_path: Path = Path('nkssg.yml')):  
        config = cls()
        config._update_from_yaml_file(yaml_file_path)
        return config

    def update(self, data: dict):
        for k, v in data.items():
            if k == 'site':
                self.site.update(v)
            elif k == 'directory':
                self.set_directory_path(v)
            elif k == 'post_type':
                self.post_type.update(v)
            elif k == 'taxonomy':
                self.taxonomy.update(v)
            else:
                super().update({k: v})
