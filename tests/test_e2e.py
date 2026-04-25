from pathlib import Path
import shutil

import pytest

from nkssg.command import build
from nkssg.structure.config import Config
from nkssg.structure.singles import Single


@pytest.fixture
def simple_site(tmp_path):
    fixture_source = Path(__file__).parent / "fixtures" / "simple_site"
    site_path = tmp_path / "test_site"
    shutil.copytree(fixture_source, site_path)
    return site_path


def test_build_simple_site(simple_site):
    original_docs_dir = Single.docs_dir
    try:
        Single.docs_dir = ''
        
        config = Config.from_file(
            yaml_file_path=simple_site / 'nkssg.yml',
            mode='build',
            base_dir=simple_site
        )

        config.set_directory_path({
            'docs': 'docs',
            'public': 'public',
            'static': 'static',
            'themes': 'themes'
        })

        build.build(config, clean=True)

        public_dir = simple_site / "public"

        assert public_dir.is_dir()

        post_path = public_dir / "posts" / "2023" / "01" / "my-first-post" / "index.html"
        assert post_path.is_file()
        post_content = post_path.read_text(encoding="utf-8")
        assert "My First Post" in post_content
        assert "This is the content of my <strong>first post</strong>." in post_content

        page_path = public_dir / "page" / "about-us" / "index.html"
        assert page_path.is_file()
        page_content = page_path.read_text(encoding="utf-8")
        assert "About Us" in page_content
        assert "This is the <strong>about</strong> page." in page_content

        assert "Test Site" in page_content

        page_archive_path = public_dir / "page" / "index.html"
        assert page_archive_path.is_file()
        page_archive_content = page_archive_path.read_text(encoding="utf-8")
        assert "About Us" in page_archive_content
    finally:
        Single.docs_dir = original_docs_dir