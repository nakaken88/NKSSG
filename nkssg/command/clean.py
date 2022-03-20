import logging
import shutil


log = logging.getLogger(__name__)
valid_values = ['public', 'cache']


def clean(config, name):

    if name == 'all':
        for value in valid_values:
            clean(config, value)
    elif name in valid_values:
        clean_dir(config, name)
    else:
        log.warn('Valid values are all /' + ' / '.join(valid_values) + '.')


def clean_dir(config, name):

    target_dir = config[name + '_dir']
    if target_dir.exists():
        shutil.rmtree(target_dir)
        target_dir.mkdir()
        log.warn(name + ' folder has been cleaned.')
    else:
        log.warn(name + ' folder is missing.')
