import types
from pathlib import Path

import pytest

from nkssg.plugins.backlink import BacklinkPlugin
from nkssg.structure.config import Config
from nkssg.structure.singles import Single


@pytest.fixture
def site_setup():
    config = Config.from_file()
    config.site.site_url = "http://example.com"
    config.site.site_url_original = "http://example.com"

    site = types.SimpleNamespace()
    site.config = config
    return site


def test_backlink_plugin_relative_link(site_setup):
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


def test_backlink_plugin_handles_fragments_and_queries(site_setup):
    site = site_setup
    config = site.config

    page_g = Single(abs_src_path=config.docs_dir / "post/page_g.md", config=config)
    page_h = Single(abs_src_path=config.docs_dir / "post/page_h.md", config=config)
    page_i = Single(abs_src_path=config.docs_dir / "post/page_i.md", config=config)

    page_g.rel_url = '/page-g/'
    page_h.rel_url = '/page-h/'
    page_i.rel_url = '/page-i/'

    page_g.content = (
        f'''<p>Link with fragment <a href="{page_h.rel_url}#section">Page H</a> '''
        f'''and link with query <a href="{page_i.rel_url}?param=1">Page I</a>.</p>'''
    )
    page_h.content = '<p>Page H</p>'
    page_i.content = '<p>Page I</p>'

    site.singles = [page_g, page_h, page_i]

    plugin = BacklinkPlugin()
    plugin.after_update_urls(site)

    assert page_h in page_g.to_links
    assert page_i in page_g.to_links
    assert len(page_g.to_links) == 2

    assert page_g in page_h.back_links
    assert page_g in page_i.back_links
    assert len(page_h.back_links) == 1
    assert len(page_i.back_links) == 1


def test_backlink_plugin_is_case_insensitive(site_setup):
    site = site_setup
    config = site.config

    page_j = Single(abs_src_path=config.docs_dir / "post/page_j.md", config=config)
    page_k = Single(abs_src_path=config.docs_dir / "post/page_k.md", config=config)

    page_j.rel_url = '/page-j/'
    page_k.rel_url = '/page-k/'
    page_j.content = f'<p>Link to <a href="/Page-K/">Page K</a>.</p>'
    page_k.content = '<p>Page K</p>'

    site.singles = [page_j, page_k]

    plugin = BacklinkPlugin()
    plugin.after_update_urls(site)

    assert page_k in page_j.to_links
    assert len(page_j.to_links) == 1
    assert page_j in page_k.back_links
    assert len(page_k.back_links) == 1


def test_backlink_plugin_handles_duplicate_links(site_setup):
    site = site_setup
    config = site.config

    page_l = Single(abs_src_path=config.docs_dir / "post/page_l.md", config=config)
    page_m = Single(abs_src_path=config.docs_dir / "post/page_m.md", config=config)

    page_l.rel_url = '/page-l/'
    page_m.rel_url = '/page-m/'
    page_l.content = (
        f'<p>Link to <a href="{page_m.rel_url}">Page M</a>. '
        f'And another link to <a href="{page_m.rel_url}">Page M again</a>.</p>'
    )
    page_m.content = '<p>Page M</p>'

    site.singles = [page_l, page_m]

    plugin = BacklinkPlugin()
    plugin.after_update_urls(site)

    assert page_m in page_l.to_links
    assert len(page_l.to_links) == 1
    assert page_l in page_m.back_links
    assert len(page_m.back_links) == 1


def test_backlink_plugin_handles_self_links(site_setup):
    site = site_setup
    config = site.config

    page_n = Single(abs_src_path=config.docs_dir / "post/page_n.md", config=config)
    page_n.rel_url = '/page-n/'
    page_n.content = f'<p>A link to <a href="{page_n.rel_url}">myself</a>.</p>'

    site.singles = [page_n]

    plugin = BacklinkPlugin()
    plugin.after_update_urls(site)

    assert page_n in page_n.to_links
    assert len(page_n.to_links) == 1
    assert page_n in page_n.back_links
    assert len(page_n.back_links) == 1


def test_backlink_plugin_ignores_nonexistent_links(site_setup):
    site = site_setup
    config = site.config

    page_o = Single(abs_src_path=config.docs_dir / "post/page_o.md", config=config)
    page_o.rel_url = '/page-o/'
    page_o.content = '<p>A link to <a href="/nonexistent-page/">a ghost</a>.</p>'

    site.singles = [page_o]

    plugin = BacklinkPlugin()
    plugin.after_update_urls(site)

    assert len(page_o.to_links) == 0
    assert len(page_o.back_links) == 0
    # The text of the link is still recorded
    assert '/nonexistent-page/' in page_o.to_links_text
    assert len(page_o.to_links_text) == 1
