import types
from pathlib import Path

import pytest

from nkssg.plugins.backlink import BacklinkPlugin
from nkssg.structure.config import Config
from nkssg.structure.singles import Single


@pytest.fixture
def site_setup():
    """Provides a common setup for creating a mock site with config."""
    config = Config()
    config.load_config('nkssg.yml')
    config.site.site_url = "http://example.com"
    config.site.site_url_original = "http://example.com"

    site = types.SimpleNamespace()
    site.config = config
    return site


def test_backlink_plugin_relative_link(site_setup):
    """Test that BacklinkPlugin correctly handles relative internal links."""
    site = site_setup
    config = site.config

    page_a = Single(abs_src_path=config.docs_dir / "post/page_a.md", config=config)
    page_b = Single(abs_src_path=config.docs_dir / "post/page_b.md", config=config)

    page_a.rel_url = '/page-a/'
    page_b.rel_url = '/page-b/'
    page_a.content = f'''<p>This is page A. It links to <a href="{page_b.rel_url}">Page B</a>.</p>'''
    page_b.content = '''<p>This is page B. It has no outgoing links.</p>'''

    site.singles = [page_a, page_b]

    plugin = BacklinkPlugin()
    plugin.after_update_urls(site)

    assert page_b in page_a.to_links
    assert len(page_a.to_links) == 1
    assert page_a in page_b.back_links
    assert len(page_b.back_links) == 1
    assert len(page_a.back_links) == 0
    assert len(page_b.to_links) == 0


def test_backlink_plugin_absolute_internal_link(site_setup):
    """Test that BacklinkPlugin handles absolute internal links correctly."""
    site = site_setup
    config = site.config

    page_c = Single(abs_src_path=config.docs_dir / "post/page_c.md", config=config)
    page_d = Single(abs_src_path=config.docs_dir / "post/page_d.md", config=config)

    page_c.rel_url = '/page-c/'
    page_d.rel_url = '/page-d/'
    page_c.content = f'''<p>This is page C. It links to <a href="{config.site.site_url}{page_d.rel_url}">Page D</a>.</p>'''
    page_d.content = '''<p>This is page D.</p>'''

    site.singles = [page_c, page_d]

    plugin = BacklinkPlugin()
    plugin.after_update_urls(site)

    assert page_d in page_c.to_links
    assert len(page_c.to_links) == 1
    assert page_c in page_d.back_links
    assert len(page_d.back_links) == 1
    assert len(page_c.back_links) == 0
    assert len(page_d.to_links) == 0


def test_backlink_plugin_ignores_external_links(site_setup):
    """Test that BacklinkPlugin ignores external links and processes internal ones."""
    site = site_setup
    config = site.config

    page_e = Single(abs_src_path=config.docs_dir / "post/page_e.md", config=config)
    page_f = Single(abs_src_path=config.docs_dir / "post/page_f.md", config=config)

    page_e.rel_url = '/page-e/'
    page_f.rel_url = '/page-f/'
    page_e.content = (
        f'''<p>This is page E. It links to <a href="https://www.google.com">Google</a> '''
        f'''and also to <a href="{page_f.rel_url}">Page F</a>.</p>'''
    )
    page_f.content = '''<p>This is page F.</p>'''

    site.singles = [page_e, page_f]

    plugin = BacklinkPlugin()
    plugin.after_update_urls(site)

    assert page_f in page_e.to_links
    assert page_e in page_f.back_links
    assert len(page_e.to_links) == 1
    assert len(page_e.to_links_text) == 1
    assert len(page_f.to_links) == 0
    assert len(page_f.back_links) == 1

