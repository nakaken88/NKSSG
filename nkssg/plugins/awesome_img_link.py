from pathlib import Path
import re
import shutil

from nkssg.structure.plugins import BasePlugin


class AwesomeImgLinkPlugin(BasePlugin):
    def after_update_singles_html(self, singles, **kwargs):
        mode = singles.config.get('mode') or 'draft'
        if mode == 'draft':
            return singles

        self.site_config = singles.config
        self.keyword = self.config.get('keyword') or '?'
        self.strip_paths = self.config.get('strip_paths') or []
        self.pattern = re.compile(r'<img[^<>]+src\s*?=\s*?["\'](.*?)["\']', re.I)

        for page in singles.pages:
            page.imgs = []
            self.update_img_link(page)
        return singles

    def update_img_link(self, page):
        config = self.site_config
        keyword = self.keyword

        if not keyword + '"' in page.html and not keyword + '"' in page.html:
            return

        srcs = []
        replacers = []

        for tag in self.pattern.finditer(page.html):
            src = tag.group(1)
            if not src.endswith(keyword):
                continue

            src = src[:-len(keyword)]
            for strip_path in self.strip_paths:
                if len(src) >= len(strip_path) and src[:len(strip_path)] == strip_path:
                    src = src[len(strip_path):]

            old_link = src
            if old_link[0] == '/':
                old_path = config['docs_dir'] / old_link[1:]
            else:
                old_path = config['docs_dir'] / page.src_path.parent / old_link
                
            new_path = page.dest_dir / old_path.name
            new_src = './' + old_path.name

            old_text = tag.group(0)
            new_text = old_text.replace(tag.group(1), new_src)
            replacers.append([tag.start(), tag.end(), new_text])

            srcs.append({'old_path': old_path, 'new_path': new_path})

        text = page.html
        for replacer in replacers[::-1]:
            s = replacer[0]
            e = replacer[1]
            new_text = replacer[2]
            text = text[:s] + new_text + text[e:]

        page.html = text
        page.imgs = srcs


    def after_output_singles(self, site, **kwargs):
        config = site.config
        for page in site.singles:
            for img in getattr(page, 'imgs', []):
                old_path = config['docs_dir'] / img['old_path']
                new_path = config['public_dir'] / img['new_path']

                if not old_path.exists():
                    print(str(old_path) + ' is not found on ' + str(page.src_path))
                    continue
                if new_path.exists():
                    continue

                shutil.copyfile(str(old_path), str(new_path))
