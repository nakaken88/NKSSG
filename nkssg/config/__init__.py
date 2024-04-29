from dataclasses import dataclass, field
import datetime
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from nkssg.structure.plugins import Plugins
from nkssg.utils import get_config_by_list


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

    def get(self, k):
        if k in self.__dict__:
            return self.__dict__[k]
        elif k in self.extras:
            return self.extras[k]
        else:
            return None

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


@dataclass
class Config(BaseConfig):

    site: SiteConfig = field(default_factory=SiteConfig)

    plugins: list[str] = field(default_factory=lambda: [
        'autop',
        'awesome-page-link',
        'awesome-img-link',
        'select-pages'
    ])

    doc_ext: list[str] = field(default_factory=lambda: [
        'md', 'markdown', 'html', 'htm', 'txt'
    ])

    exclude: list = field(default_factory=list)

    post_type: list = field(default_factory=lambda: [
        {'post': {'permalink': r'/%Y/%m/%d/%H%M%S/', 'archive_type': 'date'}},
        {'page': {'permalink': r'/{slug}/', 'archive_type': 'section'}}
    ])

    taxonomy: dict = field(default_factory=dict)

    use_abs_url: bool = True

    def load_config(self, yaml_file_path):
        with open(yaml_file_path, encoding='utf8') as f:
            data = YAML(typ='safe').load(f)

            for k, v in data.items():
                if k == 'site':
                    self.site.update(v)
                else:
                    super().update({k: v})


def load_config(mode):
    config = Config()
    config.load_config('nkssg.yml')

    config['mode'] = mode

    config['base_dir'] = Path.cwd()
    for dir_type in ['docs', 'public', 'static', 'cache', 'themes']:
        dir = dir_type + '_dir'
        config[dir] = get_config_by_list(config, ['directory', dir_type]) or dir_type
        config[dir] = config['base_dir'] / config[dir]

    config['cache_contents_path'] = config['cache_dir'] / ('contents_' + mode + '.json')
    config['cache_htmls_path'] = config['cache_dir'] / ('htmls_' + mode + '.json')

    config = set_default_config(config)

    config['plugins'] = Plugins(config)
    config = config['plugins'].do_action('after_load_config', target=config)

    return config


def set_default_config(config: Config):

    site_config = config['site']
    site_config['site_url'] = site_config['site_url'].rstrip('/')
    site_config['site_url_original'] = site_config['site_url']

    if site_config['site_url'] in site_config['site_image']:
        site_config['site_image'] = site_config['site_image'].replace(site_config['site_url'], '')

    config['now'] = datetime.datetime.now(datetime.timezone.utc)

    return config
