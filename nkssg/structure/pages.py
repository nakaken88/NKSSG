from pathlib import Path
import shutil
from urllib.parse import quote, unquote, urljoin

from nkssg.utils import get_config_by_list


class Pages:
    def __init__(self):
        self.config = None
        self.pages = []

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
        self._id = 0
        self.file_id = ''

        self.src_path = ''
        self.abs_src_path = ''
        self.src_dir = ''

        self.archive_type = ''
        self.meta = {}
        self.title = ''
        self.name = ''
        self.slug = ''
        self.content = ''
        self.summary = ''
        self.image = {}

        self.html = ''
        self.url = ''
        self.abs_url = ''
        self.rel_url = ''
        self.dest_path = ''
        self.dest_dir = ''
        self.aliases = []

        self.page_type = ''
        self.archive_list = []

        self.shouldUpdateHtml = True
        self.shouldOutput = True

    def output(self, config):
        if not self.shouldOutput:
            return

        output_path = config['public_dir'] / self.dest_path
        output_dir = output_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='UTF-8') as f:
            f.write(self.html)

        if self.image:
            old_path = self.image.get('old_path')
            new_path = self.image.get('new_path')

            if old_path is not None and new_path is not None:
                new_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(str(old_path), str(new_path))

        if self.meta.get('aliases'):
            self.output_aliases(config)

    def _get_url_from_dest(self, dest_path=''):
        if dest_path == '':
            dest_path = self.dest_path
        if dest_path == '':
            try:
                raise Exception
            except Exception:
                print('Error: dest path error on ' + self.src_path)

        parts = list(Path(dest_path).parts)

        if parts[-1] == 'index.html':
            if len(parts) == 1:
                url = '/'
            else:
                url = '/' + '/'.join(parts[:-1]) + '/'
        else:
            url = '/' + '/'.join(parts[:-1])
        return quote(url).lower()

    def _get_dest_from_url(self, url):
        url = url.strip('/')
        if '.htm' not in url:
            url = url + '/index.html'
        parts = unquote(url).split('/')
        return Path(*parts)

    def _url_setup(self, config):
        if self.rel_url == '':
            return

        site_url = get_config_by_list(config, ['site', 'site_url']) or '/'
        _site_url = site_url.rstrip('/') + '/'
        _rel_url = self.rel_url.lstrip('/')
        self.abs_url = urljoin(_site_url, _rel_url)

        if config['use_abs_url']:
            self.url = self.abs_url
        else:
            self.url = self.rel_url

    def output_aliases(self, config):
        for url in self.meta['aliases']:
            url = '/' + url.strip('/')
            if '.htm' not in url:
                url = url + '/'

            output_path = self._get_dest_from_url(url)
            output_path = config['public_dir'] / output_path
            output_dir = output_path.parent
            output_dir.mkdir(parents=True, exist_ok=True)
            print(output_path)

            with open(output_path, 'w', encoding='UTF-8') as f:
                content = '''
<!DOCTYPE html>
<html>
<head>
<meta charset="uft-8">
<link rel="canonical" href="{url}"/>
<meta http-equiv="refresh" content="0;url={url}">
</head>
<body>
<p>This page has moved. Click <a href="{url}">here</a> to go to the new page.</p>
/body>
</html>
'''.format(url=self.url)
                f.write(content)

    def lookup_template(self, config):
        return 'main.html'
