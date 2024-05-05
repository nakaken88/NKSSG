from pathlib import Path
import shutil
import tempfile

from livereload import Server

from nkssg.config import Config
from nkssg.structure.site import Site


def build(config: Config, clean=False):

    site = Site(config)
    site.setup()
    site.update()

    public_dir = config.public_dir
    if clean and public_dir.exists():
        shutil.rmtree(public_dir)

    public_dir.mkdir(exist_ok=True)
    site.output()


def start_server(config: Config, watch_path_list, port=5500):
    def reload():
        build(config)

    reload()

    try:
        server = Server()
        for watch_path in watch_path_list:
            server.watch(str(watch_path), reload)
        server.serve(port=port, root=config.public_dir, open_url_delay=None)
    finally:
        shutil.rmtree(config.public_dir)


def serve(config: Config, static=False, port=5500):

    config.site.site_url = f'http://127.0.0.1:{port}'
    config.public_dir = Path(tempfile.mkdtemp(prefix='nkssg_'))
    print(f'{config.public_dir} is created.')

    watch_path_list = []
    if not static:
        watch_path_list.append(config.docs_dir)
        if config.themes_dir.exists():
            watch_path_list.append(config.themes_dir)

    start_server(config, watch_path_list, port)


def draft(config: Config, path, port=5500):

    draft_path = Path(path)
    if not draft_path.is_absolute():
        draft_path = config.base_dir / draft_path

    config['draft_path'] = draft_path
    config.site.site_url = f'http://127.0.0.1:{port}'
    config.public_dir = Path(tempfile.mkdtemp(prefix='nkssg_'))

    start_server(config, [config['draft_path']], port)
