import os
from pathlib import Path
import shutil
from click.testing import CliRunner

from nkssg.__main__ import cli

# Path to the fixture site used for testing 'new page'
FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "simple_site"


def test_new_site_success():
    """
    Tests if `nkssg new site <sitename>` successfully creates a new site skeleton.
    """
    runner = CliRunner()
    with runner.isolated_filesystem() as temp_dir:
        result = runner.invoke(cli, ['new', 'site', 'my-test-site'])

        assert result.exit_code == 0
        assert not result.exception

        base_path = Path(temp_dir) / 'my-test-site'
        assert base_path.is_dir()
        assert (base_path / 'nkssg.yml').is_file()
        assert (base_path / 'docs').is_dir()
        assert (base_path / 'themes').is_dir()
        
        config_content = (base_path / 'nkssg.yml').read_text(encoding='utf-8')
        assert 'site_name: "my-test-site"' in config_content


def test_new_site_failure_if_exists():
    """
    Tests if `new site` safely fails when the target directory already exists.
    """
    runner = CliRunner()
    with runner.isolated_filesystem() as temp_dir:
        project_path = Path(temp_dir) / 'my-test-site'
        project_path.mkdir()
        (project_path / 'nkssg.yml').touch()

        result = runner.invoke(cli, ['new', 'site', 'my-test-site'])

        assert result.exit_code != 0
        assert result.exception
        assert "already exists" in result.output.lower()


def test_new_page_success():
    """
    Tests if `nkssg new post` creates a file according to the template.
    """
    runner = CliRunner()
    with runner.isolated_filesystem() as temp_dir:
        shutil.copytree(FIXTURE_PATH, temp_dir, dirs_exist_ok=True)
        
        os.chdir(temp_dir)
        result = runner.invoke(cli, ['new', 'post'])

        assert result.exit_code == 0
        assert not result.exception
        
        output_lines = result.output.strip().split('\n')
        created_path_str = output_lines[-1].removesuffix(' is created!')
        
        assert Path(created_path_str).is_file()