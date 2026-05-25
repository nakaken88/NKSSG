from pathlib import Path
import logging
import re
import shutil

from nkssg.structure.plugins import BasePlugin
from nkssg.structure.singles import Singles, Single
from nkssg.structure.site import Site


class AwesomeImgLinkPlugin(BasePlugin):

    src_pattern = re.compile(
        r'<img\s+'                # Opening tag and space
        r'[^>]*?'                 # Any attributes
        r'src\s*=\s*'             # src attribute
        r'["\'](.*?)["\']',       # Attribute value
        re.I | re.S
    )

    def after_update_singles_html(self, singles: Singles, **kwargs):
        mode = singles.config.get('mode', 'draft')
        if mode == 'draft':
            return singles

        self.site_config = singles.config
        self.keyword = self.config.get('keyword', '?')
        self.strip_paths = self.config.get('strip_paths', [])

        for page in singles:
            page.imgs = []
            self.update_img_link(page)
        return singles

    def update_img_link(self, page: Single):
        keyword = self.keyword

        if not any(keyword + quote in page.html for quote in ['"', "'"]):
            return

        replacers = []

        for tag in AwesomeImgLinkPlugin.src_pattern.finditer(page.html):
            src = tag.group(1)
            if not src.endswith(keyword):
                continue

            src = src[:-len(keyword)]
            for strip_path in self.strip_paths:
                if src.startswith(strip_path):
                    src = src[len(strip_path):]

            old_link = src
            if old_link.startswith('/'):
                old_path_rel = Path(old_link[1:])
            else:
                old_path_rel = page.src_path.parent / old_link

            new_path_rel = page.dest_dir / old_path_rel.name
            new_src = './' + old_path_rel.name

            old_text = tag.group(0)
            new_text = old_text.replace(tag.group(1), new_src)
            replacers.append([tag.start(), tag.end(), new_text])

            page.imgs.append({'old_path': old_path_rel, 'new_path': new_path_rel})

        for s, e, new_html in replacers[::-1]:
            page.html = page.html[:s] + new_html + page.html[e:]

    def after_output_singles(self, site: Site, **kwargs):
        config = site.config
        for page in site.singles:
            for img in getattr(page, 'imgs', []):
                old_path = config.docs_dir / img['old_path']
                new_path = config.public_dir / img['new_path']

                if not old_path.exists():
                    logging.warning(f'{old_path} is not found on {page}')
                    continue
                if new_path.exists():
                    continue

                shutil.copyfile(old_path, new_path)
