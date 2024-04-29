import collections
import inspect

from ruamel.yaml import YAML


def get_config_by_list(config, keys):
    try:
        if not isinstance(keys, list):
            keys = [keys]

        cnf = config
        for key in keys:
            if cnf is None:
                return None
            elif isinstance(cnf, list):
                temp = None
                for item in cnf:
                    if isinstance(item, dict):
                        temp = item.get(key)
                    if temp is not None:
                        break
                cnf = temp
            else:
                cnf = cnf.get(key)
        return cnf
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def to_slug(dirty_slug):
    slug = dirty_slug.replace(' ', '-').lower()
    return slug


def clean_name(dirty_name):
    if dirty_name[0] != '_':
        return dirty_name
    if dirty_name[1] == '_':
        return dirty_name[1:]

    parts = dirty_name.split('_')
    if len(parts) == 2:
        return dirty_name

    prefix = '_' + parts[1] + '_'

    if len(prefix) == len(dirty_name):
        return dirty_name
    else:
        return dirty_name[len(prefix):]


def front_matter_setup(doc):
    if doc[:3] != '---':
        return {}, doc

    parts = doc.split('---')
    front_matter = YAML(typ='safe').load(parts[1]) or {}

    doc = ''
    if len(parts) >= 2:
        doc = '---'.join(parts[2:])

    return front_matter, doc


def dup_check(tuple_list):
    key_list = [t[0] for t in tuple_list]
    counter = collections.Counter(key_list)

    dup_check_ok = True
    for k, v in counter.items():
        if v > 1:
            print('Error: ' + k + ' is duplicated')
            for t in tuple_list:
                if t[0] == k:
                    print('-', t[1])
            dup_check_ok = False

    if not dup_check_ok:
        raise Exception(inspect.stack()[1][3] + ' error')
