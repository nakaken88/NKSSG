import click

from nkssg.command import build, new
from nkssg.structure.config import Config


@click.group()
def cli():
    pass


@cli.command(name='build')
def build_command():

    config = Config.from_file(mode='build')
    build.build(config)


@cli.command(name='clean')
def clean_command():

    config = Config.from_file(mode='build')
    build.clean(config)


@cli.command(name='serve')
@click.option('--static', '-s', is_flag=True)
@click.option('--all', '-a', 'serve_all', is_flag=True)
@click.option('--port', '-p', default=5500)
def build_serve(static, serve_all, port):

    config = Config.from_file(mode='serve')
    config['serve_all'] = serve_all
    build.serve(config, static, port)


@cli.command(name='draft')
@click.argument('path')
@click.option('--port', '-p', default=5500)
def build_draft(path, port):

    config = Config.from_file(mode='draft')
    build.draft(config, path, port)


@cli.command(name="new")
@click.argument('name')
@click.argument('path', default='.', required=False)
def new_project(name, path):

    if name == 'site':
        new.site(path)
    else:
        config = Config.from_file(mode='new')
        new.page(name, path, config)


if __name__ == '__main__':
    cli()
