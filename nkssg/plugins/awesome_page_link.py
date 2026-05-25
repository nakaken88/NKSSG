import re

from nkssg.structure.plugins import BasePlugin
from nkssg.structure.singles import Single
from nkssg.structure.site import Site


class AwesomePageLinkPlugin(BasePlugin):
    """Converts page links marked with a keyword suffix (default: '?') to absolute URLs.
    Supports relative paths, absolute paths (with strip_paths), and file ID (':id?').
    Only Singles are processed; Archives are excluded by design.
    """

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

        for single in site.singles:
            self.update_page_link(single)
        return site

    def update_page_link(self, single: Single):
        docs_dir = self.site.config.docs_dir
        singles = self.site.singles
        keyword = self.keyword

        if not any(keyword + quote in single.content for quote in ['"', "'"]):
            return

        replacers = []

        for tag in AwesomePageLinkPlugin.href_pattern.finditer(single.content):
            href = tag.group(1)
            if not href.endswith(keyword):
                continue

            href = href[:-len(keyword)]
            if href.startswith(':'):
                href = href[1:]
                old_link, suffix = self.split_url(href)

                target = singles.file_ids.get(old_link)
                if target:
                    new_link = target.url + suffix
                else:
                    raise ValueError(
                        f'Error: File ID "{href}" is not found on {single}')

            else:
                for strip_path in self.strip_paths:
                    if href.startswith(strip_path):
                        href = href[len(strip_path):]

                old_link, suffix = self.split_url(href)

                if old_link.startswith('/'):
                    new_path = docs_dir / old_link[1:]
                else:
                    new_path = docs_dir / single.src_path.parent / old_link

                new_path = new_path.resolve()
                new_path = new_path.relative_to(docs_dir)

                if new_path.as_posix() in singles.src_paths.keys():
                    target = singles.src_paths[new_path.as_posix()]
                    new_link = target.url + suffix
                else:
                    new_link = old_link + suffix

            old_text = tag.group(0)
            new_text = old_text.replace(tag.group(1), new_link)
            replacers.append([tag.start(), tag.end(), new_text])

        self.apply_replacements(single, replacers)

    def apply_replacements(self, single: Single, replacers: list):
        text = single.content
        for replacer in replacers[::-1]:
            s, e, new_text = replacer
            text = text[:s] + new_text + text[e:]
        single.content = text

    def split_url(self, url: str):
        for delimiter in ['?', '#']:
            index = url.find(delimiter)
            if index != -1:
                return url[:index], url[index:]
        return url, ''
