from concurrent.futures import ThreadPoolExecutor
import logging
from pathlib import Path, PurePath

from nkssg.structure.config import Config, TermConfig
from nkssg.structure.plugins import Plugins
from nkssg.structure.pages import Page
from nkssg.structure.singles import Singles, Single
from nkssg.structure.themes import Themes


class Archives:
    def __init__(self, config: Config, plugins: Plugins):
        self.config = config
        self.plugins = plugins
        self.archives: dict[PurePath, Archive] = {}
        self.long_ids: dict[PurePath, PurePath] = {}  # for taxonomy
        self.rendered_pages: list[Page] = []

        global_root_archive = Archive(None, '/')
        self.archives[global_root_archive.id] = global_root_archive

    def __iter__(self):
        return iter(self.archives.values())

    def output(self):
        for page in self.rendered_pages:
            page.output(self.config)

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
            self.initialize_taxonomy_archives(tax_name, tax_config.terms)

        self.add_singles_to_taxonomy_archives(singles)

    def initialize_taxonomy_archives(
            self, tax_name, terms: dict[str, TermConfig]):

        base_id = PurePath('/taxonomy', tax_name)
        term_paths: dict[str, PurePath] = {}

        def get_path(term_name: str) -> PurePath:
            if term_name in term_paths:
                return term_paths[term_name]
            parent_name = terms[term_name].parent
            if parent_name in ('', tax_name):
                path = base_id / term_name
            else:
                path = get_path(parent_name) / term_name
            term_paths[term_name] = path
            return path

        for term_name in terms:
            archive_id = get_path(term_name)
            self.create_archive(archive_id)
            self.long_ids[PurePath('/taxonomy', tax_name, term_name)] = archive_id

    def add_singles_to_taxonomy_archives(self, singles: Singles):
        taxonomy_root_archive = self.create_archive(PurePath('/taxonomy'))
        for root_name in taxonomy_root_archive.children:
            for single in singles:
                if single.meta.get(root_name) is None:
                    continue
                terms = single.meta[root_name]
                if not isinstance(terms, list):
                    terms = [terms]
                for term in terms:
                    short_id = PurePath('/taxonomy', root_name, term)
                    if short_id not in self.long_ids:
                        logging.warning(f'{root_name}: {term} is not found ({single})')
                        continue

                    archive_id = self.long_ids[short_id]
                    archive = self.archives[archive_id]
                    if single not in archive.singles:
                        archive.singles.append(single)
                        single.archive_list.append(archive)

    def update_singles_all(self):
        seen: dict['Archive', set] = {}

        for archive in self.archives.values():
            if len(archive.id.parts) <= 2 or archive.children:
                continue

            archive.singles_all = archive.singles[:]
            seen[archive] = set(archive.singles)

            current = archive
            while len(current.id.parts) > 3:
                parent = current.parent
                if parent not in seen:
                    parent.singles_all = parent.singles[:]
                    seen[parent] = set(parent.singles)

                for single in current.singles_all:
                    if single not in seen[parent]:
                        parent.singles_all.append(single)
                        seen[parent].add(single)
                current = parent

    def link_section_archive_to_single(self, singles: Singles):
        attrs = [
            'file_id', 'meta', 'title', 'name', 'slug', 'content',
            'summary', 'image', 'archive_list',
            'should_update_html', 'should_output'
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
            # skip virtual root archives (/, /section, /taxonomy, etc.)
            if len(archive_id.parts) < 3:
                continue

            parent = self.archives[archive_id.parent]

            # get config for this archive type
            if archive.archive_type == 'taxonomy':
                root_config = self.config.taxonomy[archive.root_name]
            else:
                root_config = self.config.post_type[archive.root_name]

            # determine root dest path (e.g. /posts/ or /blog/)
            add_prefix_to_url = root_config.get('add_prefix_to_url', True)
            if add_prefix_to_url:
                slug = Page.to_slug(root_config.slug or archive.root_name)
                root_dest = Path(slug, 'index.html')
            else:
                root_dest = Path('index.html')

            # set dest_path: root archives use root_dest, nested use parent or flat base
            if len(archive_id.parts) == 3:
                archive.dest_path = root_dest
            else:
                flat_url = root_config.get('flat_url', False)
                base_path = root_dest.parent if flat_url else parent.dest_path.parent
                archive.dest_path = base_path / archive.slug / 'index.html'

            # section archives with index.md use the single's path
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

        def get_pages(archive: Archive) -> list[Page]:
            return archive.get_archive_pages(self.config, themes)

        with ThreadPoolExecutor() as executor:
            results = executor.map(get_pages, self.archives.values())
            for pages in results:
                self.rendered_pages.extend(pages)

        self.plugins.do_action('after_update_archives_html', target=self)


class Archive(Page):

    def __init__(self, parent: 'Archive | None', name):
        super().__init__()

        self.id = PurePath(parent.id if parent else '', name)

        self.name = Page.clean_name(name)
        self.title = self.name
        self.slug = Page.to_slug(self.name)

        self.page_type = 'archive'
        self.archive_type = self.id.parts[1] if len(self.id.parts) >= 2 else ''

        self.parent: 'Archive | None' = parent
        self.children: dict[str, 'Archive'] = {}

        self.singles: list[Single] = []
        self.singles_all: list[Single] = []
        self.single: Single | None = None

    def __str__(self):
        return f"Archive(id='{self.id}')"

    @property
    def parents(self) -> list['Archive']:
        result = []
        current = self.parent
        while current is not None and current.id != PurePath('/'):
            result.append(current)
            current = current.parent
        result.reverse()
        return result

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

    def get_archive_pages(self, config: Config, themes: Themes) -> list[Page]:

        if not self.should_update_html or self.singles_all_count == 0:
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

    def lookup_template(self, themes: Themes) -> str | None:
        prefix = f'archive-{self.archive_type}'

        search_list = [
            f'{prefix}-{self.root_name}-{self.slug}.html',
            f'{prefix}-{self.slug}.html',
            f'{prefix}-{self.name}.html',
            f'{prefix}-{self.root_name}.html',
            f'{prefix}.html',
            'archive.html',
            'main.html'
        ]

        return themes.lookup_template(search_list)
