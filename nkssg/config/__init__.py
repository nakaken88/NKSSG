from pathlib import Path

import jinja2
from ruamel.yaml import YAML

from nkssg.structure.plugins import Plugins
from nkssg.utils import get_config_by_list


def load_config(mode):
    with open('config.yml', encoding='utf8') as stream:
        config = YAML(typ='safe').load(stream)

    if get_config_by_list(config, ['site', 'site_url']) is not None:
        config['site']['site_url'] = config['site']['site_url'].rstrip('/')

    config['mode'] = mode

    config['base_dir'] = Path.cwd()
    config['docs_dir'] = config['base_dir'] / 'docs'
    config['public_dir'] = config['base_dir'] / 'public'
    config['static_dir'] = config['base_dir'] / 'static'


    config = set_default_config(config)

    config['plugins'] = Plugins(config)
    config = config['plugins'].do_action('after_load_config', target=config)

    return config


def set_default_config(config):
    config['site'] = get_config_by_list(config, ['site']) or {}
    if get_config_by_list(config, ['site', 'site_url']) is None:
        config['site']['site_url'] = ''


    if get_config_by_list(config, ['plugins']) is None:
        config['plugins'] = [
            'autop',
            'awesome-page-link',
            'awesome-img-link',
            'select-pages'
            ]


    if get_config_by_list(config, ['doc_ext']) is None:
        config['doc_ext'] = [
            'md', 'markdown',
            'html', 'htm',
            'txt',
            ]
    if get_config_by_list(config, ['exclude']) is None:
        config['exclude'] = []

    if get_config_by_list(config, ['post_type']) is None:
        config['post_type'] = []

        config['post_type'].append({
            'post': {
                'permalink': r'/%Y/%m/%d/%H%M%S/',
                'date_archive': True,
                'section_archive': False,
                'priority_archive': 'date',
            }
        })

        config['post_type'].append({
            'page': {
                'permalink': r'/{slug}/',
                'date_archive': False,
                'section_archive': True,
                'priority_archive': 'section',
            }
        })

    config['taxonomy'] = get_config_by_list(config, ['taxonomy']) or {}

    if get_config_by_list(config, ['use_abs_url']) is None:
        config['use_abs_url'] = True

    return config

