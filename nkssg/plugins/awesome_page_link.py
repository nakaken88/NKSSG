from pathlib import Path
import re

from nkssg.structure.plugins import BasePlugin


class AwesomePageLinkPlugin(BasePlugin):
    def after_update_urls(self, site, **kwargs):
        mode = site.config.get('mode') or 'draft'
        if mode == 'draft':
            return site

        self.site_config = site.config
        self.singles = site.singles
        self.file_ids = self.singles.file_ids
        self.keyword = self.config.get('keyword') or '?'
        self.strip_paths = self.config.get('strip_paths') or []
        self.pattern = re.compile(r'<a[^<>]+href\s*?=\s*?["\'](.*?)["\']', re.I)

        for page in site.singles:
            self.update_page_link(page)
        for page in site.archives.pages:
            self.update_page_link(page)
        return site

    def update_page_link(self, page):
        config = self.site_config
        keyword = self.keyword

        if not keyword + '"' in page.content and not keyword + '"' in page.content:
            return

        replacers = []

        for tag in self.pattern.finditer(page.content):
            href = tag.group(1)
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

            old_text = tag.group(0)
            new_text = old_text.replace(tag.group(1), new_link)
            replacers.append([tag.start(), tag.end(), new_text])

        text = page.content
        for replacer in replacers[::-1]:
            s = replacer[0]
            e = replacer[1]
            new_text = replacer[2]
            text = text[:s] + new_text + text[e:]

        page.content = text

    def split_url(self, url):
        index = -1
        if url.find('?') != -1:
            index = url.find('?')
        elif url.find('#') != -1:
            index = url.find('#')

        if index != -1:
            return url[:(index)], url[(index):]
        return url, ''
