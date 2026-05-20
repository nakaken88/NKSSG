from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime
import html
from html.parser import HTMLParser
import logging
from fnmatch import fnmatch
import markdown
from pathlib import Path, PurePath
import re
from urllib.parse import quote

from ruamel.yaml import YAML, YAMLError

from typing import TYPE_CHECKING

from nkssg.structure.config import Config
from nkssg.structure.plugins import Plugins
from nkssg.structure.pages import Page
from nkssg.structure.themes import Themes

if TYPE_CHECKING:
    from nkssg.structure.archives import Archives

_EPOCH = datetime.datetime(1970, 1, 1)


class Singles:
    def __init__(self, config: Config, plugins: Plugins):
        self.config = config
        self.plugins = plugins
        self.pages: list[Single] = []
        self.file_ids: dict[str, Single] = {}
        self.src_paths: dict[str, Single] = {}
        self.dest_paths: dict[str, Single] = {}

    def __iter__(self):
        return iter(self.pages)

    def setup(self):
        self.pages = self.get_pages_from_docs_directory()
        self.plugins.do_action('after_initialize_singles', target=self)

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
        self._setup_src_paths()

    def get_pages_from_docs_directory(self) -> list['Single']:
        if self.config['mode'] == 'draft':
            return [Single(self.config['draft_path'], self.config)]

        return [
            Single(f, self.config)
            for post_type in self.config.post_type
            for f in sorted((self.config.docs_dir / post_type).glob('**/*'))
            if self._is_valid_file(f)
        ]

    def _is_valid_file(self, f: Path) -> bool:
        ext = f.suffix[1:]
        has_valid_ext = ext in self.config.doc_ext
        rel = f.relative_to(self.config.docs_dir)
        is_excluded = any(fnmatch(rel, item) for item in self.config.exclude)
        return f.is_file() and has_valid_ext and not is_excluded

    def _setup_draft_mode(self):
        self.pages[0].setup(self.config, self.plugins)

    def _setup_normal_mode(self):
        new_pages = []
        for page in self.pages:
            page.setup(self.config, self.plugins)
            if self.config.get('serve_all') or not page.is_draft:
                new_pages.append(page)
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

    def _setup_src_paths(self):
        self.src_paths = {
            page.src_path.as_posix(): page for page in self.pages
        }

    def update_urls(self):
        for page in self.pages:
            page.update_url(self.config)

        self.plugins.do_action('after_update_singles_url', target=self)

        self._setup_dest_path()

    def _setup_dest_path(self):
        for page in self.pages:
            dest_path = str(page.dest_path)
            if dest_path in self.dest_paths:
                error_message = f"Duplicate Dest Path: {dest_path}.\n"
                error_message += f"Page: {page} \n"
                error_message += f"Page: {self.dest_paths[dest_path]}"
                raise ValueError(error_message)
            else:
                self.dest_paths[dest_path] = page

    def update_htmls(self, archives: 'Archives', themes: Themes) -> None:
        self.plugins.do_action('before_update_singles_html', target=self)

        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(page.update_html, self, archives, themes)
                for page in self.pages
            ]
            for future in as_completed(futures):
                future.result()

        self.plugins.do_action('after_update_singles_html', target=self)

    def output(self):
        for page in self.pages:
            page.output(self.config)

    def get_single_by_file_id(self, file_id):
        single = self.file_ids.get(file_id)
        if single is None:
            logging.warning(f'file_id: {file_id} is not found.')
        return single


class Single(Page):

    def __init__(self, abs_src_path: Path, config: Config):
        super().__init__()

        docs_dir = config.docs_dir
        if not docs_dir:
            raise ValueError("docs_dir must not be empty.")
        if docs_dir not in abs_src_path.parents:
            raise ValueError(
                f"The path '{abs_src_path}' must be a descendant "
                f"of the docs dir '{docs_dir}'.")

        self.abs_src_path = abs_src_path
        self.src_path = abs_src_path.relative_to(docs_dir)
        self.id = PurePath('/docs', self.src_path)
        self.post_type = self.id.parts[2]
        self.src_dir = self.src_path.parent
        self.filename = self.src_path.stem
        self.ext = self.src_path.suffix[1:]

        self.page_type = 'single'
        self.content_updated = False
        self.date, self.modified = self._get_file_dates()

        self.post_type_index = list(config.post_type).index(self.post_type)
        self.archive_type = config.post_type[self.post_type].archive_type

    def __str__(self) -> str:
        return f"Single(src='{self.id}')"

    def __lt__(self, other: 'Single') -> bool:
        if self.post_type != other.post_type:
            return self.post_type_index < other.post_type_index

        s_order = self.meta.get('order', 0)
        o_order = other.meta.get('order', 0)

        # negative order pins items at the top regardless of directory or date
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

    def setup(self, config: Config, plugins: Plugins) -> None:

        self.meta, doc = self.parse_front_matter(self.abs_src_path)

        self.date, self.modified = self._get_date()
        self.status = self.meta.get('status', 'publish')
        self.is_expired = self._is_expired(config.now)
        self.is_future = self._is_future(config.now)
        self.is_draft = self._is_draft(config.now)

        self.title = self._get_title()
        self.name = self.title

        post_type_slug = config.post_type[self.post_type].slug or self.post_type
        self.slug = self._get_slug(post_type_slug)

        self.content = self._get_content(doc, config, plugins)
        self.image = self._get_image(config)

        self.file_id = self._get_file_id()

    @property
    def is_root(self) -> bool:
        # /docs/{post_type}/index.md
        return len(self.id.parts) == 4 and self.filename.lower() == 'index'

    @staticmethod
    def parse_front_matter(path: Path) -> tuple[dict, str]:
        try:
            doc = path.read_text(encoding='utf-8')
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {path}")
        except Exception as e:
            raise Exception(f"Failed to read file '{path}': {str(e)}")

        parts = doc.split('---')
        if len(parts) < 3 or parts[0].strip() != '':
            return {}, doc

        try:
            front_matter = YAML(typ='safe').load(parts[1]) or {}
        except YAMLError as e:
            raise ValueError(f"YAML parsing error in {path}: {str(e)}")

        doc = '---'.join(parts[2:])
        return front_matter, doc

    def _get_file_dates(self) -> tuple[datetime.datetime, datetime.datetime]:
        try:
            stat = self.abs_src_path.stat()
            created = getattr(stat, 'st_birthtime', stat.st_mtime)
            return (
                datetime.datetime.fromtimestamp(created),
                datetime.datetime.fromtimestamp(stat.st_mtime),
            )
        except Exception:
            return _EPOCH, _EPOCH

    def _get_date(self) -> tuple[datetime.datetime, datetime.datetime]:
        try:
            cdate = datetime.datetime.strptime(self.filename.replace('-', '')[:8], '%Y%m%d')
        except ValueError:
            cdate = self.date

        cdate = self.meta.get('date', cdate)
        cdate = self._get_clean_date(cdate)

        mdate = self.meta.get('modified', self.modified)
        mdate = self._get_clean_date(mdate)
        mdate = max(cdate, mdate)

        return cdate, mdate

    def _get_clean_date(self, dirty_date) -> datetime.datetime:

        if isinstance(dirty_date, datetime.datetime):  # yyyy-mm-dd HH:MM:SS
            return dirty_date

        if isinstance(dirty_date, datetime.date):  # yyyy-mm-dd
            return datetime.datetime.combine(dirty_date, datetime.time.min)

        if isinstance(dirty_date, str) and dirty_date.count(':') == 1:
            # yyyy-mm-dd HH:MM
            try:
                return datetime.datetime.strptime(dirty_date, '%Y-%m-%d %H:%M')
            except ValueError:
                logging.warning(f'{dirty_date} is not valid date value in {self.id}')

        return _EPOCH

    def _is_expired(self, now: datetime.datetime) -> bool:
        expire = self.meta.get('expire')
        if expire is None:
            return False

        expire = self._get_clean_date(expire)
        return expire <= now

    def _is_future(self, now: datetime.datetime) -> bool:
        return self.date > now

    def _is_draft(self, now: datetime.datetime) -> bool:
        draft = self.meta.get('draft')
        if draft is not None:
            return False if str(draft).lower() == 'false' else bool(draft)

        status_list = ['auto-draft', 'draft', 'future', 'inherit',
                       'pending', 'private', 'trash']

        res = self._is_expired(now) or self._is_future(now)
        res = res or (self.post_type in status_list)
        res = res or (self.status in status_list)
        return res

    def _get_title(self) -> str:
        title = self.meta.get('title') or Page.clean_name(self.filename)
        if self.filename.lower() == 'index' and title == 'index':
            title = Page.clean_name(self.src_dir.parts[-1])
        return title

    def _get_slug(self, post_type_slug: str) -> str:
        slug = self.meta.get('slug')
        if slug is None:
            # set top index slug to post type slug instead of dir name
            if self.is_root:
                slug = post_type_slug
            else:
                slug = self.name
        return Page.to_slug(slug)

    def _get_content(self, doc: str, config: Config, plugins: Plugins) -> str:
        if not doc:
            return ''

        content = plugins.do_action(
            'on_get_content', target=doc, config=config, single=self)

        if self.content_updated:
            return content

        if self.ext in ['md', 'markdown']:
            md_config: dict = config.markdown
            return markdown.markdown(
                content,
                extensions=md_config.keys(),
                extension_configs=md_config)

        return content

    class _SummaryTextExtractor(HTMLParser):
        _SKIP_TAGS = {'script', 'style'}

        def __init__(self):
            super().__init__(convert_charrefs=True)
            self._parts = []
            self._skip = False

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if tag in self._SKIP_TAGS:
                self._skip = True

        def handle_endtag(self, tag: str) -> None:
            if tag in self._SKIP_TAGS:
                self._skip = False

        def handle_data(self, data: str) -> None:
            if not self._skip:
                self._parts.append(data)

        def get_text(self) -> str:
            return ''.join(self._parts).replace('\r\n', '').replace('\n', '')

    def _get_summary(self) -> str:
        raw = self.meta.get('summary', self.content)
        parser = self._SummaryTextExtractor()
        parser.feed(raw)
        summary = parser.get_text()[:160]
        return html.escape(summary)

    def _get_image(self, config: Config) -> dict:
        image: dict = self.meta.get('image', {})
        src: str = image.get('src', '')

        if not image or not src:
            return {}

        if src.startswith('http'):
            return image

        image = self._process_image_src(image, src, config)
        if not image:
            return {}
        return self._set_image_url(image, src, config)

    def _process_image_src(self, image: dict, src: str, config: Config) -> dict:

        if src.startswith('/'):
            image_path = config.base_dir / src.strip('/')
        else:
            image_path = self.abs_src_path.parent / src

        if not image_path.exists():
            logging.warning(f"Image path '{image_path}' for post '{self.id}' does not exist.")
            return {}

        image['old_path'] = image_path
        return image

    def _set_image_url(self, image: dict, src: str, config: Config) -> dict:

        static_rel_path = config.static_dir.relative_to(config.base_dir).as_posix()
        if src.startswith(f'/{static_rel_path}/'):
            image['rel_url'] = src
        else:
            year = str(self.date.year).zfill(4)
            month = str(self.date.month).zfill(2)

            image_name = image['old_path'].name
            thumb_path_parts = ['thumb', year, month, image_name]
            image['new_path'] = Path(config.public_dir, *thumb_path_parts)
            image['rel_url'] = '/' + '/'.join(thumb_path_parts)

        use_abs_url = config.use_abs_url
        image['abs_url'] = config.site.site_url + image['rel_url']
        image['url'] = image['abs_url'] if use_abs_url else image['rel_url']
        image['src'] = image['url']
        return image

    def _get_file_id(self) -> str:
        return self.meta.get('file_id', str(self.src_path))

    def update_url(self, config: Config) -> None:
        self.rel_url = self._get_rel_url(config)
        self.dest_path = self._get_dest_from_url(self.rel_url)
        self.dest_dir = self.dest_path.parent
        self._url_setup(config)

    def _get_rel_url(self, config: Config) -> str:

        # convert to relative url
        url: str = self.meta.get('url', '')
        url = url.replace(config.site.site_url, '')
        url = url.replace(config.site.site_url_original, '')

        if not url:
            post_type_config = config.post_type[self.post_type]
            permalink = post_type_config.permalink

            if not permalink:
                raise ValueError(f"Permalink of '{self.post_type}' is not set.")

            post_type_slug = post_type_config.slug or self.post_type
            post_type_slug = Page.to_slug(post_type_slug)

            add_prefix_to_url = post_type_config.add_prefix_to_url

            url = self.get_url_from_permalink(
                            permalink, post_type_slug, add_prefix_to_url)

        return self._format_url(url)

    def get_url_from_permalink(
            self, permalink: str, post_type_slug: str, add_prefix_to_url: bool) -> str:
        permalink = '/' + permalink.strip('/') + '/'

        if add_prefix_to_url:
            permalink = '/' + post_type_slug + permalink

        url = self.date.strftime(permalink)

        if self.is_root:
            url = url.replace('/{slug}/', '/')
            url = url.replace('/{filename}/', '/')
        else:
            url = url.replace('{slug}', self.slug)
            filename_slug = self._get_filename_slug(post_type_slug)
            url = url.replace('{filename}', filename_slug)

        url = self._replace_dynamic_parts_in_url(url)
        return quote(url).lower()

    def _get_filename_slug(self, post_type_slug: str) -> str:
        if self.is_root:
            filename_slug = post_type_slug
        elif self.filename.lower() == 'index':
            filename_slug = self.src_dir.parts[-1]
        else:
            filename_slug = self.filename

        return Page.to_slug(Page.clean_name(filename_slug))

    def _replace_dynamic_parts_in_url(self, url: str) -> str:
        for original_part in re.findall(r'\{.*?\}', url):
            part = original_part[1:-1]

            part_type = 'all'
            for suffix in ['top', 'last', 'all']:
                if part.endswith('_' + suffix):
                    part_type = suffix
                    part = part[:-(len(suffix) + 1)]
                    break

            slugs = self._get_target_archive_slugs(part)
            if part_type == 'top':
                replacement = slugs[:1]
            elif part_type == 'last':
                replacement = slugs[-1:]
            else:
                replacement = slugs

            url = url.replace(original_part, '/'.join(replacement))
            url = url.replace('//', '/')

        # For a section archive index page (e.g. sports/index.md), {slug} and
        # the last archive segment both resolve to the parent directory name,
        # producing a duplicate (e.g. /sports/sports/). Drop the duplicate when
        # the last two segments are identical.
        url_parts = url.split('/')
        if self.filename.lower() == 'index' and len(url_parts) >= 3 and url_parts[-2] == url_parts[-3]:
            url = '/'.join(url_parts[:-2]) + '/'
        else:
            url = '/'.join(url_parts) + '/'
        return url.replace('//', '/')

    def _get_target_archive_slugs(self, part: str) -> list[str]:
        for archive in self.archive_list:
            if archive.root_name == part:
                if archive.is_root:
                    return []

                slugs = [archive.slug]
                current = archive
                while not current.parent.is_root:
                    current = current.parent
                    slugs.append(current.slug)
                return slugs[::-1]
        return []

    def _format_url(self, url: str) -> str:
        is_html_file = url.split('/')[-1].endswith(('.htm', '.html'))
        if not url.endswith('/') and not is_html_file:
            url += '/'
        return url.lower()

    def update_html(self, singles: Singles, archives: 'Archives', themes: Themes) -> None:

        if not self.should_update_html:
            return

        config = singles.config
        plugins = singles.plugins
        template_file = self.lookup_template(config, themes)
        if not template_file:
            raise ValueError(f"No template found for '{self.id}'.")
        template = config.env.get_template(template_file)

        has_shortcodes = any(x in self.content for x in ['{{', '{#', '{%'])
        if has_shortcodes:
            self.content = themes.shortcode_import_statement + self.content
            self.content = config.env.from_string(self.content).render({
                'mypage': self, 'meta': self.meta})

        self.summary = self._get_summary()

        context = {
            'config': config,
            'single': self,
            'singles': singles,
            'archives': archives
        }

        self.content = plugins.do_action(
            'before_render_html', target=self.content, **context)

        self.html = template.render({'mypage': self})

        self.html = plugins.do_action(
            'after_render_html', target=self.html, **context)

    def lookup_template(self, config: Config, themes: Themes) -> str:

        search_list = []

        if config['mode'] == 'draft':
            search_list.append('draft.html')

        template_file = self.meta.get('template')
        if template_file:
            search_list.append(template_file)

        search_list.extend([
            f'single-{self.post_type}.html',
            'single.html',
            'main.html',
        ])

        return themes.lookup_template(search_list)
