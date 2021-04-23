import collections
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from nkssg.structure.plugins import BasePlugin
import time

class AwesomePageLinkPlugin(BasePlugin):
    def after_update_site(self, site, **kwargs):
        mode = site.config.get('mode') or 'draft'
        if mode == 'draft':
            return site

        self.site_config = site.config
        self.singles = site.singles
        self.file_ids = self.singles.file_ids

        self.keyword = self.config.get('keyword') or '?'
        self.strip_paths = self.config.get('strip_paths') or []

        for page in site.singles:
            self.update_page_link(page)
        for page in site.archives.pages:
            self.update_page_link(page)
        return site

    def update_page_link(self, page):
        config = self.site_config
        keyword = self.keyword

        if not keyword + '"' in page.html and not keyword + '"' in page.html:
            return

        soup = BeautifulSoup(page.html, 'html.parser')

        links = soup.find_all('a')

        for link in links:
            href = link.get('href')
            if href is None:
                continue
            if not href.endswith(keyword):
                continue

            href = href[:-len(keyword)]
            if href[0] == ':':
                href = href[1:]
                old_link, suffix = self.split_url(href)

                if self.file_ids.get(old_link):
                    new_link = self.file_ids[old_link].url + suffix
                else:
                    print('Error: File ID "' + href + '" is not found')
                    print(' on ' + str(page.src_path))
                    raise Exception('File ID error')

            else:
                for strip_path in self.strip_paths:
                    if len(href) >= len(strip_path) and href[:len(strip_path)] == strip_path:
                        href = href[len(strip_path):]

                old_link, suffix = self.split_url(href)

                if old_link[0] == '/':
                    new_path = config['docs_dir'] / old_link[1:]
                else:
                    new_path = config['docs_dir'] / page.src_path.parent / old_link
                    
                new_path = new_path.resolve()
                new_path = new_path.relative_to(config['docs_dir'])


                new_link = old_link + suffix
                if str(new_path) in self.singles.src_paths.keys():
                    single = self.singles.src_paths[str(new_path)]
                    new_link = single.url + suffix

            link['href'] = new_link

        page.html = str(soup)

    def split_url(self, url):
        index = -1
        if url.find('?') != -1:
            index = url.find('?')
        elif url.find('#') != -1:
            index = url.find('#')

        if index != -1:
            return url[:(index)], url[(index):]
        return url, ''
