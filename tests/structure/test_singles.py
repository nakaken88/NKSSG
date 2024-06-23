import datetime
from pathlib import Path
import pytest

from nkssg.structure.config import Config
from nkssg.structure.pages import Page
from nkssg.structure.singles import Single
from nkssg.structure.archives import Archive


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
    config.update({'post_type': {'sample': {}}})
    dummy_path = config.docs_dir / 'sample' / 'sample post.md'
    single = Single(dummy_path, config)

    single.date = datetime.datetime(2001, 2, 3, 4, 5, 6)
    single.slug = 'sample-slug'

    result = single.get_url_from_permalink(permalink, None, False)
    assert result == expected


@pytest.mark.parametrize("permalink, expected", [
    ("/%Y/%m/%d/", "/sample/2001/02/03/"),  # date
    ("/{slug}/", "/sample/sample-slug/"),   # slug
])
def test_get_url_from_permalink_prefix(permalink, expected):
    config = Config()
    config.update({'post_type': {'sample': {}}})
    dummy_path = config.docs_dir / 'sample' / 'sample post.md'
    single = Single(dummy_path, config)

    single.date = datetime.datetime(2001, 2, 3, 4, 5, 6)
    single.slug = 'sample-slug'

    result = single.get_url_from_permalink(permalink, 'sample', True)
    assert result == expected


@pytest.mark.parametrize("permalink, expected", [
    ("/{sample_top}/{slug}/", "/dir1/sample-post/"),
    ("/{sample_last}/{slug}/", "/dir3/sample-post/"),
    ("/{sample_all}/{slug}/", "/dir1/dir2/dir3/sample-post/"),
    ("/{sample_top}/{filename}/", "/dir1/sample%20post/"),
])
def test_get_url_from_permalink_section_normal(permalink, expected):
    config = Config()
    config.update({'post_type': {'sample': {}}})
    path_parts = 'sample/dir1/_200_dir2/_xx_dir3'.split('/')
    dummy_path = Path(config.docs_dir, *path_parts, 'sample post.md')

    single = Single(dummy_path, config)
    single.title = single._get_title()
    single.name = single._get_name()
    single.slug = single._get_slug('sample')

    archive_list: list[Archive] = []
    archive_list.append(Archive(None, '/'))

    p = Archive(None, '/')
    for part in ['section', *path_parts]:
        c = Archive(p, part)
        c.slug = Page.to_slug(Page.clean_name(c.id.name))
        c.parent = p
        p = c
    single.archive_list = [c]

    result = single.get_url_from_permalink(permalink, None, False)
    assert result == expected


@pytest.mark.parametrize("permalink, expected", [
    ("/{sample_all}/{slug}/", "/dir1/dir2/dir3/"),
])
def test_get_url_from_permalink_section_index(permalink, expected):
    config = Config()
    config.update({'post_type': {'sample': {}}})
    path_parts = 'sample/dir1/_200_dir2/_xx_dir3'.split('/')
    dummy_path = Path(config.docs_dir, *path_parts, 'index.md')

    single = Single(dummy_path, config)
    single.title = single._get_title()
    single.name = single._get_name()
    single.slug = single._get_slug('sample')

    archive_list: list[Archive] = []
    archive_list.append(Archive(None, '/'))

    p = Archive(None, '/')
    for part in ['section', *path_parts]:
        c = Archive(p, part)
        c.slug = Page.to_slug(Page.clean_name(c.id.name))
        c.parent = p
        p = c
    single.archive_list = [c]

    result = single.get_url_from_permalink(permalink, None, False)
    assert result == expected


@pytest.mark.parametrize("permalink, expected", [
    ("/{sample_all}/{slug}/", "/new_sample/"),
])
def test_get_url_from_permalink_section_top(permalink, expected):
    config = Config()
    config.update({'post_type': {'sample': {'slug': 'new_sample'}}})
    dummy_path = Path(config.docs_dir, 'sample', 'index.md')

    single = Single(dummy_path, config)
    single.title = single._get_title()
    single.name = single._get_name()
    single.slug = single._get_slug('sample')

    archive_list: list[Archive] = []
    archive_list.append(Archive(None, '/'))

    p = Archive(None, '/')
    for part in ['section', 'sample']:
        c = Archive(p, part)
        c.slug = Page.to_slug(Page.clean_name(c.id.name))
        c.parent = p
        p = c
    single.archive_list = [c]

    result = single.get_url_from_permalink(permalink, 'new_sample', True)
    assert result == expected
