from pathlib import Path
import shutil
import pytest

from nkssg.structure.config import Config
from nkssg.structure.singles import Single


@pytest.fixture
def site_fixture(tmp_path):
    """
    Prepares a simple site fixture in a temporary directory with a markdown post
    and a basic theme for testing rendering.
    """
    # Define paths within the temporary directory
    site_dir = tmp_path / "test_site"
    docs_dir = site_dir / "docs"
    posts_dir = docs_dir / "post"
    themes_dir = site_dir / "themes"
    default_theme_dir = themes_dir / "default"
    public_dir = site_dir / "public"
    
    # Create directory structure
    posts_dir.mkdir(parents=True, exist_ok=True)
    default_theme_dir.mkdir(parents=True, exist_ok=True)
    public_dir.mkdir(exist_ok=True)

    # Create dummy nkssg.yml
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

    # Create markdown posts and pages
    (posts_dir / "my-test-post.md").write_text(
        """---
title: My Test Post Title
date: 2023-01-01
---
This is the **content** of my test post.
"""
    )
    (posts_dir / "first-post.md").touch() # Additional post
    (posts_dir / "_draft.md").touch() # Should be excluded
    
    pages_dir = docs_dir / "page"
    pages_dir.mkdir(parents=True, exist_ok=True)
    (pages_dir / "about.html").touch() # Page with .html extension
    (pages_dir / "notes.txt").touch() # Invalid extension, should be ignored

    # Create a simple single.html template
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
        # Initialize Config object
        config = Config.from_file(
            yaml_file_path=site_dir / 'nkssg.yml',
            mode='build',
            base_dir=site_dir
        )
        
        # Manually set directory paths for the Config object
        config.set_directory_path({
            'docs': 'docs',
            'public': 'public',
            'static': 'static',
            'themes': 'themes'
        })

        # Set doc_ext and exclude rules to match the original test_singles_initialization_and_collection intent
        config.doc_ext = ['md', 'html']
        config.exclude = ['**/_*']
        config.post_type.update({'post': {}, 'page': {}})

        yield config

    finally:
        # Restore original Single.docs_dir
        Single.docs_dir = original_single_docs_dir
        # Clean up the temporary directory if necessary (pytest handles tmp_path cleanup)

