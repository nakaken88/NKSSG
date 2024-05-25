from pathlib import Path, PurePath

from nkssg.config import Config, TermConfig
from nkssg.structure.plugins import Plugins
from nkssg.structure.pages import Pages, Page
from nkssg.structure.singles import Singles
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
        self.update_archive_attribute()

        self.plugins.do_action('after_setup_archives', target=self)

    def create_archive(self, id: PurePath) -> 'Archive':
        if id in self.archives:
            return self.archives[id]

        parent = self.create_archive(id.parent)
        archive = Archive(parent, id.name)

        parent.children[id.name] = archive
        archive.parent = parent

        self.archives[archive.id] = archive
        return archive

    @staticmethod
    def get_modified_top_name(old_path: PurePath, new_top_name) -> PurePath:
        sub_path = old_path.relative_to(old_path.parents[-2])
        new_path = PurePath("/") / new_top_name / sub_path
        return new_path

    def setup_post_type_archives(self, singles: Singles):
        for single in singles.pages:
            post_type_name = single.post_type
            post_type_config = self.config.post_type.get(post_type_name, {})

            archive_type = post_type_config.get('archive_type', '').lower()

            if archive_type == 'section':
                id = self.get_modified_top_name(single.id, 'section').parent

            elif archive_type == 'simple':
                id = PurePath('/simple', post_type_name)

            elif archive_type == 'date':
                id = PurePath('/date', post_type_name)
                id = id / PurePath(str(single.date.year).zfill(4))
                id = id / PurePath(str(single.date.month).zfill(2))

            else:
                continue

            archive = self.create_archive(id)

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

        root_id = PurePath('/taxonomy', tax_name)

        for term_name, term_config in terms.items():

            id = root_id / term_name
            archive = self.create_archive(id)

            parent_id = root_id / term_config.parent
            parent = self.create_archive(parent_id)

            parent.children[term_name] = archive

    def reassign_id(self, base_id: PurePath, terms: dict[str, TermConfig]):

        ids_to_remove = set()
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

        for id in ids_to_remove:
            del self.archives[id]
            del base_archive.children[id.name]

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
                    id = self.long_ids[short_id]
                    archive = self.create_archive(id)
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

    def update_archive_attribute(self):
        for archive in self.archives.values():
            if len(archive.id.parts) <= 2:
                continue

            if len(archive.id.parts) == 3:
                archive.is_root = True
                archive.archive_type = archive.id.parts[1]

            archive.root_name = archive.id.parts[2]
            archive.singles_all_count = len(archive.singles_all)

            archive.name = Page.clean_name(archive.id.name)
            archive.slug = Page.to_slug(archive.name)  # todo

    def update_urls(self):
        for id, archive in self.archives.items():
            if len(id.parts) < 3:
                continue

            archive_type = id.parts[1]
            parent = self.create_archive(id.parent)

            root_name = id.parts[2]

            if archive_type == 'taxonomy':
                root_config = self.config.taxonomy[root_name]
            else:
                root_config = self.config.post_type[root_name]

            add_prefix_to_url = root_config.get('add_prefix_to_url', True)
            flat_url = root_config.get('flat-url', False)
            slug = Page.to_slug(root_config.slug or root_name)

            if add_prefix_to_url:
                root_dest = Path(slug, 'index.html')
            else:
                root_dest = Path('index.html')

            if len(id.parts) == 3:
                archive.dest_path = root_dest
            else:
                if flat_url:
                    base_path = root_dest.parent
                else:
                    base_path = parent.dest_path.parent

                archive.dest_path = base_path / archive.slug / 'index.html'

            archive.rel_url = archive._get_url_from_dest()
            archive._url_setup(self.config)

        self.plugins.do_action(
            'after_update_archives_url', target=self)

    def update_htmls(self, singles, themes: Themes):
        self.plugins.do_action('before_update_archives_html', target=self)

        for archive in self.archives.values():
            self.pages += archive.get_archives(singles, self, themes)

        self.plugins.do_action('after_update_archives_html', target=self)


class Archive(Page):

    def __init__(self, parent, name):
        super().__init__()

        self.id: PurePath
        self.set_id(parent, name)

        self.archive_type = ''
        self.name = str(name)
        self.title = self.name
        self.slug = ''

        self.page_type = 'archive'

        self.path = ''
        self.root_archive = ''
        self.root_name = ''
        self.is_root = False
        self.parent = None
        self.parents = []
        self.children = {}

        self.singles = []
        self.singles_all = []
        self.singles_all_count = 0
        self.single_index = None

    def __str__(self):
        return f"Archive(id='{self.id}')"

    def set_id(self, parent, name):
        if parent is not None:
            self.id = PurePath(parent.id, name)
            self.archive_type = self.id.parts[1]
        else:
            self.id = PurePath(name)

    def add_singles(self, singles, root_name):
        if self.archive_type == 'taxonomy':
            for single in singles:
                if single.meta.get(root_name) is None:
                    continue
                if not isinstance(single.meta[root_name], list):
                    single.meta[root_name] = [single.meta[root_name]]

                self.add_single_to_taxonomy_archive(single, root_name)

    def add_single_to_section_archive(self, single):
        if str(self.path) in str(single.abs_src_path.parent):
            if self.path == single.abs_src_path.parent:
                target_archive = self

                for parent in target_archive.parents:
                    parent.singles_all.append(single)

                target_archive.singles.append(single)
                target_archive.singles_all.append(single)
                single.archive_list.append(target_archive)

                # get data from single index file
                if single.filename == 'index':
                    self.file_id = single.file_id
                    self.meta = single.meta
                    self.title = single.title
                    self.name = single.name
                    self.slug = single.slug
                    self.content = single.content
                    self.summary = single.summary
                    self.image = single.image

                    self.html = single.html
                    self.archive_list = single.archive_list
                    self.shouldUpdateHtml = single.shouldUpdateHtml
                    self.shouldOutput = single.shouldOutput
                    self.single_index = single

            else:
                for archive in self.children.values():
                    archive.add_single_to_section_archive(single)

    def add_single_to_taxonomy_archive(self, single, root_name):
        for archive in self.children.values():
            if archive.name in single.meta[root_name]:
                target_archive = archive
                for parent in target_archive.parents:
                    if single not in parent.singles_all:
                        parent.singles_all.append(single)

                if single not in target_archive.singles:
                    target_archive.singles.append(single)
                    target_archive.singles_all.append(single)
                    single.archive_list.append(target_archive)

            archive.add_single_to_taxonomy_archive(single, root_name)

    def update_url(self):
        if self.singles_all is None or len(self.singles_all) == 0:
            return

        if self.archive_type != 'section':
            return

        # get data from single index file
        if self.single_index is not None:
            self.url = self.single_index.url
            self.abs_url = self.single_index.abs_url
            self.rel_url = self.single_index.rel_url
            self.dest_path = self.single_index.dest_path
            self.dest_dir = self.single_index.dest_dir

        if self.children is not None:
            for child_archive in self.children.values():
                child_archive.update_url()

    def get_archives(self, singles, archives: Archives, themes: Themes):

        if not self.shouldUpdateHtml:
            return []

        if self.singles_all is None or len(self.singles_all) == 0:
            return []

        if self.single_index is not None:
            self.content = self.single_index.content

        config = archives.config
        dest_dir = self.dest_path.parent

        root_name = self.id.parts[2]

        paginator = {}
        paginator['pages'] = []

        self.archive_type = self.id.parts[1]
        if self.archive_type == 'date':
            target_singles = self.singles_all

            post_type_dict = config.post_type[root_name]
            paginator['limit'] = post_type_dict.get('limit') or 10

        elif self.archive_type == 'section' or self.archive_type == 'simple':
            target_singles = self.singles

            post_type_dict = config.post_type[root_name]
            paginator['limit'] = post_type_dict.get('limit') or len(target_singles)

        elif self.archive_type == 'taxonomy':
            target_singles = self.singles_all

            post_type_dict = config.taxonomy[root_name]
            paginator['limit'] = post_type_dict.limit

        paginator['total_elements'] = len(target_singles)

        paginator['first_limit'] = post_type_dict.get('first_limit', paginator['limit'])

        paginator['path'] = post_type_dict.get('path', 'path')

        # count archive page
        start = 0
        end = min(paginator['first_limit'], paginator['total_elements'])
        page_index = 1

        while page_index == 1 or start < end:

            archive = Archive(None, self.name)
            if page_index == 1:
                archive.dest_path = dest_dir / 'index.html'
            else:
                archive.dest_path = dest_dir / paginator['path'] / str(page_index) / 'index.html'

            archive.rel_url = archive._get_url_from_dest()
            archive._url_setup(config)

            archive.page_number = page_index

            paginator['pages'].append(archive)

            page_index = page_index + 1
            start = end
            end = min(start + paginator['limit'], paginator['total_elements'])

        paginator['total_pages'] = len(paginator['pages'])
        paginator['first'] = paginator['pages'][0]
        paginator['last'] = paginator['pages'][-1]

        for i in range(paginator['total_pages']):
            if i == 0:
                start = 0
                end = min(paginator['first_limit'], paginator['total_elements'])
            else:
                start = end
                end = min(start + paginator['limit'], paginator['total_elements'])

            paginator['paged'] = i + 1

            paginator['has_prev'] = (i > 0)
            if paginator['has_prev']:
                paginator['prev'] = paginator['pages'][i - 1]
            else:
                paginator['prev'] = None

            paginator['has_next'] = (i < paginator['total_pages'] - 1)
            if i < paginator['total_pages'] - 1:
                paginator['next'] = paginator['pages'][i + 1]
            else:
                paginator['next'] = None

            template_file = self.lookup_template(themes)
            template = config.env.get_template(template_file)

            paginator['pages'][i].html = template.render({
                'mypage': self,
                'pages': target_singles[start:end],
                'paginator': paginator,
                })

        return paginator['pages']

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
