from pathlib import Path

import click

from nkssg.command import build, new
from nkssg.config import load_config


PKG_DIR = Path(__file__).resolve().parent


@click.group()
def cli():
    pass


@cli.command(name='build')
@click.option('--clean', '-c', is_flag=True)
def build_command(clean):

    config = load_config(mode='build')
    config['PKG_DIR'] = PKG_DIR
    config['build_clean'] = clean
    build.build(config, clean)


@cli.command(name='serve')
@click.option('--static', '-s', is_flag=True)
@click.option('--all', '-a', is_flag=True)
@click.option('--port', '-p', default=5500)
def build_serve(static, all, port):

    config = load_config(mode='serve')
    config['PKG_DIR'] = PKG_DIR
    config['serve_all'] = all

    build.serve(config, static, port)


@cli.command(name='draft')
@click.argument('path')
@click.option('--port', '-p', default=5500)
def build_draft(path, port):

    config = load_config(mode='draft')
    config['PKG_DIR'] = PKG_DIR
    build.draft(config, path, port)


@cli.command(name="new")
@click.argument('name')
@click.argument('path', default='.', required=False)
def new_project(name, path):

    if name == 'site':
        new.site(path, PKG_DIR)
    else:
        config = load_config(mode='new')
        config['PKG_DIR'] = PKG_DIR
        new.page(name, path, config)


if __name__ == '__main__':
    cli()
