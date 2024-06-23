import fnmatch
from pathlib import Path
import shutil

import jinja2

from nkssg.structure.archives import Archives
from nkssg.structure.config import Config
from nkssg.structure.plugins import Plugins
from nkssg.structure.singles import Singles
from nkssg.structure.themes import Themes


class Site:
    def __init__(self, config: Config):
        self.config = config

        self.plugins: Plugins = Plugins(config)
        self.config = self.plugins.do_action(
            'after_load_plugins', target=self.config)

        self.themes = Themes(self.config)
        self.themes = self.plugins.do_action(
            'after_load_theme', target=self.themes)

        self.config = self.setup_post_types()
        self.config = self.plugins.do_action(
            'after_setup_post_types', target=self.config)

        self.singles = Singles(self.config, self.plugins)
        self.archives = Archives(self.config, self.plugins)

    def setup_post_types(self):
        config: Config = self.config
        config = self.add_missing_post_types(config)
        config = self.handle_missing_home_template(config)
        return config

    def add_missing_post_types(self, config: Config):
        for d in config.docs_dir.glob('*'):
            if d.is_dir():
                post_type = d.parts[-1]
                if post_type not in config.post_type.keys():
                    config.post_type.update({post_type: {}})
        return config

    def handle_missing_home_template(self, config: Config):
        home_template = self.themes.lookup_template(['home.html'])

        if not home_template:
            _, post_type_config = next(iter(config.post_type.items()))

            post_type_config.add_prefix_to_url = False
            if post_type_config.archive_type == 'none':
                post_type_config.archive_type = 'section'

        return config

    def setup(self):
        self.singles.setup()

    def update(self):
        self.config.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.themes.dirs)
        )
        self.config.env.globals.update({
            'config': self.config,
            'singles': self.singles,
            'archives': self.archives,
            'theme': self.themes.cnf
        })
        self.config = self.plugins.do_action(
            'after_setup_env', target=self.config)

        if self.config['mode'] != 'draft':
            self.archives.setup(self.singles)
            self.singles.update_urls()
            self.archives.update_urls()
            self.plugins.do_action('after_update_urls', target=self)

        self.singles.update_htmls(self.archives, self.themes)
        self.archives.update_htmls(self.themes)
        self.plugins.do_action('after_update_site', target=self)

    def output(self):
        self.copy_static_files()
        self.singles.output()
        self.plugins.do_action('after_output_singles', target=self)

        if self.config['mode'] != 'draft':
            self.archives.output()
            self.plugins.do_action('after_output_archives', target=self)
            self.output_extra_pages()

        self.plugins.do_action('after_output_site', target=self)
        self.plugins.do_action('on_end', target=self)

    def copy_static_files(self):
        def copy_file_if_newer(src: Path, dest: Path):
            if dest.exists() and src.stat().st_mtime <= dest.stat().st_mtime:
                return
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)

        for f in self.config.static_dir.glob('**/*'):
            if f.is_file():
                rel_path = f.relative_to(self.config.static_dir)
                to_path = self.config.public_dir / rel_path
                copy_file_if_newer(f, to_path)

        for d in self.themes.dirs:
            for f in d.glob('**/*'):
                if f.is_file() and self.is_target(f.relative_to(d.parent)):
                    rel_path = f.relative_to(d.parent)
                    to_path = self.config.public_dir / 'themes' / rel_path
                    copy_file_if_newer(f, to_path)

    def is_target(self, rel_path):
        for pattern in self.themes.cnf.get('static_exclude', []):
            if fnmatch.fnmatch(rel_path, pattern):
                return False

        for pattern in self.themes.cnf.get('static_include', []):
            if fnmatch.fnmatch(rel_path, pattern):
                return True
        return False

    def output_extra_pages(self):
        theme_config = self.themes.cnf
        extra_pages = theme_config.get('extra_pages', [])
        extra_pages = set(extra_pages + self.config.extra_pages)

        for extra_page in extra_pages:
            template_path = self.themes.lookup_template(extra_page)
            if template_path:
                self.output_extra_page(extra_page, template_path)
            elif extra_page not in self.config.extra_pages:
                print(f'{extra_page} is not found on extra pages')

    def output_extra_page(self, extra_page, template_path):
        template = self.config.env.get_template(template_path)
        html = template.render()

        if extra_page == 'home.html':
            output_path = 'index.html'
        elif extra_page in self.config.extra_pages:
            output_path = extra_page
        else:
            output_path = template_path

        output_path = self.config.public_dir / output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='UTF-8') as f:
            f.write(html)
