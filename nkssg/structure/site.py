from pathlib import Path
import shutil

import jinja2

from nkssg.structure.archives import Archives
from nkssg.structure.singles import Singles
from nkssg.structure.themes import Themes
from nkssg.utils import get_config_by_list


class Site:
    def __init__(self, config):
        self.config = config

        self.config['themes'] = Themes(self.config)
        self.config = self.config['plugins'].do_action('after_load_theme', target=self.config)

        self.config = self.setup_post_types()
        self.config = self.config['plugins'].do_action('after_setup_post_types', target=self.config)


        self.singles = Singles(self.config)
        self.archives = Archives(self.config)


    def setup_post_types(self):
        config = self.config

        # update post type list
        config['post_type_list'] = []
        for temp_item in config['post_type']:
            temp_dict = {}
            if type(temp_item) is dict:
                temp_dict = temp_item
            else:
                temp_dict[temp_item] = temp_item
            
            for post_type in temp_dict.keys():
                if Path(config['docs_dir'], post_type).exists():
                    config['post_type_list'].append(post_type)
        
        for d in config['docs_dir'].glob('*'):
            if d.is_dir():
                post_type = d.parts[-1]
                if not post_type in config['post_type_list']:
                    config['post_type_list'].append(post_type)

        # update archive type, and with front
        has_home_template = False
        for theme_dir in config['themes'].dirs:
            target_file = Path(theme_dir) / 'home.html'
            if target_file.exists():
                has_home_template = True
                break

        config_post_type = []
        for index, post_type in enumerate(config['post_type_list']):
            post_type_dict = get_config_by_list(config, ['post_type', post_type]) or {}

            archive_type = post_type_dict.get('archive_type')
            if archive_type is None:
                if post_type == 'post':
                    archive_type = 'date'
                else:
                    archive_type = 'section'
            
            archive_type = archive_type.lower()
            if archive_type != 'date' and archive_type != 'none':
                archive_type = 'section'

            post_type_dict['archive_type'] = archive_type

            if not has_home_template and index == 0:
                post_type_dict['with_front'] = False
            elif index > 0:
                post_type_dict['with_front'] = True
            
            config_post_type.append({post_type: post_type_dict})

        config['post_type'] = config_post_type

        return config



    def setup(self):
        self.singles.setup()


    def update(self):
        self.config['env'] = jinja2.Environment(loader=jinja2.FileSystemLoader( self.config['themes'].dirs ))
        self.config = self.config['plugins'].do_action('after_setup_env', target=self.config)

        if self.config['mode'] != 'draft':
            self.archives.setup(self.singles)

        self.singles.update(self.archives)

        if self.config['mode'] != 'draft':
            self.archives.update(self.singles)

        self.config['plugins'].do_action('after_update_site', target=self)


    def output(self):
        self.copy_static_files()
        self.singles.output()
        self.config['plugins'].do_action('after_output_singles', target=self)

        if self.config['mode'] != 'draft':
            self.archives.output()
            self.config['plugins'].do_action('after_output_archives', target=self)

            self.output_extra_pages()

        self.config['plugins'].do_action('after_output_site', target=self)
        self.config['plugins'].do_action('on_end', target=self)


    def copy_static_files(self):
        static_dir = Path.cwd() / 'static'
        public_dir = self.config['public_dir']

        for f in static_dir.glob('**/*'):
            if f.is_file():
                rel_path = f.relative_to(static_dir)
                to_path = public_dir / rel_path
                to_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(str(f), str(to_path))
        
        for d in self.config['themes'].dirs:
            for f in d.glob('**/*'):
                if f.is_file() and f.suffix[1:] in ['css', 'js', 'gif']:
                    rel_path = f.relative_to(d.parent)
                    to_path = public_dir / 'themes' / rel_path
                    to_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(str(f), str(to_path))



    def output_extra_pages(self):
        extra_pages = get_config_by_list(self.config, ['extra_pages']) or []
        config_extra_pages = extra_pages[:]
        default_extra_pages = ['home.html', '404.html', 'sitemap.html', 'sitemap.xml']

        for default_extra_page in default_extra_pages:
            if not default_extra_page in extra_pages:
                extra_pages.append(default_extra_page)

        for extra_page in extra_pages:
            exist_check = False
            for theme_dir in self.config['themes'].dirs:
                if Path(theme_dir, extra_page).exists():
                    self.output_extra_page(extra_page)
                    exist_check = True
                    continue

            if extra_page in config_extra_pages and not exist_check:
                print(extra_page + ' is not found on extra pages')



    def output_extra_page(self, extra_page):
        parts = Path(extra_page).parts
        template = self.config['env'].get_template('/'.join(parts))

        html = template.render({
            'config': self.config,
            'single_pages': self.singles.pages,
            'archives': self.archives,
            })

        if parts[0] == 'home.html' and len(parts) == 1:
            output_path = self.config['public_dir'] / 'index.html'
        else:
            output_path = Path(self.config['public_dir'], *parts)

        with open(output_path, 'w', encoding='UTF-8') as f:
            f.write(html)
