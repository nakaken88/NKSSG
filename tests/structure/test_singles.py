import datetime
import pytest

from nkssg.config import Config
from nkssg.structure.singles import Single


@pytest.mark.parametrize("permalink, expected", [
    ("/fix/", "/fix/"),                         # fix
    ("/%Y/%m/%d/", "/2001/02/03/"),             # date
    ("/pre/%Y/%m/%d/", "/pre/2001/02/03/"),     # date with prefix
    ("/%Y%m%d/%H%M%S/", "/20010203/040506/"),   # datetime
    ("/{slug}/", "/sample-slug/"),              # slug
    ("/{filename}/", "/sample%20post/"),        # filename
])
def test_get_url_from_permalink_simple(permalink, expected):
    config = Config()
    config.update({
        'post_type': {
            'sample': {
                'add_prefix_to_url': False
            }
        }
    })
    dummy_path = config.docs_dir / 'sample' / 'sample post.md'
    single = Single(dummy_path, config)

    single.date = datetime.datetime(2001, 2, 3, 4, 5, 6)
    single.slug = 'sample-slug'

    result = single.get_url_from_permalink(permalink, None)
    assert result == expected


def test_get_url_from_permalink_filename_index():
    config = Config()
    config.update({'post_type': {'sample': {}}})
    dummy_path = config.docs_dir / 'sample' / 'dir1' / 'dir2' / 'index.md'
    single = Single(dummy_path, config)
    ret = single.get_url_from_permalink('/{filename}/', None)
    assert ret == '/dir2/'


def test_get_url_from_permalink_filename_top_index():
    config = Config()
    config.update({'post_type': {'sample': {'slug': 'new_post_type'}}})
    dummy_path = config.docs_dir / 'sample' / 'index.md'
    single = Single(dummy_path, config)
    ret = single.get_url_from_permalink('/{filename}/', 'new_post_type')
    assert ret == '/new_post_type/'
