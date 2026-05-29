from pathlib import Path, PurePath
import shutil
from typing import TYPE_CHECKING
from urllib.parse import quote, unquote

from nkssg.structure.config import Config

if TYPE_CHECKING:
    from nkssg.structure.archives import Archive


class Page:
    def __init__(self):
        self.id: PurePath = PurePath('')
        self.file_id = ''

        self.meta: dict = {}
        self.title = ''
        self.name = ''
        self.slug = ''
        self.content: str = ''
        self.summary = ''
        self.image: dict = {}

        self.status = 'public'
        self.is_draft = False
        self.is_expired = False
        self.is_future = False

        self.html: str = ''
        self.url = '/'
        self.abs_url = ''
        self.rel_url = ''
        self.dest_path: Path = Path('index.html')
        self.dest_dir = ''
        self.aliases: list[str] = []

        self.page_type = ''
        self.archive_type = ''
        self.archive_list: list['Archive'] = []

        self.should_update_html = True
        self.should_output = True
        self.page_number = 0

    @staticmethod
    def to_slug(dirty_slug: str) -> str:
        return dirty_slug.replace(' ', '-').lower()

    @staticmethod
    def clean_name(dirty_name: str) -> str:
        if dirty_name.startswith('__'):
            return dirty_name[1:]
        if not dirty_name.startswith('_'):
            return dirty_name
        second = dirty_name.find('_', 1)
        if second == -1 or second == len(dirty_name) - 1:
            return dirty_name
        return dirty_name[second + 1:]

    def output(self, config: Config) -> None:
        if not self.should_output:
            return

        output_path = config.public_dir / self.dest_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.html, encoding='utf-8')

        if self.image:
            old_path: Path | None = self.image.get('old_path')
            new_path: Path | None = self.image.get('new_path')

            if old_path and new_path:
                new_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(old_path, new_path)

        if self.meta.get('aliases'):
            self.output_aliases(config)

    def _get_url_from_dest(self, dest_path: Path | str = '') -> str:

        dest_path = dest_path or self.dest_path
        if not dest_path:
            raise ValueError(f'Destination path error on {self.id}')

        parts = Path(dest_path).parts
        if parts[-1] == 'index.html':
            inner = '/'.join(parts[:-1])
            url = f'/{inner}/' if inner else '/'
        elif '.' in parts[-1]:
            url = '/' + '/'.join(parts)
        else:
            url = '/' + '/'.join(parts) + '/'
        return quote(url).lower()

    def _get_dest_from_url(self, url: str) -> Path:
        url = url.strip('/')
        parts = unquote(url).split('/')
        if '.' not in parts[-1]:
            parts.append('index.html')
        return Path(*parts)

    def _url_setup(self, config: Config) -> None:
        if not self.rel_url:
            return

        site_url = config.site.site_url.rstrip('/')
        rel_url = self.rel_url.lstrip('/')
        self.abs_url = f'{site_url}/{rel_url}'

        self.url = self.abs_url if config.use_abs_url else self.rel_url

    def output_aliases(self, config: Config) -> None:
        for alias in self.meta['aliases']:
            alias_url = '/' + alias.strip('/')
            if not alias_url.endswith(('.htm', '.html')):
                alias_url += '/'

            output_path = config.public_dir / self._get_dest_from_url(alias_url)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link rel="canonical" href="{self.url}"/>
<meta http-equiv="refresh" content="0;url={self.url}">
</head>
<body>
<p>
This page has moved.
Click <a href="{self.url}">here</a> to go to the new page.
</p>
</body>
</html>
''', encoding='utf-8')
