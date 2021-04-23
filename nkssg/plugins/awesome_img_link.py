from pathlib import Path
import shutil

from bs4 import BeautifulSoup

from nkssg.structure.plugins import BasePlugin


class AwesomeImgLinkPlugin(BasePlugin):
    def after_update_singles_html(self, singles, **kwargs):
        mode = singles.config.get('mode') or 'draft'
        if mode == 'draft':
            return singles

        self.site_config = singles.config
        self.keyword = self.config.get('keyword') or '?'
        self.strip_paths = self.config.get('strip_paths') or []

        for page in singles.pages:
            page.imgs = []
            self.update_img_link(page)
        return singles

    def update_img_link(self, page):
        config = self.site_config
        keyword = self.keyword

        if not keyword + '"' in page.html and not keyword + '"' in page.html:
            return

        soup = BeautifulSoup(page.html, 'html.parser')
        imgs = soup.find_all('img')
        srcs = []

        for img in imgs:
            src = img['src']
            if src is None:
                continue
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

            srcs.append({'old_path': old_path, 'new_path': new_path})

            img['src'] = new_src

        if not srcs:
            return

        page.html = str(soup)
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
