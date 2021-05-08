import datetime
from pathlib import Path
from urllib.parse import quote

from nkssg.structure.pages import Pages, Page
from nkssg.utils import clean_name, get_config_by_list, to_slug


class Archives(Pages):
    def __init__(self, config):
        self.config = config
        self.archives = []
        self.root_archives = []
        self.pages = []

    def __iter__(self):
        return iter(self.archives)


    def setup(self, singles):

        self.setup_post_type_archives(singles)
        self.setup_taxonomy_archives(singles)

        self.setup_parents()
        self.add_singles(singles)

        for archive in self.archives:
            archive.singles_all_count = len(archive.singles_all)

        self.config['plugins'].do_action('after_setup_archives', target=self)


    def create_archive(self, archive_type, name, slug=''):
        archive = Archive(len(self.archives) + 1, archive_type, name, slug)
        self.archives.append(archive)
        return archive

    def create_root_archive(self, archive_type, name, slug=''):
        root_archive = self.create_archive(archive_type, name, slug)
        root_archive.root_name = root_archive.name
        root_archive.is_root = True
        self.root_archives.append(root_archive)

        return root_archive


    def setup_post_type_archives(self, singles):
        for post_type in self.config['post_type_list']:
            post_type_dict = get_config_by_list(self.config, ['post_type', post_type])

            with_front = get_config_by_list(post_type_dict, 'with_front')
            archive_type = get_config_by_list(post_type_dict, 'archive_type') or ''

            archive_type = archive_type.lower()
            if archive_type == 'none':
                continue
            elif archive_type != 'section':
                self.setup_date_archives(post_type, singles, with_front)

            else:
                base_path = self.config['docs_dir'] / post_type
                self.setup_section_archive(post_type, base_path, with_front)


    def setup_date_archives(self, post_type, singles, with_front):
        slug = get_config_by_list(self.config, ['post_type', post_type, 'slug'])
        date_archive = self.create_root_archive('date', post_type, slug)

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
                year_archive = self.create_archive('date', year)
                year_archive.set_parent(date_archive, self.config)
            else:
                year_archive = date_archive.get_child(year)

            year_archive.singles_all.append(single)


            if year_archive.get_child(year_month) is None:
                month_archive = self.create_archive('date', year_month, month)
                month_archive.set_parent(year_archive, self.config)
            else:
                month_archive = year_archive.get_child(year_month)

            month_archive.singles.append(single)
            month_archive.singles_all.append(single)
            single.archive_list.append(month_archive)


    def setup_section_archive(self, post_type, basepath, with_front):
        slug = get_config_by_list(self.config, ['post_type', post_type, 'slug'])
        root_archive = self.create_root_archive('section', post_type, slug)

        if with_front:
            root_archive.dest_path = Path(root_archive.slug, 'index.html')
        else:
            root_archive.dest_path = Path('index.html')

        root_archive.rel_url = root_archive._get_url_from_dest()
        root_archive._url_setup(self.config)


        root_archive.path = basepath
        archive_dict = {basepath: root_archive}

        dirs = [d for d in basepath.glob('**/*') if d.is_dir()]
        for dir in sorted(dirs):
            name = clean_name(dir.parts[-1])
            new_archive = self.create_archive('section', name)
            new_archive.path = dir

            parent_archive = archive_dict[dir.parent]
            new_archive.set_parent(parent_archive, self.config)
            archive_dict[dir] = new_archive


    def setup_taxonomy_archives(self, singles):
        for tax_dict in self.config['taxonomy']:
            tax_name = list(tax_dict.keys())[0] 
            term_list = tax_dict[tax_name]
            self.setup_taxonomy_archive(tax_name, term_list)

    def setup_taxonomy_archive(self, tax_name, term_list):
        slug = get_config_by_list(term_list, ['slug']) or tax_name

        root_archive = self.create_root_archive('taxonomy', tax_name, slug)
        root_archive.dest_path = Path(root_archive.slug, 'index.html')
        root_archive.rel_url = root_archive._get_url_from_dest()
        root_archive._url_setup(self.config)


        archive_dict = {tax_name: root_archive}
        parent_names = {tax_name: ''}

        for term_item in term_list:
            if type(term_item) != dict:
                term_item = {term_item: {}}

            name = list(term_item.keys())[0]
            term_dict = term_item[name]
            if type(term_dict) != dict:
                continue # it is taxonomy setting

            slug = term_dict.get('slug', name)
            parent_name = term_dict.get('parent', tax_name)

            new_archive = self.create_archive('taxonomy', name, slug)
            archive_dict[name] = new_archive
            parent_names[name] = parent_name

        for archive_item in archive_dict.values():
            parent_name = parent_names[archive_item.name]
            if parent_name != '' and parent_name in archive_dict.keys():
                parent = archive_dict[parent_name]
                archive_item.set_parent(parent, self.config)


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

        self.config['plugins'].do_action('after_update_archives_url', target=self)

    def update_htmls(self, singles):
        self.config['plugins'].do_action('before_update_archives_html', target=self)

        for archive in self.archives:
            self.pages += archive.get_archives(singles, self)

        self.config['plugins'].do_action('after_update_archives_html', target=self)




class Archive(Page):

    def __init__(self, id, archive_type, name, slug=''):
        super().__init__()

        self._id = id

        self.archive_type = archive_type
        self.name = str(name)
        self.title = self.name
        self.slug = to_slug(slug or self.name)

        self.page_type = 'archive'

        self.path = ''
        self.root_name = ''
        self.is_root = False
        self.parent = None
        self.parents = []
        self.children = []

        self.singles = []
        self.singles_all = []
        self.single_index = None


    def __str__(self):
        return "Archive(name='{}', root='{}', type='{}')".format(self.name, self.root_name, self.archive_type)

    
    def get_child(self, name):
        for child in self.children:
            if child.name == str(name):
                return child
        return None

    def set_parent(self, parent, config):
        self.parent = parent
        parent.children.append(self)

        self.dest_path = parent.dest_path.parent / self.slug / 'index.html'
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
                if type(single.meta[root_name]) != list:
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
                    self.single_index = single

            else:
                for archive in self.children:
                    archive.add_single_to_section_archive(single)

    def add_single_to_taxonomy_archive(self, single, root_name):
        for archive in self.children:
            if archive.name in single.meta[root_name]:
                target_archive = archive
                for parent in target_archive.parents:
                    if not single in parent.singles_all:
                        parent.singles_all.append(single)

                if not single in target_archive.singles:
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

        if not self.children is None:
            for child_archive in self.children:
                child_archive.update_url()


    def get_archives(self, singles, archives):
        if self.singles_all is None or len(self.singles_all) == 0:
            return []

        if self.single_index is not None:
            self.content = self.single_index.content

        config = archives.config
        dest_dir = self.dest_path.parent

        paginator = {}
        paginator['pages'] = []

        if self.archive_type == 'date':
            target_singles = self.singles_all

            post_type_dict = get_config_by_list(config, ['post_type', self.root_name])
            paginator['limit'] = get_config_by_list(post_type_dict, 'limit') or 10

        elif self.archive_type == 'section':
            target_singles = self.singles

            post_type_dict = get_config_by_list(config, ['post_type', self.root_name])
            paginator['limit'] = get_config_by_list(post_type_dict, 'limit') or len(target_singles)

        elif self.archive_type == 'taxonomy':
            target_singles = self.singles_all

            post_type_dict = get_config_by_list(config, ['taxonomy', self.root_name])

            paginator['limit'] = get_config_by_list(post_type_dict, 'limit')
            if paginator['limit'] is None or type(paginator['limit']) == dict:
                paginator['limit'] = 10



        paginator['total_elements'] = len(target_singles)

        paginator['first_limit'] = get_config_by_list(post_type_dict, 'first_limit')
        if paginator['first_limit'] is None or type(paginator['first_limit']) == dict:
            paginator['first_limit'] = paginator['limit']

        paginator['path'] = get_config_by_list(post_type_dict, 'path')
        if paginator['path'] is None or type(paginator['path']) == dict:
            paginator['path'] = 'path'



        # count archive page
        start = 0
        end = min(paginator['first_limit'], paginator['total_elements'])
        page_index = 1

        while page_index == 1 or start < end:

            archive = Archive(0, self.archive_type, self.name, self.slug)
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


            template_file = self.lookup_template(config)
            template = config['env'].get_template(template_file)

            paginator['pages'][i].html = template.render({
                'mypage': self,
                'pages': target_singles[start:end],
                'paginator': paginator,
                })

        return paginator['pages']


    def lookup_template(self, config):
        prefix = 'archive-' + self.archive_type

        for theme_dir in config['themes'].dirs:

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
