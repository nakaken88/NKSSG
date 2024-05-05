import collections
import inspect


def to_slug(dirty_slug):
    slug = dirty_slug.replace(' ', '-').lower()
    return slug


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
