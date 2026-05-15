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

        # long_ids maps short IDs to hierarchical IDs
        short_cat2 = PurePath('/taxonomy', 'category', 'cat2')
        short_cat3 = PurePath('/taxonomy', 'category', 'cat3')
        assert archives.long_ids[short_cat2] == cat2_id
        assert archives.long_ids[short_cat3] == cat3_id

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
