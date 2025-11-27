from pathlib import Path

import click

from nkssg.command import build, new
from nkssg.structure.config import Config


def load_config(mode):
    config = Config.from_file()
    config['mode'] = mode
    return config


@click.group()
def cli():
    pass


@cli.command(name='build')
@click.option('--clean', '-c', is_flag=True)
def build_command(clean):

    config = load_config('build')
    build.build(config, clean)


@cli.command(name='serve')
@click.option('--static', '-s', is_flag=True)
@click.option('--all', '-a', is_flag=True)
@click.option('--port', '-p', default=5500)
def build_serve(static, all, port):

    config = load_config('serve')
    config['serve_all'] = all
    build.serve(config, static, port)


@cli.command(name='draft')
@click.argument('path')
@click.option('--port', '-p', default=5500)
def build_draft(path, port):

    config = load_config('draft')
    build.draft(config, path, port)


@cli.command(name="new")
@click.argument('name')
@click.argument('path', default='.', required=False)
def new_project(name, path):

    if name == 'site':
        new.site(path)
    else:
        config = load_config('new')
        new.page(name, path, config)


if __name__ == '__main__':
    cli()
