import datetime
from pathlib import Path

from ruamel.yaml import YAML

from nkssg.structure.plugins import Plugins
from nkssg.utils import get_config_by_list


class Config(dict):
    def __init__(self) -> None:
        super().__init__(self)

    def load_config(self, yaml_file_path):
        with open(yaml_file_path, encoding='utf8') as f:
            data = YAML(typ='safe').load(f)

            for k, v in data.items():
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


def set_default_config(config: dict):
    site_config: dict = config.setdefault('site', {})
    site_config.setdefault('site_name', 'Site Title')
    site_config.setdefault('site_url', '')
    site_config.setdefault('site_desc', '')
    site_config.setdefault('site_image', '')
    site_config.setdefault('language', 'en')

    site_config['site_url'] = site_config['site_url'].rstrip('/')
    site_config['site_url_original'] = site_config['site_url']

    if site_config['site_url'] in site_config['site_image']:
        site_config['site_image'] = site_config['site_image'].replace(site_config['site_url'], '')

    config['now'] = datetime.datetime.now(datetime.timezone.utc)

    config.setdefault('plugins', [
        'autop',
        'awesome-page-link',
        'awesome-img-link',
        'select-pages'
    ])

    config.setdefault('doc_ext', [
        'md', 'markdown',
        'html', 'htm',
        'txt',
    ])

    config.setdefault('exclude', [])

    if get_config_by_list(config, ['post_type']) is None:
        config['post_type'] = []

        config['post_type'].append({
            'post': {
                'permalink': r'/%Y/%m/%d/%H%M%S/',
                'archive_type': 'date',
            }
        })

        config['post_type'].append({
            'page': {
                'permalink': r'/{slug}/',
                'archive_type': 'section',
            }
        })

    config.setdefault('taxonomy', {})

    config.setdefault('use_abs_url', True)

    return config
