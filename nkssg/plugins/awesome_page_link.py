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

        self.site = site
        self.keyword = self.config.get('keyword', '?')
        self.strip_paths = self.config.get('strip_paths', [])

        for page in site.singles:
            self.update_page_link(page)
        for page in site.archives:
            self.update_page_link(page)
        return site

    def update_page_link(self, page: Page):
        docs_dir = self.site.config.docs_dir
        singles = self.site.singles
        keyword = self.keyword

        if not any(keyword + quote in page.content for quote in ['"', "'"]):
            return

        replacers = []

        for tag in AwesomePageLinkPlugin.href_pattern.finditer(page.content):
            href = tag.group(1)
            if not href.endswith(keyword):
                continue

            href = href[:-len(keyword)]
            if href.startswith(':'):
                href = href[1:]
                old_link, suffix = self.split_url(href)

                if singles.file_ids.get(old_link):
                    new_link = singles.file_ids[old_link].url + suffix
                else:
                    raise ValueError(
                        f'Error: File ID "{href}" is not found on {page}')

            else:
                for strip_path in self.strip_paths:
                    if href.startswith(strip_path):
                        href = href[len(strip_path):]

                old_link, suffix = self.split_url(href)

                if old_link.startswith('/'):
                    new_path = docs_dir / old_link[1:]
                else:
                    new_path = docs_dir / page.src_path.parent / old_link

                new_path = new_path.resolve()
                new_path = new_path.relative_to(docs_dir)

                if str(new_path) in singles.src_paths.keys():
                    single = singles.src_paths[str(new_path)]
                    new_link = single.url + suffix
                else:
                    new_link = old_link + suffix

            old_text = tag.group(0)
            new_text = old_text.replace(tag.group(1), new_link)
            replacers.append([tag.start(), tag.end(), new_text])

        self.apply_replacements(page, replacers)

    def apply_replacements(self, page: Page, replacers: list):
        text = page.content
        for replacer in replacers[::-1]:
            s, e, new_text = replacer
            text = text[:s] + new_text + text[e:]
        page.content = text

    def split_url(self, url: str):
        for delimiter in ['?', '#']:
            index = url.find(delimiter)
            if index != -1:
                return url[:index], url[index:]
        return url, ''
