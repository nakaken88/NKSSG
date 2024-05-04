import fnmatch
import json
from pathlib import Path
import shutil

import jinja2

from nkssg.config import Config
from nkssg.structure.archives import Archives
from nkssg.structure.plugins import Plugins
from nkssg.structure.singles import Singles
from nkssg.structure.themes import Themes
from nkssg.utils import get_config_by_list, to_slug


class Site:
    def __init__(self, config: Config):
        self.config = config

        self.plugins: Plugins = Plugins(config)
        self.config = self.plugins.do_action(
            'after_load_config', target=self.config)

        self.themes = Themes(self.config)
        self.config = self.plugins.do_action(
            'after_load_theme', target=self.config)

        self.config = self.setup_post_types()
        self.config = self.plugins.do_action(
            'after_setup_post_types', target=self.config)

        self.singles = Singles(self.config, self.plugins)
        self.archives = Archives(self.config, self.plugins)

    def setup_post_types(self):
        config: Config = self.config

        # remove post_types for which folder does not exist
        keys_to_remove = []
        for post_type in config.post_type.keys():
            if not Path(config.docs_dir, post_type).exists():
                keys_to_remove.append(post_type)

        for post_type in keys_to_remove:
            config.post_type.pop(post_type)

        # add post_types for which folder exists but is not included in config"
        for d in config.docs_dir.glob('*'):
            if d.is_dir():
                post_type = d.parts[-1]
                if post_type not in config.post_type.keys():
                    config.post_type.update({post_type: {}})

        # update archive type, slug, and with front
        has_home_template = False
        for theme_dir in self.themes.dirs:
            target_file = Path(theme_dir) / 'home.html'
            if target_file.exists():
                has_home_template = True
                break

        for post_type_name, post_type_config in config.post_type.items():

            index = list(config.post_type).index(post_type_name)
            archive_type = post_type_config.archive_type

            if not has_home_template and index == 0:
                post_type_config.with_front = False
                if archive_type == 'none':
                    archive_type = 'section'

            post_type_config.archive_type = archive_type

            slug = post_type_config.slug or post_type_name
            post_type_config.slug = to_slug(slug)

        return config

    def setup(self):
        self.singles.setup()

    def update(self):
        self.config.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.themes.dirs)
            )

        self.config.env.globals['config'] = self.config
        self.config.env.globals['singles'] = self.singles
        self.config.env.globals['archives'] = self.archives
        self.config.env.globals['theme'] = self.themes.cnf

        self.config = self.plugins.do_action(
            'after_setup_env', target=self.config)

        if self.config['mode'] != 'draft':
            self.archives.setup(self.singles)
            self.singles.update_urls()
            self.archives.update_urls()

        self.plugins.do_action('after_update_urls', target=self)

        self.singles.update_htmls(self.archives, self.themes)
        if self.config['mode'] != 'draft':
            self.archives.update_htmls(self.singles, self.themes)

        self.plugins.do_action('after_update_site', target=self)

    def output(self):
        self.copy_static_files()
        self.singles.output()
        self.plugins.do_action('after_output_singles', target=self)

        if self.config['mode'] != 'draft':
            self.archives.output()
            self.plugins.do_action(
                'after_output_archives', target=self)

            self.output_extra_pages()

        self.plugins.do_action('after_output_site', target=self)

        if self.config.cache_dir.exists():
            with open(self.config['cache_contents_path'], mode='w') as f:
                cache_contents = {
                    str(page.src_path): page.content for page in self.singles
                    }
                json.dump(cache_contents, f)

            with open(self.config['cache_htmls_path'], mode='w') as f:
                cache_htmls = {
                    str(page.src_path): page.html for page in self.singles
                    }
                json.dump(cache_htmls, f)

        self.plugins.do_action('on_end', target=self)

    def copy_static_files(self):

        for f in self.config.static_dir.glob('**/*'):
            if f.is_file():
                rel_path = f.relative_to(self.config.static_dir)
                to_path = self.config.public_dir / rel_path
                if to_path.exists() and f.stat().st_mtime < to_path.stat().st_mtime:
                    continue

                to_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(str(f), str(to_path))

        for d in self.themes.dirs:
            for f in d.glob('**/*'):
                if not f.is_file():
                    continue

                rel_path = f.relative_to(d.parent)
                if not self.is_target(rel_path):
                    continue

                to_path = self.config.public_dir / 'themes' / rel_path
                if to_path.exists() and f.stat().st_mtime < to_path.stat().st_mtime:
                    continue

                to_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(str(f), str(to_path))

    def is_target(self, rel_path):
        config = self.themes.cnf
        exclude = get_config_by_list(config, ['static_exclude']) or []
        for item in exclude:
            if fnmatch.fnmatch(rel_path, item):
                return False

        include = get_config_by_list(config, ['static_include']) or []
        for item in include:
            if fnmatch.fnmatch(rel_path, item):
                return True
        return False

    def output_extra_pages(self):
        config = self.themes.cnf
        extra_pages = get_config_by_list(config, ['extra_pages']) or []
        config_extra_pages = extra_pages[:]

        default_extra_pages = [
            'home.html', '404.html', 'sitemap.html', 'sitemap.xml'
            ]

        for default_extra_page in default_extra_pages:
            if default_extra_page not in extra_pages:
                extra_pages.append(default_extra_page)

        for extra_page in extra_pages:
            exist_check = False
            for theme_dir in self.themes.dirs:
                if Path(theme_dir, extra_page).exists():
                    self.output_extra_page(extra_page)
                    exist_check = True
                    continue

            if extra_page in config_extra_pages and not exist_check:
                print(extra_page + ' is not found on extra pages')

    def output_extra_page(self, extra_page):
        template = self.config.env.get_template(extra_page)

        html = template.render()

        if extra_page == 'home.html':
            output_path = self.config.public_dir / 'index.html'
        else:
            output_path = Path(self.config.public_dir, extra_page)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='UTF-8') as f:
            f.write(html)
