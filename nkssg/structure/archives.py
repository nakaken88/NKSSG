from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from pathlib import Path, PurePath

from nkssg.structure.config import Config, TermConfig
from nkssg.structure.plugins import Plugins
from nkssg.structure.pages import Pages, Page
from nkssg.structure.singles import Singles, Single
from nkssg.structure.themes import Themes


class Archives(Pages):
    def __init__(self, config: Config, plugins: Plugins):
        self.config = config
        self.plugins = plugins
        self.archives: dict[PurePath, Archive] = {}
        self.long_ids: dict[PurePath, PurePath] = {}  # for taxonomy
        self.pages = []

        global_root_archive = Archive(None, '/')
        self.archives[global_root_archive.id] = global_root_archive

    def __iter__(self):
        return iter(self.archives.values())

    def setup(self, singles):

        self.setup_post_type_archives(singles)
        self.setup_taxonomy_archives(singles)
        self.update_singles_all()
        self.link_section_archive_to_single(singles)

        self.plugins.do_action('after_setup_archives', target=self)

    def create_archive(self, archive_id: PurePath) -> 'Archive':
        if archive_id in self.archives:
            return self.archives[archive_id]

        parent = self.create_archive(archive_id.parent)
        archive = Archive(parent, archive_id.name)

        parent.children[archive_id.name] = archive
        archive.parent = parent

        self.archives[archive.id] = archive
        return archive

    @staticmethod
    def modified_id(old_id: PurePath, index: int, new_part_name) -> PurePath:
        parts = list(old_id.parts)
        parts[index] = new_part_name
        return PurePath(*parts)

    def setup_post_type_archives(self, singles: Singles):
        for single in singles.pages:
            post_type_name = single.post_type
            archive_type = single.archive_type

            if archive_type == 'section':
                archive_id = self.modified_id(single.id.parent, 1, 'section')

            elif archive_type == 'simple':
                archive_id = PurePath('/simple', post_type_name)

            elif archive_type == 'date':
                yyyy = str(single.date.year).zfill(4)
                mm = str(single.date.month).zfill(2)
                archive_id = PurePath('/date', post_type_name, yyyy, mm)

            else:
                continue

            archive = self.create_archive(archive_id)

            archive.singles.append(single)
            single.archive_list.append(archive)

    def setup_taxonomy_archives(self, singles):

        for tax_name, tax_config in self.config.taxonomy.items():
            root_id = PurePath('/taxonomy', tax_name)
            self.initialize_taxonomy_archives(tax_name, tax_config.terms)
            self.reassign_id(root_id, tax_config.terms)

        self.add_singles_to_taxonomy_archives(singles)

    def initialize_taxonomy_archives(
            self, tax_name, terms: dict[str, TermConfig]):

        for term_name, term_config in terms.items():

            archive_id = PurePath('/taxonomy', tax_name, term_name)
            archive = self.create_archive(archive_id)

            parent_id = PurePath('/taxonomy', tax_name, term_config.parent)
            parent = self.create_archive(parent_id)

            parent.children[term_name] = archive

    def reassign_id(self, base_id: PurePath, terms: dict[str, TermConfig]):

        ids_to_remove: set[PurePath] = set()
        base_archive = self.create_archive(base_id)

        for child_name, child_archive in base_archive.children.items():
            term_config = terms[child_name]
            if term_config.parent in ('', base_id.name):
                new_id = base_archive.id / child_name
                self.create_archive(new_id)
                self.long_ids[child_archive.id] = new_id
                self.reassign_id(child_archive.id, terms)
            else:
                ids_to_remove.add(child_archive.id)

        for archive_id in ids_to_remove:
            del self.archives[archive_id]
            del base_archive.children[archive_id.name]

    def add_singles_to_taxonomy_archives(self, singles: Singles):
        taxonomy_root_archive = self.create_archive(PurePath('/taxonomy'))
        for root_name in taxonomy_root_archive.children:
            for single in singles:
                if single.meta.get(root_name) is None:
                    continue
                if not isinstance(single.meta[root_name], list):
                    single.meta[root_name] = [single.meta[root_name]]

                for term in single.meta[root_name]:
                    short_id = PurePath('/taxonomy', root_name, term)
                    if short_id not in self.long_ids:
                        logging.warning(f'{root_name}: {term} is not found ({single})')
                        continue

                    archive_id = self.long_ids[short_id]
                    archive = self.create_archive(archive_id)
                    if single not in archive.singles:
                        archive.singles.append(single)
                        single.archive_list.append(archive)

    def update_singles_all(self):
        for archive in self.archives.values():
            if len(archive.id.parts) <= 2 or archive.children:
                continue

            archive.singles_all = archive.singles[:]
            current_id = archive.id
            while len(current_id.parts) > 3:
                current = self.create_archive(current_id)
                parent = self.create_archive(current_id.parent)

                for single in parent.singles:
                    if single not in parent.singles_all:
                        parent.singles_all.append(single)

                for single in current.singles_all:
                    if single not in parent.singles_all:
                        parent.singles_all.append(single)
                current_id = current_id.parent

    def link_section_archive_to_single(self, singles: Singles):
        attrs = [
            'file_id', 'meta', 'title', 'name', 'slug', 'content',
            'summary', 'image', 'archive_list',
            'shouldUpdateHtml', 'shouldOutput'
        ]
        for single in singles:
            archive_type = single.archive_type
            if single.filename == 'index' and archive_type == 'section':
                temp_id = self.modified_id(single.id.parent, 1, 'section')
                if temp_id in self.archives:
                    archive = self.archives[temp_id]
                    archive.single = single
                    for attr in attrs:
                        setattr(archive, attr, getattr(single, attr))

    def update_urls(self):
        for archive_id, archive in self.archives.items():
            if len(archive_id.parts) < 3:
                continue

            parent = self.create_archive(archive_id.parent)

            if archive.archive_type == 'taxonomy':
                root_config = self.config.taxonomy[archive.root_name]
            else:
                root_config = self.config.post_type[archive.root_name]

            add_prefix_to_url = root_config.get('add_prefix_to_url', True)

            if add_prefix_to_url:
                slug = Page.to_slug(root_config.slug or archive.root_name)
                root_dest = Path(slug, 'index.html')
            else:
                root_dest = Path('index.html')

            if len(archive_id.parts) == 3:
                archive.dest_path = root_dest
            else:
                flat_url = root_config.get('flat-url', False)
                if flat_url:
                    base_path = root_dest.parent
                else:
                    base_path = parent.dest_path.parent

                archive.dest_path = base_path / archive.slug / 'index.html'

            if archive.single:
                archive.dest_path = archive.single.dest_path
                archive.dest_dir = archive.single.dest_dir

            archive.rel_url = archive._get_url_from_dest()
            archive._url_setup(self.config)

        self.plugins.do_action(
            'after_update_archives_url', target=self)

    def update_htmls(self, singles: Singles, themes: Themes):
        self.plugins.do_action('before_update_archives_html', target=self)

        self.link_section_archive_to_single(singles)

        def render_archive_html(archive: Archive):
            self.pages += archive.get_archive_pages(self.config, themes)

        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(render_archive_html, archive)
                for archive in self.archives.values()
            ]
            for future in as_completed(futures):
                future.result()

        self.plugins.do_action('after_update_archives_html', target=self)


class Archive(Page):

    def __init__(self, parent: 'Archive', name):
        super().__init__()

        self.id = PurePath(parent.id if parent else '', name)

        self.name = Page.clean_name(name)
        self.title = self.name
        self.slug = Page.to_slug(self.name)

        self.page_type = 'archive'

        self.parent = None
        self.parents = []
        self.children: dict[str, 'Archive'] = {}

        self.singles = []
        self.singles_all = []
        self.single: Single | None = None

    def __str__(self):
        return f"Archive(id='{self.id}')"

    @property
    def is_root(self):
        # /{archive_type}/{root_name}/
        return len(self.id.parts) == 3

    @property
    def root_name(self):
        return self.id.parts[2] if len(self.id.parts) >= 3 else ''

    @property
    def singles_all_count(self):
        return len(self.singles_all)

    def get_archive_pages(self, config: Config, themes: Themes):

        if not self.shouldUpdateHtml or self.singles_all_count == 0:
            return []

        if self.archive_type == 'date':
            target_singles = self.singles_all
            post_type_dict = config.post_type[self.root_name]
            limit = post_type_dict.get('limit') or 12

        elif self.archive_type == 'taxonomy':
            target_singles = self.singles_all
            post_type_dict = config.taxonomy[self.root_name]
            limit = post_type_dict.get('limit') or len(target_singles)

        else:  # section or simple
            target_singles = self.singles
            post_type_dict = config.post_type[self.root_name]
            limit = post_type_dict.get('limit') or len(target_singles)

        paginator = {}
        paginator['limit'] = limit
        paginator['path'] = post_type_dict.get('path', 'path')

        first_limit = post_type_dict.get('first_limit') or limit
        paginator['first_limit'] = first_limit
        total_elements = len(target_singles)
        paginator['total_elements'] = total_elements

        # 1. compute slices
        slices = []
        start, end = 0, min(first_limit, total_elements)
        while not slices or start < end:
            slices.append((start, end))
            start, end = end, min(end + limit, total_elements)

        # 2. create page objects
        pages: list[Page] = []
        for i, _ in enumerate(slices):
            page_index = i + 1
            parts = [paginator['path'], str(page_index), 'index.html'] if page_index > 1 else ['index.html']
            page = Page()
            page.dest_path = Path(self.dest_path.parent, *parts)
            page.rel_url = page._get_url_from_dest()
            page._url_setup(config)
            page.page_number = page_index
            pages.append(page)

        paginator['pages'] = pages
        paginator['total_pages'] = len(pages)
        paginator['first'] = pages[0]
        paginator['last'] = pages[-1]

        template_file = self.lookup_template(themes)
        if not template_file:
            raise ValueError(f"No template found for '{self.id}'.")
        template = config.env.get_template(template_file)

        # 3. render
        for i, (start, end) in enumerate(slices):
            paginator['paged'] = i + 1
            paginator['has_prev'] = i > 0
            paginator['prev'] = pages[i - 1] if paginator['has_prev'] else None
            paginator['has_next'] = i < paginator['total_pages'] - 1
            paginator['next'] = pages[i + 1] if paginator['has_next'] else None

            pages[i].html = template.render({
                'mypage': self,
                'pages': target_singles[start:end],
                'paginator': paginator,
                })

        return pages

    def lookup_template(self, themes: Themes):
        prefix = f'archive-{self.archive_type}'

        search_list = [
            f'{prefix}-{self.slug}.html',
            f'{prefix}-{self.name}.html',
            f'{prefix}-{self.root_name}.html',
            f'{prefix}.html',
            'archive.html',
            'main.html'
        ]

        return themes.lookup_template(search_list)
