from pathlib import Path
import shutil
import tempfile

from livereload import Server

from nkssg.structure.site import Site


def build(config, clean=False):

    site = Site(config)

    site.setup()
    site.update()

    if clean:
        public_dir = config['public_dir']
        if public_dir.exists():
            shutil.rmtree(public_dir)

        public_dir.mkdir()

    site.output()


def serve(config, static=False, port=5500):

    config['site']['site_url'] = 'http://127.0.0.1:' + str(port)
    config['public_dir'] = Path(tempfile.mkdtemp(prefix='nkssg_'))
    print(str(config['public_dir']) + ' is created.')

    def reload():
        build(config)

    reload()

    try:
        server = Server()
        if not static:
            server.watch(config['docs_dir'], reload)
            for dir in config['themes'].dirs:
                server.watch(dir, reload)

        server.serve(port=port, root=config['public_dir'], open_url_delay=None)
    finally:
        shutil.rmtree(config['public_dir'])
    

def draft(config, path, port=5500):

    draft_path = Path(path)
    if not draft_path.is_absolute():
        draft_path = config['base_dir'] / draft_path

    config['draft_path'] = draft_path
    config['site']['site_url'] = 'http://127.0.0.1:' + str(port)
    config['public_dir'] = Path(tempfile.mkdtemp(prefix='nkssg_'))

    def reload():
        build(config)

    reload()

    try:
        server = Server()
        server.watch(config['draft_path'].parent, reload)
        server.serve(port=port, root=config['public_dir'], open_url_delay=None)
    finally:
        shutil.rmtree(config['public_dir'])
    
