from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from nkssg.__main__ import cli


@patch('nkssg.__main__.build')
@patch('nkssg.__main__.Config')
def test_cli_build_command(MockConfig, mock_build_module, tmp_path):
    """
    Tests that the `build` command calls the underlying build function
    without the --clean flag.
    """
    mock_config_instance = MagicMock()
    MockConfig.from_file.return_value = mock_config_instance

    runner = CliRunner()

    result = runner.invoke(cli, ['build'])

    assert result.exit_code == 0, result.output
    MockConfig.from_file.assert_called_once_with(mode='build')
    mock_build_module.build.assert_called_once_with(mock_config_instance, False)


@patch('nkssg.__main__.build')
@patch('nkssg.__main__.Config')
def test_cli_build_command_with_clean_flag(MockConfig, mock_build_module, tmp_path):
    """
    Tests that the `build` command calls the underlying build function
    with the --clean flag.
    """
    mock_config_instance = MagicMock()
    MockConfig.from_file.return_value = mock_config_instance

    runner = CliRunner()

    result = runner.invoke(cli, ['build', '--clean'])

    assert result.exit_code == 0, result.output
    MockConfig.from_file.assert_called_once_with(mode='build')
    mock_build_module.build.assert_called_once_with(mock_config_instance, True)


@patch('nkssg.__main__.build')
@patch('nkssg.__main__.Config')
def test_cli_build_command_with_short_clean_flag(MockConfig, mock_build_module, tmp_path):
    """
    Tests that the `build` command works with the short -c flag for --clean.
    """
    mock_config_instance = MagicMock()
    MockConfig.from_file.return_value = mock_config_instance

    runner = CliRunner()

    result = runner.invoke(cli, ['build', '-c'])

    assert result.exit_code == 0, result.output
    MockConfig.from_file.assert_called_once_with(mode='build')
    mock_build_module.build.assert_called_once_with(mock_config_instance, True)


@patch('nkssg.__main__.build')
@patch('nkssg.__main__.Config')
def test_cli_serve_command_defaults(MockConfig, mock_build_module):
    """Tests the `serve` command with default options."""

    mock_config_instance = MagicMock()
    MockConfig.from_file.return_value = mock_config_instance
    runner = CliRunner()

    result = runner.invoke(cli, ['serve'])

    assert result.exit_code == 0, result.output
    MockConfig.from_file.assert_called_once_with(mode='serve')
    mock_build_module.serve.assert_called_once_with(mock_config_instance, False, 5500)
    # For default, __setitem__ is called with False
    mock_config_instance.__setitem__.assert_called_once_with('serve_all', False)


@patch('nkssg.__main__.build')
@patch('nkssg.__main__.Config')
def test_cli_serve_command_with_all_options(MockConfig, mock_build_module):
    """Tests the `serve` command with all options specified."""
    mock_config_instance = MagicMock()
    MockConfig.from_file.return_value = mock_config_instance
    runner = CliRunner()

    result = runner.invoke(cli, ['serve', '--static', '--all', '--port', '8000'])

    assert result.exit_code == 0, result.output
    MockConfig.from_file.assert_called_once_with(mode='serve')
    mock_build_module.serve.assert_called_once_with(mock_config_instance, True, 8000)
    mock_config_instance.__setitem__.assert_called_once_with('serve_all', True)


@patch('nkssg.__main__.build')
@patch('nkssg.__main__.Config')
def test_cli_serve_command_with_short_options(MockConfig, mock_build_module):
    """Tests the `serve` command with short form options."""
    mock_config_instance = MagicMock()
    MockConfig.from_file.return_value = mock_config_instance
    runner = CliRunner()

    result = runner.invoke(cli, ['serve', '-s', '-a', '-p', '8000'])

    assert result.exit_code == 0, result.output
    MockConfig.from_file.assert_called_once_with(mode='serve')
    mock_build_module.serve.assert_called_once_with(mock_config_instance, True, 8000)
    mock_config_instance.__setitem__.assert_called_once_with('serve_all', True)


@patch('nkssg.__main__.build')
@patch('nkssg.__main__.Config')
def test_cli_draft_command_with_path(MockConfig, mock_build_module):
    """Tests the `draft` command with a required path argument."""
    mock_config_instance = MagicMock()
    MockConfig.from_file.return_value = mock_config_instance
    runner = CliRunner()
    test_path = 'some/draft/post.md'

    result = runner.invoke(cli, ['draft', test_path])

    assert result.exit_code == 0, result.output
    MockConfig.from_file.assert_called_once_with(mode='draft')
    mock_build_module.draft.assert_called_once_with(mock_config_instance, test_path, 5500)


@patch('nkssg.__main__.build')
@patch('nkssg.__main__.Config')
def test_cli_draft_command_with_port_option(MockConfig, mock_build_module):
    """Tests the `draft` command with a specified port."""
    mock_config_instance = MagicMock()
    MockConfig.from_file.return_value = mock_config_instance
    runner = CliRunner()
    test_path = 'some/draft/post.md'

    result = runner.invoke(cli, ['draft', test_path, '--port', '9000'])

    assert result.exit_code == 0, result.output
    MockConfig.from_file.assert_called_once_with(mode='draft')
    mock_build_module.draft.assert_called_once_with(mock_config_instance, test_path, 9000)


@patch('nkssg.__main__.new')
def test_cli_new_site_command(mock_new_module):
    """Tests the `new site` command."""
    runner = CliRunner()
    test_path = 'my-new-site'

    result = runner.invoke(cli, ['new', 'site', test_path])

    assert result.exit_code == 0, result.output
    mock_new_module.site.assert_called_once_with(test_path)


@patch('nkssg.__main__.new')
@patch('nkssg.__main__.Config')
def test_cli_new_page_command(MockConfig, mock_new_module):
    """Tests the `new <name>` command for creating pages."""
    mock_config_instance = MagicMock()
    MockConfig.from_file.return_value = mock_config_instance
    runner = CliRunner()
    page_name = 'my-new-page'
    page_path = 'content/posts'

    result = runner.invoke(cli, ['new', page_name, page_path])

    assert result.exit_code == 0, result.output
    MockConfig.from_file.assert_called_once_with(mode='new')
    mock_new_module.page.assert_called_once_with(page_name, page_path, mock_config_instance)


def test_cli_draft_command_missing_path_argument_fails():
    """
    Tests that the `draft` command fails when the required path argument is missing.
    """
    runner = CliRunner()
    result = runner.invoke(cli, ['draft'])

    assert result.exit_code != 0
    assert "Error: Missing argument 'PATH'." in result.output

