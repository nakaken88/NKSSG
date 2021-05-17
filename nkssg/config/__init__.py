from pathlib import Path

import jinja2
from ruamel.yaml import YAML

from nkssg.structure.plugins import Plugins
from nkssg.utils import get_config_by_list


def load_config(mode):
    with open('nkssg.yml', encoding='utf8') as stream:
        config = YAML(typ='safe').load(stream)

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
    config['site']['site_name'] = get_config_by_list(config, ['site', 'site_name']) or 'Site Title'
    config['site']['site_url'] = get_config_by_list(config, ['site', 'site_url']) or ''
    config['site']['site_desc'] = get_config_by_list(config, ['site', 'site_desc']) or ''
    config['site']['site_image'] = get_config_by_list(config, ['site', 'site_image']) or ''
    config['site']['language'] = get_config_by_list(config, ['site', 'language']) or 'en'

    config['site']['site_url'] = config['site']['site_url'].rstrip('/')


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
                'archive_type': 'date',
            }
        })

        config['post_type'].append({
            'page': {
                'permalink': r'/{slug}/',
                'archive_type': 'section',
            }
        })

    config['taxonomy'] = get_config_by_list(config, ['taxonomy']) or {}

    if get_config_by_list(config, ['use_abs_url']) is None:
        config['use_abs_url'] = True


    default_block_tag_string = "address|article|aside|details|dialog|dd|div|dl|dt|fieldset|figcaption|figure|footer|form|h1|h2|h3|h4|h5|h6|header|hgroup|hr|li|main|nav|ol|p|pre|section|table|ul|legend|map|math|menu|script|style|summary"
    
    config['block_tag'] = get_config_by_list(config, ['block_tag']) or default_block_tag_string
    config['block_tags'] = config['block_tag'].split('|')

    return config

