import collections
import datetime
import fnmatch
import markdown
from pathlib import Path
import platform
import re
import shutil
from urllib.parse import quote, unquote

from bs4 import BeautifulSoup
import jinja2

from nkssg.structure.pages import Pages, Page
from nkssg.utils import *


class Singles(Pages):
    def __init__(self, config):
        self.config = config
        self.pages = self.get_pages_from_docs_directory()
        self.config['plugins'].do_action('after_initialize_singles', target=self)

    def get_pages_from_docs_directory(self):
        config = self.config
        docs_dir = config['docs_dir']

        if config['mode'] == 'draft':
            src_path = config['draft_path'].relative_to(docs_dir)
            return [Single(src_path, docs_dir)]

        pages = []

        for post_type in config['post_type_list']:
            target_dir = docs_dir / post_type
            files = [f for f in target_dir.glob('**/*') if f.is_file()]

            for f in sorted(files):
                ext = f.suffix[1:]
                if not ext in config['doc_ext']:
                    continue

                relative_path = f.relative_to(docs_dir)
                if self.is_exclude(relative_path):
                    continue

                pages.append(Single(relative_path, docs_dir, len(pages) + 1))

        return pages

    def is_exclude(self, target):
        for item in self.config['exclude']:
            if fnmatch.fnmatch(target, item):
                return True
        return False



    def setup(self):
        config = self.config

        if config['mode'] == 'draft':
            page = self.pages[0]
            new_page = page.setup(config)
            new_page.url = '/'
            new_page.dest_path = 'index.html'
            new_page.dest_dir = ''
            self.pages = [new_page]
            self.config['plugins'].do_action('after_setup_draft_singles', target=self)
            return

        new_pages = []
        for page in self.pages:
            new_page = page.setup(config)

            if new_page.is_draft or new_page.is_expired:
                continue

            new_pages.append(new_page)
        
        self.config['plugins'].do_action('after_setup_singles', target=self)

        self.pages = sorted(new_pages)
        self.config['plugins'].do_action('after_sort_singles', target=self)

        self.src_paths = {str(page.src_path): page for page in self.pages}

        bookended = [None] + self.pages + [None]
        zipped = zip(bookended[:-2], bookended[1:-1], bookended[2:])
        for page0, page1, page2 in zipped:
            page1.prev_page, page1.next_page = page0, page2



    def update_urls(self):
        for page in self.pages:
            page.update_url(self.config)

        self.config['plugins'].do_action('after_update_singles_url', target=self)
        self.dest_path_dup_check()

    def update_htmls(self, archives):
        for page in self.pages:
            page.update_html(self, archives)

        self.config['plugins'].do_action('after_update_singles_html', target=self)


    def dest_path_dup_check(self):
        dest_path_list = [(str(page.dest_path), page) for page in self.pages]
        dup_check(dest_path_list)
        self.dest_paths = {str(page.dest_path): page for page in self.pages}




class Single(Page):

    def __init__(self, src_path, docs_dir, id=0):
        super().__init__()

        self._id = id

        self.src_path = Path(src_path)
        self.abs_src_path = docs_dir / self.src_path
        self.src_dir = self.src_path.parent

        self.filename = self.src_path.stem
        self.ext = self.src_path.suffix[1:]

        self.date = ''
        self.modified = ''

        self.page_type = 'single'

        self.post_type = ''
        self.status = ''
        self.is_draft = False
        self.is_expired = False


    def __repr__(self):
        return "File(src='{}')".format(self.src_path)

    def __lt__(self, other):
        if self.post_type != other.post_type:
            return self.post_type_index < other.post_type_index

        s_order = 0 if self.meta.get('order') is None else self.meta.get('order')
        o_order = 0 if other.meta.get('order') is None else other.meta.get('order')

        if s_order < 0 or o_order < 0:
            return (s_order, self.src_path) < (o_order, other.src_path)


        if self.archive_type == 'date':
            if self.date != other.date:
                return self.date > other.date
            return self.src_path < other.src_path

        if self.src_dir != other.src_dir:
            return self.src_dir < other.src_dir

        if self.filename == 'index' or other.filename == 'index':
            return self.filename == 'index'

        return (s_order, self.src_path) < (o_order, other.src_path)


    def setup(self, config):
        with open(self.abs_src_path, 'r', encoding='UTF-8') as f:
            doc = f.read()

        try:
            self.meta, doc = front_matter_setup(doc)
        except:
            raise Exception('front matter error: ' + str(self.abs_src_path))

        self.post_type = self._get_post_type()
        self.post_type_slug = get_config_by_list(config, ['post_type', self.post_type, 'slug'])
        self.post_type_index = config['post_type_list'].index(self.post_type)

        self.status = self._get_status()
        self.is_draft = self._is_draft()
        self.is_expired = self._is_expired()

        self.date, self.modified = self._get_date()
        self.title = self._get_title()
        self.name = self._get_name()
        self.slug = self._get_slug()

        self.content = self._get_content(config, doc)
        self.summary = self._get_summary()

        self.image = self._get_image(config)

        self.file_id = self._get_file_id()
        self.archive_type = self._get_archive_type(config)

        return self


    def _get_post_type(self):
        return self.src_path.parts[0]


    def _get_status(self):
        status = self.meta.get('status') or 'publish'
        return status


    def _is_draft(self):
        draft = self.meta.get('draft')
        if not draft is None:
            return draft

        private_status_list = ['draft', 'future', 'pending', 'private', 'trash', 'auto-draft']

        if self.post_type in private_status_list:
            return True

        if self.status in private_status_list:
            return True

        return False


    def _is_expired(self):
        expire = self.meta.get('expire')
        if expire is None:
            return False

        now = datetime.datetime.now()

        if type(expire) != type(now):
            expire = datetime.datetime.combine(expire, datetime.time(0, 0, 0))

        return expire <= now


    def _get_date(self):
        cdate = self.meta.get('date')
        now = datetime.datetime.now()
        
        if cdate is None:
            try:
                cdate = datetime.datetime.strptime(self.filename, '%Y%m%d')
                cdate = datetime.datetime.combine(cdate, datetime.time(0, 0, 0))
            except ValueError:
                cdate_unix = self._creation_date(self.abs_src_path)
                cdate = datetime.datetime.fromtimestamp(cdate_unix)

        elif type(cdate) != type(now):
            cdate = datetime.datetime.combine(cdate, datetime.time(0, 0, 0))

        mtime_unix = self.abs_src_path.stat().st_mtime
        mdate = datetime.datetime.fromtimestamp(mtime_unix)

        return cdate, mdate

    def _creation_date(self, path_to_file):
        if platform.system() == 'Windows':
            return self.abs_src_path.stat().st_ctime
        else:
            try:
                return self.abs_src_path.stat().st_birthtime
            except AttributeError:
                return 0


    def _get_title(self):
        title = self.meta.get('title') or clean_name(self.filename)
        if self.filename == 'index' and title == 'index':
            title = clean_name(self.src_dir.parts[-1])
        return title

    def _get_name(self):
        return self.title[:80]

    def _get_slug(self):
        slug = self.meta.get('slug') or self.name
        return to_slug(slug)



    def _get_content(self, config, doc):
        if not doc:
            return ''

        content = config['plugins'].do_action('on_get_content', target=doc, config=config, single=self)
        if content and content != doc:
            return content

        ext = self.ext
        if ext == 'md' or ext == 'markdown':
            md_config = get_config_by_list(config, 'markdown')
            if md_config is None:
                return markdown.markdown(doc)
            else:
                extensions = []
                ext_configs = {}
                for item in md_config:
                    if type(item) == dict:
                        for k in item:
                            extensions.append(k)
                            ext_configs[k] = item[k]
                            break
                    else:
                        extensions.append(item)
                return markdown.markdown(doc, extensions=extensions, extension_configs=ext_configs)
        else:
            return doc

    def _get_summary(self):
        summary = self.meta.get('summary')
        if summary is None:
            soup = BeautifulSoup(self.content, 'html.parser')
            summary = soup.get_text()
            summary = summary[:200]
            summary = summary.replace('/', ' ').replace('\\', ' ')
            summary = summary.replace('"', ' ').replace("'", ' ')
            summary = summary.replace('\n', '')
            summary = summary[:110]
        return summary


    def _get_image(self, config):
        image = self.meta.get('image') or {}
        if image:
            src = image.get('src') or ''
            if src:
                if 'http' == src[:len('http')]:
                    return image
                elif '/' == src[:len('/')]:
                    image_path = config['base_dir'] / src.strip('/')
                else:
                    image_path = self.abs_src_path.parent / src

                if image_path.exists():
                    image['old_path'] = image_path
                else:
                    image = {}
        if not image:
            return image


        if '/static' == src[:len('/static')]:
            image['rel_url'] = src[len('/static'):]
        else:
            cdate = self.date
            year = str(cdate.year).zfill(4)
            month = str(cdate.month).zfill(2)

            image_name = image_path.name
            new_path = Path(config['public_dir'], 'thumb', year, month, image_name)
            image['new_path'] = new_path

            image['rel_url'] = '/' + '/'.join(['thumb', year, month, image_name])


        image['abs_url'] = config['site']['site_url'] + image['rel_url']
        if config['use_abs_url']:
            image['url'] = image['abs_url']
        else:
            image['url'] = image['rel_url']
        image['src'] = image['url']
        return image


    def _get_file_id(self):
        return self.meta.get('file_id') or self.src_path

    def _get_archive_type(self, config):
        return  get_config_by_list(config, ['post_type', self.post_type, 'archive_type'])



    def update_url(self, config):
        self.rel_url, self.dest_path = self._get_url_and_dest_path(config)
        self.dest_dir = self.dest_path.parent
        self._url_setup(config)


    def _get_url_and_dest_path(self, config):

        url = self.meta.get('url')
        
        if url is None:
            post_type = self.post_type
            permalink = get_config_by_list(config, ['post_type', post_type, 'permalink'])

            if permalink is None:
                dest_path = self.src_dir / self.filename / 'index.html'
                if self.filename == 'index':
                    dest_path = self.src_dir / 'index.html'

                with_front = get_config_by_list(config, ['post_type', post_type, 'with_front'])

                if with_front:
                    slug = get_config_by_list(config, ['post_type', post_type, 'slug'])
                    dest_path = Path(str(dest_path).replace(post_type, slug, 1))
                else:
                    dest_path = dest_path.relative_to(Path(post_type))
                
                parts = dest_path.parts
                new_parts = []
                for part in parts:
                    new_parts.append(to_slug(clean_name(part)))
                dest_path = Path(*new_parts)

                url = self._get_url_from_dest(dest_path)

            else:
                url = self.get_url_from_permalink(permalink, config)
                dest_path = self._get_dest_from_url(url)

        else:
            dest_path = self._get_dest_from_url(url)

        url = '/' + url.strip('/') + '/'
        url = url.replace('//', '/')

        return url.lower(), dest_path


    def get_url_from_permalink(self, permalink, config):
        permalink = '/' + permalink.strip('/') + '/'
        url = self.date.strftime(permalink)
        url = url.replace('{slug}', self.slug)

        if '{filename}' in url:
            filename = clean_name(self.filename)
            if filename == 'index':
                part_list = list(self.src_dir.parts)
                if len(part_list) == 1:
                    filename = get_config_by_list(config, ['post_type', self.post_type, 'slug'])
                else:
                    filename = clean_name(part_list[-1])

            filename = to_slug(filename)
            url = url.replace('{filename}', filename)

        if '{' in url:
            parts = re.findall(r'\{.*?\}', url)
            for part in parts:
                original_part = part
                part = part[1:-1]

                part_type = 'all'
                if '_top' in part:
                    part_type = 'top'
                    part = part[:-(len('_top'))]
                elif '_last' in part:
                    part_type = 'last'
                    part = part[:-(len('_last'))]

                new_part = []
                target_archive = None
                for archive in self.archive_list:
                    if archive.root_name == part and not archive.is_root:
                        target_archive = archive
                        break
                
                if target_archive is None:
                    new_part.append('no-' + to_slug(part))
                else:
                    target_archives = [p for p in target_archive.parents if not p.is_root]
                    target_archives = target_archives + [target_archive]

                    if part_type == 'all':
                        new_part = [p.slug for p in target_archives]
                    elif part_type == 'top':
                        new_part = [target_archives[0].slug]
                    elif part_type == 'last':
                        new_part = [target_archives[-1].slug]

                url = url.replace(original_part, '/'.join(new_part))

        return quote(url).lower()


    def update_html(self, singles, archives):
        config = singles.config
        template_file = self.lookup_template(config)
        template = config['env'].get_template(template_file)

        if '{{' in self.content:
            self.content = config['env'].from_string(self.content).render({
                'config': config,
                'mypage': self,
                'meta': self.meta,
                'singles': singles,
                'archives': archives,
                'theme': config['themes'].cnf,
                })

        self.html = template.render({
            'config': config,
            'mypage': self,
            'singles': singles,
            'archives': archives,
            'theme': config['themes'].cnf,
            })



    def lookup_template(self, config):
        template_file = self.meta.get('template')

        for theme_dir in config['themes'].dirs:
            if not template_file is None:
                template_file = template_file.replace('.html', '') + '.html'
                template_path = theme_dir / template_file
                if template_path.exists():
                    return template_file

            if config['mode'] == 'draft':
                template_file = 'draft.html'
                template_path = theme_dir / template_file
                if template_path.exists():
                    return template_file

            template_file = 'single-' + self.post_type + '.html'
            template_path = theme_dir / template_file
            if template_path.exists():
                return template_file

            template_file = 'single.html'
            template_path = theme_dir / template_file
            if template_path.exists():
                return template_file

        return 'main.html'
