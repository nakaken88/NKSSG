import re

from nkssg.structure.pages import Page
from nkssg.structure.plugins import BasePlugin
from nkssg.structure.site import Site


class AwesomePageLinkPlugin(BasePlugin):

    href_pattern = re.compile(
        r'<a\s+'                # Opening tag and space
        r'[^>]*?'               # Any attributes
        r'href\s*=\s*'          # href attribute
        r'["\'](.*?)["\']',     # Attribute value
        re.I | re.S
    )

    def after_update_urls(self, site: Site, **kwargs):
        mode = site.config.get('mode') or 'draft'
        if mode == 'draft':
            return site

        self.site_config = site.config
        self.singles = site.singles
        self.file_ids = self.singles.file_ids
        self.keyword = self.config.get('keyword', '?')
        self.strip_paths = self.config.get('strip_paths', [])

        for page in site.singles:
            self.update_page_link(page)
        for page in site.archives:
            self.update_page_link(page)
        return site

    def update_page_link(self, page: Page):
        config = self.site_config
        keyword = self.keyword

        if not any(keyword + quote in page.content for quote in ['"', "'"]):
            return

        replacers = []

        for tag in AwesomePageLinkPlugin.href_pattern.finditer(page.content):
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

    def split_url(self, url: str):
        for delimiter in ['?', '#']:
            index = url.find(delimiter)
            if index != -1:
                return url[:index], url[index:]
        return url, ''
