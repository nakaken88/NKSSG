from pathlib import Path
import shutil
import pytest

from nkssg.structure.config import Config
from nkssg.structure.singles import Single


@pytest.fixture
def site_fixture(tmp_path):
    site_dir = tmp_path / "test_site"
    docs_dir = site_dir / "docs"
    posts_dir = docs_dir / "post"
    themes_dir = site_dir / "themes"
    default_theme_dir = themes_dir / "default"
    public_dir = site_dir / "public"

    posts_dir.mkdir(parents=True, exist_ok=True)
    default_theme_dir.mkdir(parents=True, exist_ok=True)
    public_dir.mkdir(exist_ok=True)

    (site_dir / "nkssg.yml").write_text(
        """site:
  site_name: 'Test Site'
theme:
  name: 'default'
post_type:
  post:
    permalink: /{slug}/
"""
    )

    (posts_dir / "my-test-post.md").write_text(
        """---
title: My Test Post Title
date: 2023-01-01
---
This is the **content** of my test post.
"""
    )
    (posts_dir / "first-post.md").touch()
    (posts_dir / "_draft.md").touch()  # Should be excluded

    pages_dir = docs_dir / "page"
    pages_dir.mkdir(parents=True, exist_ok=True)
    (pages_dir / "about.html").touch()
    (pages_dir / "notes.txt").touch()

    (default_theme_dir / "single.html").write_text(
        """<!DOCTYPE html>
<html>
<head>
    <title>{{ mypage.title }}</title>
</head>
<body>
    <h1>{{ mypage.title }}</h1>
    <div class="content">
        {{ mypage.content }}
    </div>
</body>
</html>"""
    )

    # Temporarily set Single.docs_dir for correct path resolution in Single.__init__
    original_single_docs_dir = Single.docs_dir
    Single.docs_dir = site_dir / 'docs'

    try:
        config = Config.from_file(
            yaml_file_path=site_dir / 'nkssg.yml',
            mode='build',
            base_dir=site_dir
        )

        config.set_directory_path({
            'docs': 'docs',
            'public': 'public',
            'static': 'static',
            'themes': 'themes'
        })

        config.doc_ext = ['md', 'html']
        config.exclude = ['**/_*']
        config.post_type.update({'post': {}, 'page': {}})

        yield config

    finally:
        Single.docs_dir = original_single_docs_dir
