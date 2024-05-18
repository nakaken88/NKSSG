import datetime
from fnmatch import fnmatch
import markdown
from pathlib import Path, PurePath
import re
from urllib.parse import quote

from ruamel.yaml import YAML, YAMLError

from nkssg.config import Config
from nkssg.structure.plugins import Plugins
from nkssg.structure.pages import Pages, Page
from nkssg.structure.themes import Themes


class Singles(Pages):
    def __init__(self, config: Config, plugins: Plugins):
        self.config = config
        self.plugins = plugins
        self.pages = self.get_pages_from_docs_directory()
        self.file_ids = {}
        self.dest_paths = {}
        self.plugins.do_action(
            'after_initialize_singles', target=self)

    def get_pages_from_docs_directory(self):
        if self.config['mode'] == 'draft':
            return self._handle_draft_mode()

        return self._handle_normal_mode()

    def _handle_draft_mode(self):
        draft_path = self.config['draft_path']
        return [Single(draft_path, self.config)]

    def _handle_normal_mode(self):
        return [
            Single(f, self.config)
            for post_type in self.config.post_type
            for f in sorted((self.config.docs_dir / post_type).glob('**/*'))
            if self._is_valid_file(f)
        ]

    def _is_valid_file(self, f: Path):
        docs_dir = self.config.docs_dir
        ext = f.suffix[1:]
        is_file = f.is_file()
        has_valid_extension = ext in self.config.doc_ext
        not_excluded = not self.is_exclude(f.relative_to(docs_dir))
        return is_file and has_valid_extension and not_excluded

    def is_exclude(self, target):
        return any(fnmatch(target, item) for item in self.config.exclude)

    def setup(self):
        if self.config['mode'] == 'draft':
            self._setup_draft_mode()
            self.plugins.do_action('after_setup_draft_singles', target=self)
            return

        self._setup_normal_mode()
        self.plugins.do_action('after_setup_singles', target=self)

        self.pages.sort()
        self.plugins.do_action('after_sort_singles', target=self)

        self._setup_prev_next_page()
        self._setup_file_ids()

    def _setup_draft_mode(self):
        page = self.pages[0]
        new_page = page.setup(self.config, self.plugins)
        new_page.url = '/'
        new_page.dest_path = 'index.html'
        new_page.dest_dir = ''
        self.pages = [new_page]

    def _setup_normal_mode(self):
        new_pages = []
        for page in self.pages:
            new_page = page.setup(self.config, self.plugins)
            if self.config.get('serve_all') or not new_page.is_draft:
                new_pages.append(new_page)
        self.pages = new_pages

    def _setup_prev_next_page(self):
        bookended = [None] + self.pages + [None]
        zipped = zip(bookended[:-2], bookended[1:-1], bookended[2:])
        for page0, page1, page2 in zipped:
            page1.prev_page, page1.next_page = page0, page2

    def _setup_file_ids(self):
        for page in self.pages:
            page_id = str(page.file_id)
            if page_id in self.file_ids:
                raise ValueError(
                    f"Duplicate file ID detected: '{page_id}' "
                    f"for pages {page} and {self.file_ids[page_id]}")
            else:
                self.file_ids[page_id] = page

    def update_urls(self):
        for page in self.pages:
            page.update_url(self.config)

        self.plugins.do_action(
            'after_update_singles_url', target=self)

        self.setup_dest_path()

    def update_htmls(self, archives, themes: Themes):
        self.plugins.do_action(
            'before_update_singles_html', target=self)

        for page in self.pages:
            try:
                page.update_html(self, archives, themes)
            except Exception:
                print(page)
                raise

        self.plugins.do_action(
            'after_update_singles_html', target=self)

    def setup_dest_path(self):
        for page in self.pages:
            dest_path = str(page.dest_path)
            if dest_path in self.dest_paths:
                error_message = f"Duplicate Dest Path: {dest_path}.\n"
                error_message += f"Page: {page} \n"
                error_message += f"Page: {self.dest_paths[dest_path]}"
                raise ValueError(error_message)
            else:
                self.dest_paths[dest_path] = page

    def get_single_by_file_id(self, file_id):
        single = self.file_ids.get(file_id)
        if single is None:
            print('file_id:' + file_id + ' is not found.')
        return single


class Single(Page):

    def __init__(self, abs_src_path: Path, config: Config):
        super().__init__()

        docs_dir = config.docs_dir

        if docs_dir not in abs_src_path.parents:
            raise ValueError(
                f"The path '{abs_src_path}' must be a descendant "
                "of the docs dir '{docs_dir}'.")

        self.abs_src_path = abs_src_path
        self.src_path = abs_src_path.relative_to(docs_dir)
        self.src_dir = self.src_path.parent

        self.id: PurePath = PurePath('/docs', self.src_path)
        self.post_type = self.id.parts[2]
        self.page_type = 'single'

        self.filename = self.src_path.stem
        self.ext = self.src_path.suffix[1:]

        self.date = self._get_created_date()
        self.modified = self._get_modified_date()

        self.post_type_index = list(config.post_type).index(self.post_type)
        self.archive_type = config.post_type[self.post_type]

    def __str__(self):
        return f"Single(src='{self.id}')"

    def __lt__(self, other):
        if self.post_type != other.post_type:
            return self.post_type_index < other.post_type_index

        s_order = self.meta.get('order', 0)
        o_order = other.meta.get('order', 0)

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

    def setup(self, config: Config, plugins: Plugins):

        self.meta, doc = self.parse_front_matter(self.abs_src_path)

        post_type_config = config.post_type[self.post_type]

        self.date, self.modified = self._get_date()
        self.status = self._get_status()
        self.is_expired = self._is_expired(config.now)
        self.is_future = self._is_future(config.now)
        self.is_draft = self._is_draft()

        self.title = self._get_title()
        self.name = self._get_name()
        self.slug = self._get_slug(post_type_config.slug)

        self.content = self._get_content(doc, config, plugins)
        self.summary = self._get_summary()
        self.image = self._get_image(config)

        self.file_id = self._get_file_id()

        return self

    @staticmethod
    def parse_front_matter(path):
        try:
            doc = Single.read_document(path)
            parts = doc.split('---')
            if len(parts) < 3 or parts[0].strip() != '':
                return {}, doc

            try:
                front_matter = YAML(typ='safe').load(parts[1]) or {}
            except YAMLError as e:
                raise ValueError(f"YAML parsing error in {path}: {str(e)}")

            doc = '---'.join(parts[2:])
            return front_matter, doc

        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {path}")
        except Exception as e:
            raise Exception(
                f"front matter parse error in {path}: {str(e)}")

    @staticmethod
    def read_document(path):
        try:
            with open(path, 'r', encoding='UTF-8') as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {path}")
        except Exception as e:
            raise Exception(
                f"An error occurred while reading {path}: {str(e)}")

    def _get_created_date(self):
        try:
            stat_info = self.abs_src_path.stat()
            created_time = getattr(stat_info, 'st_birthtime', None)
            if created_time is None:
                created_time = getattr(stat_info, 'st_ctime', 0)
        except Exception:
            created_time = 0
        return datetime.datetime.fromtimestamp(created_time)

    def _get_modified_date(self):
        try:
            stat_info = self.abs_src_path.stat()
            modified_time = getattr(stat_info, 'st_mtime', 0)
        except Exception:
            modified_time = 0
        return datetime.datetime.fromtimestamp(modified_time)

    def _get_date(self):
        try:
            cdate = datetime.datetime.strptime(self.filename, '%Y%m%d')
        except ValueError:
            cdate = self.date

        cdate = self.meta.get('date', cdate)
        cdate = self._get_clean_date(cdate)

        mdate = self.meta.get('modified', self.modified)
        mdate = self._get_clean_date(mdate)
        mdate = max(cdate, mdate)

        return cdate, mdate

    def _get_clean_date(self, dirty_date):

        if isinstance(dirty_date, datetime.datetime):  # yyyy-mm-dd HH:MM:SS
            return dirty_date

        epoch_datetime = datetime.datetime.fromtimestamp(0)
        if isinstance(dirty_date, datetime.date):  # yyyy-mm-dd
            return datetime.datetime.combine(dirty_date, epoch_datetime.time())

        if isinstance(dirty_date, str) and dirty_date.count(':') == 1:
            # yyyy-mm-dd HH:MM
            try:
                return datetime.datetime.strptime(dirty_date, '%Y-%m-%d %H:%M')
            except ValueError:
                print(f'{dirty_date} is not valid date value in {self.id}')
                return epoch_datetime

        return epoch_datetime

    def _get_status(self):
        return self.meta.get('status', 'publish')

    def _is_expired(self, now):
        expire = self.meta.get('expire')
        if expire is None:
            return False

        expire = self._get_clean_date(expire)
        return expire <= now

    def _is_future(self, now):
        return self.date > now

    def _is_draft(self):
        draft = self.meta.get('draft')
        if draft is not None:
            return draft

        status_list = ['auto-draft', 'draft', 'future', 'inherit',
                       'pending', 'private', 'trash']

        if self.post_type in status_list:
            return True

        if self.status in status_list:
            return True

        if self.is_expired or self.is_future:
            return True

        return False

    def _get_title(self):
        title = self.meta.get('title') or Page.clean_name(self.filename)
        if self.filename == 'index' and title == 'index':
            title = Page.clean_name(self.src_dir.parts[-1])
        return title

    def _get_name(self):
        return self.title

    def _get_slug(self, post_type_slug):
        slug = self.meta.get('slug')
        if slug is None:
            # set top index slug to post type slug instead of dir name
            if self.filename == 'index' and len(self.id.parts) == 3:
                slug = post_type_slug
            else:
                slug = self.name
        return Page.to_slug(slug)

    def _get_content(self, doc, config: Config, plugins: Plugins):
        if not doc:
            return ''

        content = doc
        self.content_updated = False
        content = plugins.do_action(
            'on_get_content', target=content, config=config, single=self)

        if self.content_updated:
            return content

        if self.ext in ['md', 'markdown']:
            md_config: dict = config.markdown

            return markdown.markdown(
                content,
                extensions=md_config.keys(),
                extension_configs=md_config)
        else:
            return content

    def _get_summary(self):
        summary = self.meta.get('summary', self.content)
        remove_patterns = [
            r'<script.*?script>', r'<style.*?style>',
            r'<[^>]*?>', r'{{[^}]*?}}', r'{#[^}]*?#}', r'{%[^}]*?%}'
        ]
        for pattern in remove_patterns:
            summary = re.sub(pattern, '', summary, flags=re.DOTALL)

        for word in ['/', '\\', '"', "'"]:
            summary = summary.replace(word, ' ')

        summary = summary.replace('\r\n', '').replace('\n', '')
        summary = summary[:110]
        return summary

    def _get_image(self, config: Config):
        image: dict = self.meta.get('image', {})
        src: str = image.get('src', '')

        if not image or not src:
            return {}

        if src.startswith('http'):
            return image

        image = self._process_image_src(image, src, config)
        image = self._set_image_url(image, src, config)

        return image

    def _process_image_src(self, image: dict, src: str, config: Config):

        if src.startswith('/'):
            image_path = config.base_dir / src.strip('/')
        else:
            image_path = self.abs_src_path.parent / src

        if image_path.exists():
            image['old_path'] = image_path
        else:
            image = {}
            print(f"Warning: Image path '{image_path}'"
                  f" for post '{self.id}' does not exist.")
        return image

    def _set_image_url(self, image: dict, src: str, config: Config):

        if src.startswith('/' + config.static_dir):
            image['rel_url'] = src[len('/' + config.static_dir):]
        else:
            year = str(self.date.year).zfill(4)
            month = str(self.date.month).zfill(2)

            image_name = image['old_path'].name
            thumb_path_parts = ['thumb', year, month, image_name]
            new_path = Path(config.public_dir, *thumb_path_parts)
            image['new_path'] = new_path

            image['rel_url'] = '/' + '/'.join(thumb_path_parts)

        image['abs_url'] = config.site.site_url + image['rel_url']
        if config.use_abs_url:
            image['url'] = image['abs_url']
        else:
            image['url'] = image['rel_url']
        image['src'] = image['url']
        return image

    def _get_file_id(self):
        return self.meta.get('file_id') or self.src_path

    def update_url(self, config):
        self.rel_url, self.dest_path = self._get_url_and_dest_path(config)
        self.dest_dir = self.dest_path.parent
        self._url_setup(config)

    def _get_url_and_dest_path(self, config: Config):

        url = self.meta.get('url')

        if url is None:
            post_type = self.post_type
            permalink = config.post_type[post_type].permalink

            if permalink is None:
                dest_path = self.src_dir / self.filename / 'index.html'
                if self.filename == 'index':
                    dest_path = self.src_dir / 'index.html'

                with_front = config.post_type[post_type].with_front

                if with_front:
                    slug = config.post_type[post_type].slug
                    dest_path = Path(str(dest_path).replace(post_type, slug, 1))
                else:
                    dest_path = dest_path.relative_to(Path(post_type))

                parts = dest_path.parts
                new_parts = []
                for part in parts:
                    new_parts.append(Page.to_slug(Page.clean_name(part)))
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

    def get_url_from_permalink(self, permalink, config: Config):
        permalink = '/' + permalink.strip('/') + '/'
        url = self.date.strftime(permalink)
        url = url.replace('{slug}', self.slug)

        if '{filename}' in url:
            filename = Page.clean_name(self.filename)
            if filename == 'index':
                part_list = list(self.src_dir.parts)
                if len(part_list) == 1:
                    filename = config.post_type[self.post_type].slug
                else:
                    filename = Page.clean_name(part_list[-1])

            filename = Page.to_slug(filename)
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
                    new_part.append('no-' + Page.to_slug(part))
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

    def update_html(self, singles: Singles, archives, themes: Themes):
        config = singles.config
        plugins = singles.plugins
        if not self.shouldUpdateHtml:
            return

        template_file = self.lookup_template(config, themes)
        template = config.env.get_template(template_file)

        if any(x in self.content for x in ['{{', '{#', '{%']):
            # add "import short code" statement
            additional_statement = ''
            import_sc = '{% import "import/short-code.html" as sc %}'
            import_scc = '{% import "import/short-code-child.html" as scc %}'

            for theme_dir in themes.dirs:
                template_path = theme_dir / 'import' / 'short-code.html'
                if template_path.exists():
                    additional_statement = additional_statement + import_sc

                template_path = theme_dir / 'import' / 'short-code-child.html'
                if template_path.exists():
                    additional_statement = additional_statement + import_scc

            content = additional_statement + self.content
            content = config.env.from_string(content).render({
                'mypage': self,
                'meta': self.meta,
                })

            self.content = content

        self.content = plugins.do_action(
            'before_render_html',
            target=self.content,
            config=config,
            single=self,
            singles=singles,
            archives=archives
            )

        self.html = template.render({
            'mypage': self,
            })

        self.html = plugins.do_action(
            'after_render_html',
            target=self.html,
            config=config,
            single=self,
            singles=singles,
            archives=archives
            )

    def lookup_template(self, config: Config, themes: Themes):

        def template_exists(template_name):
            for theme_dir in themes.dirs:
                template_path = theme_dir / template_name
                if template_path.exists():
                    return True
            return False

        template_file = self.meta.get('template')
        if template_file:
            template_file = template_file.replace('.html', '') + '.html'
            if template_exists(template_file):
                return template_file

        if config['mode'] == 'draft':
            template_file = 'draft.html'
            if template_exists(template_file):
                return template_file

        template_file = 'single-' + self.post_type + '.html'
        if template_exists(template_file):
            return template_file

        template_file = 'single.html'
        if template_exists(template_file):
            return template_file

        return 'main.html'
