from pathlib import Path, PurePath
import shutil
from urllib.parse import quote, unquote

from nkssg.structure.config import Config


class Pages:
    def __init__(self):
        self.config: Config = None
        self.pages: list[Page] = []

    def __iter__(self):
        return iter(self.pages)

    def setup(self):
        pass

    def update(self):
        pass

    def output(self):
        for page in self.pages:
            page.output(self.config)


class Page:
    def __init__(self):
        self.id: PurePath = PurePath('')
        self.file_id = ''

        self.meta = {}
        self.title = ''
        self.name = ''
        self.slug = ''
        self.content: str = ''
        self.summary = ''
        self.image = {}

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
        self.aliases = []

        self.page_type = ''
        self.archive_list = []

        self.shouldUpdateHtml = True
        self.shouldOutput = True

    @property
    def archive_type(self):
        return self.id.parts[1] if len(self.id.parts) >= 2 else ''

    @staticmethod
    def to_slug(dirty_slug: str):
        return dirty_slug.replace(' ', '-').lower()

    @staticmethod
    def clean_name(dirty_name: str):
        if not dirty_name.startswith('_'):
            return dirty_name
        if dirty_name.startswith('__'):
            return dirty_name[1:]

        parts = dirty_name.split('_')
        if len(parts) <= 2:
            return dirty_name

        prefix = f'_{parts[1]}_'
        suffix = dirty_name[len(prefix):]
        return suffix if suffix else dirty_name

    def output(self, config: Config):
        if not self.shouldOutput:
            return

        output_path = config.public_dir / self.dest_path
        output_dir = output_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='UTF-8') as f:
            f.write(self.html)

        if self.image:
            old_path: Path = self.image.get('old_path')
            new_path: Path = self.image.get('new_path')

            if old_path and new_path:
                new_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(str(old_path), str(new_path))

        if self.meta.get('aliases'):
            self.output_aliases(config)

    def _get_url_from_dest(self, dest_path=''):

        dest_path = dest_path or self.dest_path
        if not dest_path:
            raise ValueError(f'Destination path error on {self.id}')

        parts = Path(dest_path).parts

        if len(parts) == 1 and parts[-1] == 'index.html':
            url = '/'
        elif parts[-1] == 'index.html':
            url = '/' + '/'.join(parts[:-1]) + '/'
        elif '.' in parts[-1]:
            url = '/' + '/'.join(parts)
        else:
            url = '/' + '/'.join(parts) + '/'
        return quote(url).lower()

    def _get_dest_from_url(self, url: str):
        url = url.strip('/')
        parts = unquote(url).split('/')
        if '.' not in parts[-1]:
            parts.append('index.html')
        return Path(*parts)

    def _url_setup(self, config: Config):
        if not self.rel_url:
            return

        site_url = (config.site.site_url or '/').rstrip('/')
        rel_url = self.rel_url.lstrip('/')
        self.abs_url = f'{site_url}/{rel_url}'

        self.url = self.abs_url if config.use_abs_url else self.rel_url

    def output_aliases(self, config: Config):
        for url in self.meta['aliases']:
            url = '/' + url.strip('/')
            if '.htm' not in url:
                url += '/'

            output_path = self._get_dest_from_url(url)
            output_path = config.public_dir / output_path
            output_path.parent.mkdir(parents=True, exist_ok=True)
            print(output_path)

            with open(output_path, 'w', encoding='UTF-8') as f:
                content = f'''
<!DOCTYPE html>
<html>
<head>
<meta charset="uft-8">
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
'''
                f.write(content)
