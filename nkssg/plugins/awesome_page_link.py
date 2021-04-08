import collections
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from nkssg.structure.plugins import BasePlugin


class AwesomePageLinkPlugin(BasePlugin):
    def after_update_site(self, site, **kwargs):
        self.site_config = site.config
        self.singles = site.singles

        self.keyword = self.config.get('keyword') or '?'
        self.strip_paths = self.config.get('strip_paths') or []

        # setting url ids
        target_pages = [page for page in self.singles if page.meta.get('url_id')]
        url_id_list = [str(page.meta['url_id']) for page in target_pages]
        url_id_counter = collections.Counter(url_id_list)

        url_id_check = True
        for k, v in url_id_counter.items():
            if v > 1:
                print('Error: URL ID "' + k + '" is duplicated')
                for page in target_pages:
                    if str(page.meta['url_id']) == k:
                        print('- ' + str(page.src_path))
                url_id_check = False

        if not url_id_check:
            raise Exception('URL ID error')

        self.url_ids = {str(page.meta['url_id']): page for page in target_pages}


        for page in site.singles:
            self.update_page_link(page)
        for page in site.archives:
            self.update_page_link(page)
        return site

    def update_page_link(self, page):
        config = self.site_config
        keyword = self.keyword

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

                if self.url_ids.get(old_link):
                    new_link = self.url_ids[old_link].url + suffix
                else:
                    print('Error: URL ID "' + href + '" is not found')
                    print(' on ' + str(page.src_path))
                    raise Exception('URL ID error')

            else:
                for strip_path in self.strip_paths:
                    href = href.removeprefix(strip_path)

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
