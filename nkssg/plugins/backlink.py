from nkssg.structure.plugins import BasePlugin
import re
from urllib.parse import quote


class BacklinkPlugin(BasePlugin):
    def after_update_urls(self, site, **kwargs):
        target = site.singles
        pattern = re.compile(r'<a[^<>]+href\s*?=\s*?["\'](.*?)["\']', re.I)
        for page in target:
            to_links = set()
            for tag in pattern.finditer(page.content):
                href = tag.group(1)
                if 'http' in href:
                    if site.config['site']['site_url'] in href:
                        href = href.replace(site.config['site']['site_url'], '')
                    else:
                        continue
                if '#' in href:
                    href = href[:(href.find('#'))]
                if '?' in href:
                    href = href[:(href.find('?'))]
                if href == '': continue
                to_links.add(href)
            page.to_links = to_links
            page.back_links = set()

        urls = {str(page.rel_url): page for page in target}
        for page in target:
            for link in page.to_links:
                quote_link = quote(link).lower()
                if quote_link in urls:
                    urls[quote_link].back_links.add(page)
                    

