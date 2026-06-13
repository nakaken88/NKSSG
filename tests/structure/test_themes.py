import pytest
from unittest.mock import MagicMock
from pathlib import Path

import jinja2
import nkssg  # Needed for default theme path
from nkssg.structure.config import Config
from nkssg.structure.themes import FragmentCacheExtension, Themes


@pytest.fixture
def base_config(tmp_path):
    config = MagicMock(spec=Config)
    config.base_dir = tmp_path
    config.themes_dir = tmp_path / "themes"
    config.themes_dir.mkdir(exist_ok=True)
    config.theme = {}
    return config


@pytest.fixture
def create_theme_structure(tmp_path):
    def _creator(theme_name, config_content=None, parent=None, templates=None):
        theme_dir = tmp_path / "themes" / theme_name
        theme_dir.mkdir(parents=True, exist_ok=True)

        if config_content:
            (theme_dir / f"{theme_name}.yml").write_text(config_content)

        if templates:
            for template_path, template_content in templates.items():
                file_path = theme_dir / template_path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(template_content)
        return theme_dir
    return _creator


def test_init_no_themes_loads_default(base_config, create_theme_structure):
    # Ensure default theme exists for testing
    package_dir = Path(nkssg.__file__).parent
    default_theme_dir = package_dir / 'themes' / 'default'
    assert default_theme_dir.is_dir()

    themes = Themes(base_config)

    assert len(themes.dirs) == 1
    assert themes.dirs[0] == default_theme_dir
    assert 'default' in base_config.theme['name']
    assert base_config.theme['updated'] is True
    assert themes.cnf


def test_init_single_theme_loads_correctly(base_config, create_theme_structure):
    theme_name = "my_single_theme"
    create_theme_structure(
        theme_name,
        config_content="key: value",
        templates={'index.html': 'content'}
    )
    base_config.theme['name'] = theme_name

    themes = Themes(base_config)

    assert len(themes.dirs) == 1
    assert themes.dirs[0] == base_config.themes_dir / theme_name
    assert themes.cnf == {'key': 'value'}
    assert base_config.theme['updated'] is True


def test_init_child_theme_takes_priority_over_parent(
    base_config, create_theme_structure
):
    parent_theme = "parent_theme"
    child_theme = "child_theme"

    create_theme_structure(
        parent_theme,
        config_content="parent_key: parent_value\ncommon_key: parent_common",
        templates={'index.html': 'parent_index', 'style.css': 'parent_style'}
    )
    create_theme_structure(
        child_theme,
        config_content="child_key: child_value\ncommon_key: child_common",
        templates={'index.html': 'child_index', 'script.js': 'child_script'}
    )

    base_config.theme['name'] = parent_theme
    base_config.theme['child'] = child_theme

    themes = Themes(base_config)

    assert len(themes.dirs) == 2
    # Child theme directory should come first for lookup priority
    assert themes.dirs[0] == base_config.themes_dir / child_theme
    assert themes.dirs[1] == base_config.themes_dir / parent_theme

    # Config should be merged, child overriding parent
    expected_config = {
        'parent_key': 'parent_value',
        'child_key': 'child_value',
        'common_key': 'child_common'
    }
    assert themes.cnf == expected_config
    assert base_config.theme['updated'] is True


def test_load_theme_non_existent_theme_is_ignored(
    base_config, caplog, create_theme_structure
):
    base_config.theme['name'] = "non_existent_theme"

    themes = Themes(base_config)

    assert "non_existent_theme is not found" in caplog.text
    assert len(themes.dirs) == 1
    package_dir = Path(nkssg.__file__).parent
    default_theme_dir = package_dir / 'themes' / 'default'
    assert themes.dirs[0] == default_theme_dir
    assert 'name' in base_config.theme
    assert base_config.theme['updated'] is True


def test_load_theme_config_invalid_yaml(base_config, caplog, create_theme_structure):
    theme_name = "bad_config_theme"
    create_theme_structure(theme_name, config_content="key: { value")
    base_config.theme['name'] = theme_name

    themes = Themes(base_config)

    assert not themes.cnf
    assert "Failed to load config for bad_config_theme" in caplog.text


def test_load_theme_config_missing_yaml_no_warning(base_config, caplog, create_theme_structure):
    theme_name = "no_config_theme"
    create_theme_structure(theme_name, templates={'index.html': 'content'})
    base_config.theme['name'] = theme_name

    Themes(base_config)

    assert "no_config_theme" not in caplog.text


def test_lookup_template_exists_in_single_theme(base_config, create_theme_structure):
    theme_name = "test_theme"
    create_theme_structure(
        theme_name, templates={'layout/header.html': 'header_content'}
    )
    base_config.theme['name'] = theme_name

    themes = Themes(base_config)

    found_path = themes.lookup_template(['header.html'])
    assert found_path == 'layout/header.html'

    # falls back to the next item in the list if the first is not found
    found_path = themes.lookup_template(['non_existent.html', 'header.html'])
    assert found_path == 'layout/header.html'


def test_lookup_template_child_theme_priority(base_config, create_theme_structure):
    parent_theme = "parent_theme_lookup"
    child_theme = "child_theme_lookup"

    create_theme_structure(
        parent_theme,
        templates={'shared.html': 'parent_shared', 'specific_parent.html': 'content'}
    )
    create_theme_structure(
        child_theme,
        templates={'shared.html': 'child_shared', 'specific_child.html': 'content'}
    )

    base_config.theme['name'] = parent_theme
    base_config.theme['child'] = child_theme

    themes = Themes(base_config)

    found_path = themes.lookup_template(['shared.html'])
    # Should be from child due to priority
    assert found_path == 'shared.html'


def test_lookup_template_not_found(base_config, create_theme_structure):
    theme_name = "empty_theme"
    create_theme_structure(theme_name)
    base_config.theme['name'] = theme_name

    themes = Themes(base_config)

    found_path = themes.lookup_template(['non_existent_template.html'])
    assert found_path is None


def test_lookup_template_full_path(base_config, create_theme_structure):
    theme_name = "full_path_theme"
    theme_dir = create_theme_structure(
        theme_name, templates={'pages/home.html': 'home_content'}
    )
    base_config.theme['name'] = theme_name

    themes = Themes(base_config)

    found_path = themes.lookup_template(['home.html'], full_path=True)
    expected_path = str(theme_dir / 'pages' / 'home.html').replace('\\', '/')
    assert found_path == expected_path


class TestFragmentCacheExtension:

    @pytest.fixture
    def env(self):
        return jinja2.Environment(extensions=[FragmentCacheExtension])

    def test_block_is_evaluated_and_returned(self, env):
        template = env.from_string('{% cache "key" %}hello{% endcache %}')
        assert template.render() == 'hello'

    def test_block_evaluated_only_once(self, env):
        calls = []
        env.globals['record'] = lambda: calls.append(1) or ''
        template = env.from_string(
            '{% cache "key" %}{{ record() }}content{% endcache %}'
        )
        result1 = template.render()
        result2 = template.render()
        assert result1 == result2 == 'content'
        assert len(calls) == 1

    def test_different_keys_cached_separately(self, env):
        template = env.from_string(
            '{% cache "a" %}A{% endcache %}{% cache "b" %}B{% endcache %}'
        )
        assert template.render() == 'AB'
        assert env.fragment_cache['a'] == 'A'
        assert env.fragment_cache['b'] == 'B'


def test_build_shortcode_import_statement(base_config, create_theme_structure):
    theme_name = "shortcode_theme"
    create_theme_structure(
        theme_name,
        templates={
            'import/card.html': 'card content',
            'import/button.html': 'button content',
            'import/my-invalid.html': 'invalid alias',  # not a valid identifier
            'layout/base.html': 'base content',         # not in import/, excluded
        }
    )
    base_config.theme['name'] = theme_name

    themes = Themes(base_config)

    assert '{% import "import/card.html" as card %}' in themes.shortcode_import_statement
    assert '{% import "import/button.html" as button %}' in themes.shortcode_import_statement
    assert 'my-invalid' not in themes.shortcode_import_statement
    assert 'base' not in themes.shortcode_import_statement
