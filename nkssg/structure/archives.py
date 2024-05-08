from pathlib import Path, PurePath

from nkssg.config import Config, TermConfig
from nkssg.structure.plugins import Plugins
from nkssg.structure.pages import Pages, Page
from nkssg.structure.themes import Themes
from nkssg.utils import to_slug


class Archives(Pages):
    def __init__(self, config: Config, plugins: Plugins):
        self.config = config
        self.plugins = plugins
        self.archives = []
        self.root_archives = []
        self.pages = []

        self.date_root_archive = Archive(None, '/date')
        self.simple_root_archive = Archive(None, '/simple')
        self.section_root_archive = Archive(None, '/section')
        self.taxonomy_root_archive = Archive(None, '/taxonomy')

    def __iter__(self):
        return iter(self.archives)

    def setup(self, singles):

        self.setup_post_type_archives(singles)
        self.setup_taxonomy_archives(singles)

        self.setup_parents()
        self.add_singles(singles)

        for archive in self.archives:
            archive.singles_all_count = len(archive.singles_all)

        self._root_archives = {
            str(archive.name): archive
            for archive in self.root_archives}

        self._archives = {
            (str(archive.root_name), str(archive.name)): archive
            for archive in self.archives}

        self.plugins.do_action('after_setup_archives', target=self)

    def create_archive(self, parent, name):
        archive = Archive(parent, name)
        self.archives.append(archive)
        return archive

    def create_root_archive(self, parent, name):
        root_archive = self.create_archive(parent, name)
        root_archive.root_archive = root_archive
        root_archive.root_name = root_archive.name
        root_archive.is_root = True
        self.root_archives.append(root_archive)

        return root_archive

    def setup_post_type_archives(self, singles):
        for post_type_name, post_type_config in self.config.post_type.items():

            with_front = post_type_config.with_front
            archive_type = post_type_config.archive_type

            archive_type = archive_type.lower()
            if archive_type == 'none':
                continue

            elif archive_type == 'simple':
                self.setup_simple_archive(post_type_name, singles, with_front)

            elif archive_type != 'section':
                self.setup_date_archives(post_type_name, singles, with_front)

            else:
                base_path = self.config.docs_dir / post_type_name
                self.setup_section_archive(
                    post_type_name, base_path, with_front)

    def setup_simple_archive(self, post_type, singles, with_front):
        root_archive = self.create_root_archive(
                            self.simple_root_archive, post_type)

        slug = self.config.post_type[post_type].slug or post_type
        root_archive.slug = to_slug(slug)

        if with_front:
            root_archive.dest_path = Path(root_archive.slug, 'index.html')
        else:
            root_archive.dest_path = Path('index.html')

        root_archive.rel_url = root_archive._get_url_from_dest()
        root_archive._url_setup(self.config)

        for single in singles:
            if single.post_type == post_type:
                root_archive.singles.append(single)
                root_archive.singles_all.append(single)
                single.archive_list.append(root_archive)

    def setup_date_archives(self, post_type, singles, with_front):
        date_archive = self.create_root_archive(
                            self.date_root_archive, post_type)

        slug = self.config.post_type[post_type].slug or post_type
        date_archive.slug = to_slug(slug)

        if with_front:
            date_archive.dest_path = Path(date_archive.slug, 'index.html')
        else:
            date_archive.dest_path = Path('index.html')

        date_archive.rel_url = date_archive._get_url_from_dest()
        date_archive._url_setup(self.config)

        for single in singles:
            if single.post_type != post_type:
                continue

            date_archive.singles_all.append(single)

            cdate = single.date
            year = str(cdate.year).zfill(4)
            month = str(cdate.month).zfill(2)
            year_month = year + month

            if date_archive.get_child(year) is None:
                year_archive = self.create_archive(date_archive, year)
                year_archive.slug = year
                year_archive.set_parent(date_archive, self.config)
            else:
                year_archive = date_archive.get_child(year)

            year_archive.singles_all.append(single)

            if year_archive.get_child(year_month) is None:
                month_archive = self.create_archive(year_archive, month)
                month_archive.slug = month
                month_archive.set_parent(year_archive, self.config)
            else:
                month_archive = year_archive.get_child(year_month)

            month_archive.singles.append(single)
            month_archive.singles_all.append(single)
            single.archive_list.append(month_archive)

    def setup_section_archive(self, post_type, basepath, with_front):
        root_archive = self.create_root_archive(
                            self.section_root_archive, post_type)

        slug = self.config.post_type[post_type].slug or post_type
        root_archive.slug = to_slug(slug)
        root_archive.archive_type = 'section'

        if with_front:
            root_archive.dest_path = Path(root_archive.slug, 'index.html')
        else:
            root_archive.dest_path = Path('index.html')

        root_archive.rel_url = root_archive._get_url_from_dest()
        root_archive._url_setup(self.config)

        root_archive.path = basepath
        archive_dict = {basepath: root_archive}
        flat_url = self.config.post_type[root_archive.name].get('flat-url') or False

        dirs = [d for d in basepath.glob('**/*') if d.is_dir()]
        for dir in sorted(dirs):
            parent_archive = archive_dict[dir.parent]

            name = Page.clean_name(dir.parts[-1])
            new_archive = self.create_archive(parent_archive, name)
            new_archive.path = dir

            new_archive.set_parent(parent_archive, self.config, flat_url)
            archive_dict[dir] = new_archive

    def setup_taxonomy_archives(self, singles):
        for tax_name, tax_config in self.config.taxonomy.items():

            root_archive = self.create_root_archive(
                                    self.taxonomy_root_archive, tax_name)

            slug = tax_config.slug or tax_name
            root_archive.slug = to_slug(slug)
            root_archive.archive_type = 'taxonomy'

            root_archive.dest_path = Path(root_archive.slug, 'index.html')
            root_archive.rel_url = root_archive._get_url_from_dest()
            root_archive._url_setup(self.config)
            root_archive.meta = {}

            self.setup_taxonomy_archive(
                root_archive, tax_name, tax_config.term)

    def setup_taxonomy_archive(
            self,
            root_archive,
            tax_name,
            term_list: list[TermConfig]
            ):

        archive_dict = {tax_name: root_archive}
        parent_names = {tax_name: ''}

        for term in term_list:

            name = term.name
            slug = term.slug or name
            parent_name = term.parent or tax_name

            new_archive = self.create_archive(None, name)
            new_archive.slug = to_slug(slug)
            archive_dict[name] = new_archive
            parent_names[name] = parent_name
            new_archive.meta = term

        flat_url = self.config.taxonomy[root_archive.name].get('flat-url') or False

        for archive_item in archive_dict.values():
            parent_name = parent_names[archive_item.name]
            if parent_name != '' and parent_name in archive_dict.keys():
                parent = archive_dict[parent_name]
                archive_item.set_parent(parent, self.config, flat_url)
                archive_item.set_id(parent, archive_item.name)

    def setup_parents(self):
        for root_archive in self.root_archives:
            for child_archve in root_archive.children:
                self.update_parents(child_archve)

    def update_parents(self, target_archive):
        parent_archive = target_archive.parent
        target_archive.parents = [*parent_archive.parents, parent_archive]
        target_archive.root_name = parent_archive.root_name

        for child_archve in target_archive.children:
            self.update_parents(child_archve)

    def add_singles(self, singles):
        for root_archive in self.root_archives:
            if root_archive.archive_type != 'date':
                root_archive.add_singles(singles, root_archive.root_name)

    def update_urls(self):
        for root_archive in self.root_archives:
            root_archive.update_url()

        self.plugins.do_action(
            'after_update_archives_url', target=self)

    def update_htmls(self, singles, themes: Themes):
        self.plugins.do_action(
            'before_update_archives_html', target=self)

        for archive in self.archives:
            self.pages += archive.get_archives(singles, self, themes)

        self.plugins.do_action(
            'after_update_archives_html', target=self)

    def get_root_archive_by_name(self, name):
        name = str(name)
        archive = self._root_archives.get(name)
        if archive is None:
            print('root archive:' + name + ' is not found.')
        return archive

    def get_archive_by_name(self, root_name, name):
        root_name, name = str(root_name), str(name)
        archive = self._archives.get((root_name, name))
        if archive is None:
            print('archive:(' + root_name + ', ' + name + ') is not found.')
        return archive


class Archive(Page):

    def __init__(self, parent, name):
        super().__init__()

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
        self.children = []

        self.singles = []
        self.singles_all = []
        self.single_index = None

    def __str__(self):
        return f"Archive(id='{self.id}')"

    def set_id(self, parent, name):
        if parent is not None:
            self.id = PurePath(parent.id, name)
            self.archive_type = self.id.parts[1]
        else:
            self.id = PurePath(name)

    def get_child(self, name):
        for child in self.children:
            if child.name == str(name):
                return child
        return None

    def set_parent(self, parent, config, flat_url=False):
        self.parent = parent
        parent.children.append(self)
        self.root_archive = parent.root_archive

        if flat_url:
            base_path = self.root_archive.dest_path.parent
        else:
            base_path = parent.dest_path.parent

        self.dest_path = base_path / self.slug / 'index.html'
        self.rel_url = self._get_url_from_dest()
        self._url_setup(config)

    def add_singles(self, singles, root_name):
        if self.archive_type == 'section':
            for single in singles:
                if single.archive_type == 'section':
                    self.add_single_to_section_archive(single)

        elif self.archive_type == 'taxonomy':
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
                for archive in self.children:
                    archive.add_single_to_section_archive(single)

    def add_single_to_taxonomy_archive(self, single, root_name):
        for archive in self.children:
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
            for child_archive in self.children:
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

        paginator = {}
        paginator['pages'] = []

        self.archive_type = self.id.parts[1]
        if self.archive_type == 'date':
            target_singles = self.singles_all

            post_type_dict = config.post_type[self.root_name]
            paginator['limit'] = post_type_dict.get('limit') or 10

        elif self.archive_type == 'section' or self.archive_type == 'simple':
            target_singles = self.singles

            post_type_dict = config.post_type[self.root_name]
            paginator['limit'] = post_type_dict.get('limit') or len(target_singles)

        elif self.archive_type == 'taxonomy':
            target_singles = self.singles_all

            post_type_dict = config.taxonomy[self.root_name]
            paginator['limit'] = post_type_dict.limit

        paginator['total_elements'] = len(target_singles)

        paginator['first_limit'] = post_type_dict.get('first_limit') or paginator['limit']

        paginator['path'] = post_type_dict.get('path') or 'path'

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

            template_file = self.lookup_template(config, themes)
            template = config.env.get_template(template_file)

            paginator['pages'][i].html = template.render({
                'mypage': self,
                'pages': target_singles[start:end],
                'paginator': paginator,
                })

        return paginator['pages']

    def lookup_template(self, config, themes: Themes):
        prefix = 'archive-' + self.archive_type

        for theme_dir in themes.dirs:

            template_file = prefix + '-' + self.slug + '.html'
            template_path = theme_dir / template_file
            if template_path.exists():
                return template_file

            template_file = prefix + '-' + self.name + '.html'
            template_path = theme_dir / template_file
            if template_path.exists():
                return template_file

            template_file = prefix + '-' + self.root_name + '.html'
            template_path = theme_dir / template_file
            if template_path.exists():
                return template_file

            template_file = prefix + '.html'
            template_path = theme_dir / template_file
            if template_path.exists():
                return template_file

            template_file = 'archive.html'
            template_path = theme_dir / template_file
            if template_path.exists():
                return template_file

        return 'main.html'
