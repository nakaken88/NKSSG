import pytest
from unittest.mock import MagicMock
from pathlib import PurePath
import datetime

from nkssg.structure.config import Config, PostTypeConfig, PostTypeConfigManager, TaxonomyConfig, TermConfig, TaxonomyConfigManager
from nkssg.structure.singles import Single, Singles
from nkssg.structure.archives import Archives, Archive
from nkssg.structure.plugins import Plugins


class TestArchives:
    def test_setup_post_type_archives_with_date_type(self):
        config = Config()
        
        post_type_config = PostTypeConfig(
            permalink='posts/{year}/{month}/{day}/{slug}/',
            archive_type='date',
        )
        config.post_type = PostTypeConfigManager()
        config.post_type['post'] = post_type_config

        mock_plugins = MagicMock(spec=Plugins)

        single1 = MagicMock(
            spec=Single,
            post_type='post',
            archive_type='date',
            archive_list=[],
            date=datetime.datetime(2023, 1, 15),
            id=PurePath('/docs/2023/01/15/post-1')
        )
        single2 = MagicMock(
            spec=Single,
            post_type='post',
            archive_type='date',
            archive_list=[],
            date=datetime.datetime(2023, 2, 20),
            id=PurePath('/docs/2023/02/20/post-2')
        )
        single_list = [single1, single2]
        singles = MagicMock(spec=Singles)
        singles.pages = single_list
        singles.__iter__.return_value = iter(single_list)

        archives = Archives(config, mock_plugins)
        archives.setup_post_type_archives(singles)

        # ID should be /date/{post_type_name}/{year}/{month}
        date1_id = PurePath('/date', 'post', '2023', '01')
        assert date1_id in archives.archives
        date1_archive = archives.archives[date1_id]
        assert len(date1_archive.singles) == 1
        assert single1 in date1_archive.singles

        date2_id = PurePath('/date', 'post', '2023', '02')
        assert date2_id in archives.archives
        date2_archive = archives.archives[date2_id]
        assert len(date2_archive.singles) == 1
        assert single2 in date2_archive.singles

    def test_setup_post_type_archives_with_section_type(self):
        config = Config()
        
        post_type_config = PostTypeConfig(
            permalink='posts/{slug}/',
            archive_type='section',
        )
        config.post_type = PostTypeConfigManager()
        config.post_type['post'] = post_type_config

        mock_plugins = MagicMock(spec=Plugins)

        single1 = MagicMock(
            spec=Single,
            post_type='post',
            archive_type='section',
            archive_list=[],
            date=datetime.datetime(2023, 1, 15),
            id=PurePath('/docs/my-section/post-1')
        )
        single2 = MagicMock(
            spec=Single,
            post_type='post',
            archive_type='section',
            archive_list=[],
            date=datetime.datetime(2023, 2, 20),
            id=PurePath('/docs/another-section/post-2')
        )
        single_list = [single1, single2]
        singles = MagicMock(spec=Singles)
        singles.pages = single_list
        singles.__iter__.return_value = iter(single_list)

        archives = Archives(config, mock_plugins)
        archives.setup_post_type_archives(singles)

        # ID should be /section/{section_name}
        section1_id = PurePath('/section/my-section')
        assert section1_id in archives.archives
        section1_archive = archives.archives[section1_id]
        assert len(section1_archive.singles) == 1
        assert single1 in section1_archive.singles

        section2_id = PurePath('/section/another-section')
        assert section2_id in archives.archives
        section2_archive = archives.archives[section2_id]
        assert len(section2_archive.singles) == 1
        assert single2 in section2_archive.singles

    def test_setup_post_type_archives_with_simple_type(self):
        config = Config()

        post_type_config = PostTypeConfig(archive_type='simple')
        config.post_type = PostTypeConfigManager()
        config.post_type['post'] = post_type_config

        mock_plugins = MagicMock(spec=Plugins)

        single1 = MagicMock(
            spec=Single,
            post_type='post',
            archive_type='simple',
            archive_list=[],
            id=PurePath('/docs/post/post-1')
        )
        single2 = MagicMock(
            spec=Single,
            post_type='post',
            archive_type='simple',
            archive_list=[],
            id=PurePath('/docs/post/subdir/post-2')
        )
        single_list = [single1, single2]
        singles = MagicMock(spec=Singles)
        singles.pages = single_list
        singles.__iter__.return_value = iter(single_list)

        archives = Archives(config, mock_plugins)
        archives.setup_post_type_archives(singles)

        # ID should be /simple/{post_type_name} — all singles share one archive
        simple_id = PurePath('/simple', 'post')
        assert simple_id in archives.archives
        simple_archive = archives.archives[simple_id]
        assert len(simple_archive.singles) == 2
        assert single1 in simple_archive.singles
        assert single2 in simple_archive.singles


    def test_setup_taxonomy_archives(self):
        config = Config()

        config.taxonomy = TaxonomyConfigManager()
        
        cat_tax_config = TaxonomyConfig(name='category', slug='categories')
        cat_tax_config.terms['cat1'] = TermConfig(name='cat1', slug='cat1')
        cat_tax_config.terms['cat2'] = TermConfig(name='cat2', slug='cat2')
        config.taxonomy['category'] = cat_tax_config

        mock_plugins = MagicMock(spec=Plugins)

        single1 = MagicMock(
            spec=Single,
            post_type='post',
            archive_list=[],
            id=PurePath('/docs/post-1'),
            meta={'category': ['cat1', 'cat2']}
        )
        single2 = MagicMock(
            spec=Single,
            post_type='post',
            archive_list=[],
            id=PurePath('/docs/post-2'),
            meta={'category': ['cat1']}
        )
        single_list = [single1, single2]
        singles = MagicMock(spec=Singles)
        singles.pages = single_list
        singles.__iter__.return_value = iter(single_list)

        archives = Archives(config, mock_plugins)
        archives.setup_taxonomy_archives(singles)

        # ID should be /taxonomy/{taxonomy_name}/{term_name}
        cat1_id = PurePath('/taxonomy', 'category', 'cat1')
        assert cat1_id in archives.archives
        cat1_archive = archives.archives[cat1_id]
        assert len(cat1_archive.singles) == 2
        assert single1 in cat1_archive.singles
        assert single2 in cat1_archive.singles
        
        cat2_id = PurePath('/taxonomy', 'category', 'cat2')
        assert cat2_id in archives.archives
        cat2_archive = archives.archives[cat2_id]
        assert len(cat2_archive.singles) == 1
        assert single1 in cat2_archive.singles
        assert single2 not in cat2_archive.singles

    def test_setup_taxonomy_archives_duplicate_terms(self):
        config = Config()
        config.taxonomy = TaxonomyConfigManager()

        cat_tax_config = TaxonomyConfig(name='category', slug='categories')
        cat_tax_config.terms['cat1'] = TermConfig(name='cat1', slug='cat1')
        config.taxonomy['category'] = cat_tax_config

        mock_plugins = MagicMock(spec=Plugins)

        single = MagicMock(
            spec=Single,
            post_type='post',
            archive_list=[],
            id=PurePath('/docs/post-1'),
            meta={'category': ['cat1', 'cat1']}
        )
        singles = MagicMock(spec=Singles)
        singles.__iter__.return_value = iter([single])

        archives = Archives(config, mock_plugins)
        archives.setup_taxonomy_archives(singles)

        cat1_id = PurePath('/taxonomy', 'category', 'cat1')
        assert len(archives.archives[cat1_id].singles) == 1

    def test_setup_taxonomy_archives_nested(self):
        config = Config()

        config.taxonomy = TaxonomyConfigManager()

        cat_tax_config = TaxonomyConfig(name='category', slug='categories')
        cat_tax_config.terms['cat1'] = TermConfig(name='cat1', slug='cat1')
        cat_tax_config.terms['cat2'] = TermConfig(name='cat2', slug='cat2', parent='cat1')
        cat_tax_config.terms['cat3'] = TermConfig(name='cat3', slug='cat3', parent='cat2')
        config.taxonomy['category'] = cat_tax_config

        mock_plugins = MagicMock(spec=Plugins)
        archives = Archives(config, mock_plugins)
        archives.setup_taxonomy_archives(MagicMock(spec=Singles, __iter__=lambda _: iter([])))

        # cat1 is root-level: /taxonomy/category/cat1
        cat1_id = PurePath('/taxonomy', 'category', 'cat1')
        assert cat1_id in archives.archives

        # cat2 is child of cat1: /taxonomy/category/cat1/cat2
        cat2_id = PurePath('/taxonomy', 'category', 'cat1', 'cat2')
        assert cat2_id in archives.archives

        # cat3 is child of cat2: /taxonomy/category/cat1/cat2/cat3
        cat3_id = PurePath('/taxonomy', 'category', 'cat1', 'cat2', 'cat3')
        assert cat3_id in archives.archives

    def test_setup_taxonomy_archives_nested_reverse_order(self):
        config = Config()

        config.taxonomy = TaxonomyConfigManager()

        # Define child before parent
        cat_tax_config = TaxonomyConfig(name='category', slug='categories')
        cat_tax_config.terms['cat2'] = TermConfig(name='cat2', slug='cat2', parent='cat1')
        cat_tax_config.terms['cat1'] = TermConfig(name='cat1', slug='cat1')
        config.taxonomy['category'] = cat_tax_config

        mock_plugins = MagicMock(spec=Plugins)
        archives = Archives(config, mock_plugins)
        archives.setup_taxonomy_archives(MagicMock(spec=Singles, __iter__=lambda _: iter([])))

        cat1_id = PurePath('/taxonomy', 'category', 'cat1')
        cat2_id = PurePath('/taxonomy', 'category', 'cat1', 'cat2')
        assert cat1_id in archives.archives
        assert cat2_id in archives.archives


    def test_setup_taxonomy_archives_circular_reference(self):
        config = Config()
        config.taxonomy = TaxonomyConfigManager()

        cat_tax_config = TaxonomyConfig(name='category', slug='categories')
        cat_tax_config.terms['A'] = TermConfig(name='A', parent='B')
        cat_tax_config.terms['B'] = TermConfig(name='B', parent='A')
        config.taxonomy['category'] = cat_tax_config

        mock_plugins = MagicMock(spec=Plugins)
        archives = Archives(config, mock_plugins)
        with pytest.raises(ValueError, match="Circular parent reference"):
            archives.setup_taxonomy_archives(
                MagicMock(spec=Singles, __iter__=lambda _: iter([])))


class TestUpdateSinglesAll:
    def test_singles_propagate_to_parent_archives(self):
        config = Config()
        archives = Archives(config, MagicMock(spec=Plugins))

        jan_archive = archives.create_archive(PurePath('/date/post/2023/01'))
        feb_archive = archives.create_archive(PurePath('/date/post/2023/02'))

        single1 = MagicMock(spec=Single)
        single2 = MagicMock(spec=Single)
        jan_archive.singles = [single1]
        feb_archive.singles = [single2]

        archives.update_singles_all()

        year_archive = archives.archives[PurePath('/date/post/2023')]
        root_archive = archives.archives[PurePath('/date/post')]

        assert single1 in jan_archive.singles_all
        assert single2 in feb_archive.singles_all
        assert single1 in year_archive.singles_all
        assert single2 in year_archive.singles_all
        assert single1 in root_archive.singles_all
        assert single2 in root_archive.singles_all

    def test_duplicate_singles_not_added_twice(self):
        config = Config()
        archives = Archives(config, MagicMock(spec=Plugins))

        jan_archive = archives.create_archive(PurePath('/date/post/2023/01'))
        feb_archive = archives.create_archive(PurePath('/date/post/2023/02'))

        single = MagicMock(spec=Single)
        jan_archive.singles = [single]
        feb_archive.singles = [single]  # same single in both months

        archives.update_singles_all()

        year_archive = archives.archives[PurePath('/date/post/2023')]
        assert year_archive.singles_all.count(single) == 1


class TestLinkSectionArchiveToSingle:
    def test_index_single_is_linked_to_section_archive(self):
        config = Config()
        archives = Archives(config, MagicMock(spec=Plugins))

        section_id = PurePath('/section/post/subdir')
        archives.create_archive(section_id)

        single = MagicMock()
        single.is_index = True
        single.archive_type = 'section'
        single.id = PurePath('/docs/post/subdir/index.md')
        single.title = 'Subdir Title'
        single.meta = {'description': 'test'}
        single.should_output = True

        singles_mock = MagicMock(spec=Singles)
        singles_mock.__iter__.return_value = iter([single])

        archives.link_section_archive_to_single(singles_mock)

        section_archive = archives.archives[section_id]
        assert section_archive.single is single
        assert section_archive.title == single.title
        assert section_archive.meta == single.meta
        assert section_archive.should_output == single.should_output

    def test_non_index_single_is_not_linked(self):
        config = Config()
        archives = Archives(config, MagicMock(spec=Plugins))

        section_id = PurePath('/section/post/subdir')
        archives.create_archive(section_id)

        single = MagicMock()
        single.is_index = False
        single.archive_type = 'section'
        single.id = PurePath('/docs/post/subdir/post.md')

        singles_mock = MagicMock(spec=Singles)
        singles_mock.__iter__.return_value = iter([single])

        archives.link_section_archive_to_single(singles_mock)

        section_archive = archives.archives[section_id]
        assert section_archive.single is None


class TestArchiveDepth:
    def _make_chain(self, *names):
        archive = Archive(None, '/')
        for name in names:
            archive = Archive(archive, name)
        return archive

    def test_depth_root(self):
        archive = self._make_chain('taxonomy', 'category')
        assert archive.depth == 0

    def test_depth_one_level(self):
        archive = self._make_chain('taxonomy', 'category', 'cat1')
        assert archive.depth == 1

    def test_depth_two_levels(self):
        archive = self._make_chain('taxonomy', 'category', 'cat1', 'cat2')
        assert archive.depth == 2

    def test_depth_date_year(self):
        archive = self._make_chain('date', 'post', '2023')
        assert archive.depth == 1

    def test_depth_date_month(self):
        archive = self._make_chain('date', 'post', '2023', '01')
        assert archive.depth == 2


class TestArchiveLookup:
    def _make_archives(self):
        config = Config()
        config.taxonomy = TaxonomyConfigManager()
        cat_config = TaxonomyConfig(name='category', slug='category')
        cat_config.terms['cat1'] = TermConfig(name='cat1', slug='cat1')
        cat_config.terms['cat2'] = TermConfig(name='cat2', slug='cat2', parent='cat1')
        config.taxonomy['category'] = cat_config
        archives = Archives(config, MagicMock(spec=Plugins))
        archives.setup_taxonomy_archives(
            MagicMock(spec=Singles, __iter__=lambda _: iter([])))
        return archives

    def test_get_root_archive_exists(self):
        archives = self._make_archives()
        root = archives.get_root_archive('taxonomy', 'category')
        assert root is not None
        assert root.is_root
        assert root.root_name == 'category'

    def test_get_root_archive_not_found(self):
        archives = self._make_archives()
        assert archives.get_root_archive('taxonomy', 'nonexistent') is None

    def test_get_terms_returns_all_terms(self):
        archives = self._make_archives()
        terms = archives.get_terms('category')
        assert len(terms) == 2
        assert all(t.root_name == 'category' for t in terms)
        assert all(not t.is_root for t in terms)

    def test_get_terms_empty_for_unknown_taxonomy(self):
        archives = self._make_archives()
        assert archives.get_terms('nonexistent') == []

    def test_get_term_returns_correct_term(self):
        archives = self._make_archives()
        term = archives.get_term('category', 'cat1')
        assert term is not None
        assert term.name == 'cat1'
        assert term.root_name == 'category'

    def test_get_term_case_insensitive(self):
        archives = self._make_archives()
        assert archives.get_term('category', 'CAT1') is archives.get_term('category', 'cat1')

    def test_get_term_nested_term(self):
        archives = self._make_archives()
        term = archives.get_term('category', 'cat2')
        assert term is not None
        assert term.name == 'cat2'

    def test_get_term_unknown_term_returns_none(self):
        archives = self._make_archives()
        assert archives.get_term('category', 'nonexistent') is None

    def test_get_term_unknown_taxonomy_returns_none(self):
        archives = self._make_archives()
        assert archives.get_term('nonexistent', 'cat1') is None


class TestUpdateUrls:
    def _make_archives(self, tax_config):
        config = Config()
        config.taxonomy = TaxonomyConfigManager()
        config.taxonomy['tag'] = tax_config

        archives = Archives(config, MagicMock(spec=Plugins))
        archives.setup_taxonomy_archives(
            MagicMock(spec=Singles, __iter__=lambda _: iter([])))
        archives.update_urls()
        return archives

    def test_update_urls_nested_taxonomy_default(self):
        tax_config = TaxonomyConfig(name='tag', slug='tag')
        tax_config.terms['parent'] = TermConfig(name='parent', slug='parent')
        tax_config.terms['child'] = TermConfig(name='child', slug='child', parent='parent')

        archives = self._make_archives(tax_config)

        parent_archive = archives.archives[PurePath('/taxonomy', 'tag', 'parent')]
        child_archive = archives.archives[PurePath('/taxonomy', 'tag', 'parent', 'child')]

        # default: child is nested under parent
        assert parent_archive.dest_path.parts == ('tag', 'parent', 'index.html')
        assert child_archive.dest_path.parts == ('tag', 'parent', 'child', 'index.html')

    def test_update_urls_nested_taxonomy_flat_url(self):
        tax_config = TaxonomyConfig(name='tag', slug='tag')
        tax_config.update({'flat_url': True})
        tax_config.terms['parent'] = TermConfig(name='parent', slug='parent')
        tax_config.terms['child'] = TermConfig(name='child', slug='child', parent='parent')

        archives = self._make_archives(tax_config)

        parent_archive = archives.archives[PurePath('/taxonomy', 'tag', 'parent')]
        child_archive = archives.archives[PurePath('/taxonomy', 'tag', 'parent', 'child')]

        # flat_url: child is at the same level as parent
        assert parent_archive.dest_path.parts == ('tag', 'parent', 'index.html')
        assert child_archive.dest_path.parts == ('tag', 'child', 'index.html')


class TestBreadcrumbs:
    def _make_chain(self, *names):
        archive = Archive(None, '/')
        for name in names:
            archive = Archive(archive, name)
        return archive

    def test_root_archive_breadcrumbs(self):
        archive = self._make_chain('section', 'docs')
        assert archive.breadcrumbs == [archive]

    def test_nested_archive_breadcrumbs(self):
        root = self._make_chain('section', 'docs')
        child = Archive(root, 'guide')
        assert child.breadcrumbs == [root, child]

    def test_deeply_nested_archive_breadcrumbs(self):
        root = self._make_chain('section', 'docs')
        child = Archive(root, 'guide')
        grandchild = Archive(child, 'intro')
        assert grandchild.breadcrumbs == [root, child, grandchild]


class TestHasPage:
    def _make_archive(self, url='/section/docs/'):
        root = Archive(None, '/')
        section = Archive(root, 'section')
        archive = Archive(section, 'docs')
        archive.url = url
        return archive

    def test_has_page_via_singles_all(self):
        archive = self._make_archive()
        page = MagicMock()
        page.url = '/other/'
        archive.singles_all = [page]
        assert archive.has_page(page) is True

    def test_has_page_via_url_match(self):
        archive = self._make_archive(url='/section/docs/')
        page = MagicMock()
        page.url = '/section/docs/'
        archive.singles_all = []
        assert archive.has_page(page) is True

    def test_has_page_via_parents(self):
        archive = self._make_archive()
        page = MagicMock()
        page.url = '/other/'
        page.parents = [archive]
        archive.singles_all = []
        assert archive.has_page(page) is True

    def test_has_page_returns_false(self):
        archive = self._make_archive(url='/section/docs/')
        page = MagicMock()
        page.url = '/other/'
        page.parents = []
        archive.singles_all = []
        assert archive.has_page(page) is False

    def test_has_page_no_parents_attribute(self):
        archive = self._make_archive(url='/section/docs/')
        page = MagicMock(spec=[])
        page.url = '/other/'
        archive.singles_all = []
        assert archive.has_page(page) is False
