from pathlib import Path
import shutil
import os

from nkssg.command import build
from nkssg.structure.config import Config
from nkssg.structure.singles import Single


def test_build_simple_site(tmp_path):
    """
    シンプルなサイトが正しくビルドされることを検証するE2Eテスト。
    """
    original_docs_dir = Single.docs_dir
    try:
        Single.docs_dir = ''
        fixture_path = Path(__file__).parent / "fixtures" / "simple_site"
        shutil.copytree(fixture_path, tmp_path, dirs_exist_ok=True)

        original_cwd = Path.cwd()
        os.chdir(tmp_path)
        try:
            config = Config.from_file()
            config.base_dir = tmp_path
            config['mode'] = 'build'

            import nkssg
            pkg_dir = Path(nkssg.__file__).parent
            config['PKG_DIR'] = pkg_dir

            config.set_directory_path({
                'docs': 'docs',
                'public': 'public',
                'static': 'static',
                'themes': 'themes'
            })

            build.build(config, clean=True)
        finally:
            os.chdir(original_cwd)

        public_dir = tmp_path / "public"

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
    finally:
        Single.docs_dir = original_docs_dir