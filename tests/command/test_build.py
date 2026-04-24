import pytest
from unittest.mock import MagicMock, patch, ANY
from pathlib import Path

from nkssg.command.build import build, draft, serve, prepare_temp_dir, start_server
from nkssg.structure.config import Config


@pytest.fixture
def mock_config():
    config = MagicMock(spec=Config)
    mock_public_dir = MagicMock(spec=Path)
    mock_public_dir.exists.return_value = False
    config.public_dir = mock_public_dir
    config.site = MagicMock()
    config.docs_dir = Path('path/to/docs')
    config.themes_dir = MagicMock(spec=Path)
    config.themes_dir.exists.return_value = False
    return config


@patch('nkssg.command.build.Site')
@patch('nkssg.command.build.shutil')
def test_build_function_calls_site_methods_and_creates_public_dir(
    mock_shutil, MockSite, mock_config
):
    mock_site_instance = MockSite.return_value

    build(mock_config, clean=False)

    MockSite.assert_called_once_with(mock_config)
    mock_site_instance.setup.assert_called_once()
    mock_site_instance.update.assert_called_once()
    mock_site_instance.output.assert_called_once()

    mock_config.public_dir.mkdir.assert_called_once_with(exist_ok=True)
    mock_shutil.rmtree.assert_not_called()


@patch('nkssg.command.build.Site')
@patch('nkssg.command.build.shutil')
def test_build_function_cleans_public_dir_when_clean_is_true(
    mock_shutil, MockSite, mock_config
):
    mock_config.public_dir.exists.return_value = True
    mock_site_instance = MockSite.return_value

    build(mock_config, clean=True)

    mock_shutil.rmtree.assert_called_once_with(mock_config.public_dir)
    mock_config.public_dir.mkdir.assert_called_once_with(exist_ok=True)

    MockSite.assert_called_once_with(mock_config)
    mock_site_instance.setup.assert_called_once()
    mock_site_instance.update.assert_called_once()
    mock_site_instance.output.assert_called_once()


@patch('nkssg.command.build.Site')
@patch('nkssg.command.build.shutil')
def test_build_function_does_not_remove_public_dir_if_not_exists_and_clean_is_true(
    mock_shutil, MockSite, mock_config
):
    mock_config.public_dir.exists.return_value = False
    mock_site_instance = MockSite.return_value

    build(mock_config, clean=True)

    mock_shutil.rmtree.assert_not_called()
    mock_config.public_dir.mkdir.assert_called_once_with(exist_ok=True)

    MockSite.assert_called_once_with(mock_config)
    mock_site_instance.setup.assert_called_once()
    mock_site_instance.update.assert_called_once()
    mock_site_instance.output.assert_called_once()


@patch('nkssg.command.build.start_server')
@patch('nkssg.command.build.prepare_temp_dir')
def test_serve_calls_dependencies_and_watches_docs_dir(
    mock_prepare_temp_dir, mock_start_server, mock_config
):
    serve(mock_config, static=False, port=8000)

    assert mock_config.site.site_url == 'http://127.0.0.1:8000'
    mock_prepare_temp_dir.assert_called_once_with(mock_config)
    mock_start_server.assert_called_once_with(
        mock_config, [Path('path/to/docs')], 8000
    )


@patch('nkssg.command.build.start_server')
@patch('nkssg.command.build.prepare_temp_dir')
def test_serve_watches_nothing_when_static_is_true(
    mock_prepare_temp_dir, mock_start_server, mock_config
):
    serve(mock_config, static=True, port=8000)

    assert mock_config.site.site_url == 'http://127.0.0.1:8000'
    mock_prepare_temp_dir.assert_called_once_with(mock_config)
    mock_start_server.assert_called_once_with(mock_config, [], 8000)


@patch('nkssg.command.build.start_server')
@patch('nkssg.command.build.prepare_temp_dir')
def test_serve_watches_themes_dir_if_exists(
    mock_prepare_temp_dir, mock_start_server, mock_config
):
    mock_config.themes_dir.exists.return_value = True
    serve(mock_config, static=False, port=8000)

    assert mock_config.site.site_url == 'http://127.0.0.1:8000'
    mock_prepare_temp_dir.assert_called_once_with(mock_config)
    mock_start_server.assert_called_once_with(
        mock_config, [Path('path/to/docs'), mock_config.themes_dir], 8000
    )


@patch('nkssg.command.build.tempfile')
def test_prepare_temp_dir_creates_temp_dir_and_sets_config(
    mock_tempfile, mock_config
):
    mock_temp_dir = Path('/tmp/fake_temp_dir')
    mock_tempfile.mkdtemp.return_value = str(mock_temp_dir)

    prepare_temp_dir(mock_config)

    mock_tempfile.mkdtemp.assert_called_once_with(prefix='nkssg_')
    assert mock_config.public_dir == mock_temp_dir


@patch('nkssg.command.build.start_server')
@patch('nkssg.command.build.prepare_temp_dir')
def test_draft_with_relative_path(
    mock_prepare_temp_dir, mock_start_server, mock_config
):
    mock_config.base_dir = Path('/fake/base')
    draft_path = 'docs/draft.md'
    expected_abs_path = Path('/fake/base/docs/draft.md')

    mock_config.__getitem__.return_value = expected_abs_path

    draft(mock_config, draft_path, port=8001)

    mock_config.__setitem__.assert_called_with('draft_path', expected_abs_path)
    assert mock_config.site.site_url == 'http://127.0.0.1:8001'
    mock_prepare_temp_dir.assert_called_once_with(mock_config)
    mock_start_server.assert_called_once_with(
        mock_config, [expected_abs_path], 8001
    )


@patch('nkssg.command.build.start_server')
@patch('nkssg.command.build.prepare_temp_dir')
def test_draft_with_absolute_path(
    mock_prepare_temp_dir, mock_start_server, mock_config
):
    mock_config.base_dir = Path('/fake/base')
    draft_path = '/another/path/draft.md'
    expected_abs_path = Path(draft_path)

    mock_config.__getitem__.return_value = expected_abs_path

    draft(mock_config, draft_path, port=8002)

    mock_config.__setitem__.assert_called_with('draft_path', expected_abs_path)
    assert mock_config.site.site_url == 'http://127.0.0.1:8002'
    mock_prepare_temp_dir.assert_called_once_with(mock_config)
    mock_start_server.assert_called_once_with(
        mock_config, [expected_abs_path], 8002
    )


@patch('nkssg.command.build.build')
@patch('nkssg.command.build.shutil')
@patch('nkssg.command.build.Server')
def test_start_server_normal_flow(
    MockServer, mock_shutil, mock_build, mock_config
):
    mock_server_instance = MockServer.return_value
    watch_paths = [Path('/path/one'), Path('/path/two')]

    start_server(mock_config, watch_paths, port=8080)

    mock_build.assert_called_once_with(mock_config)

    MockServer.assert_called_once()
    assert mock_server_instance.watch.call_count == 2
    mock_server_instance.watch.assert_any_call(str(watch_paths[0]), ANY)
    mock_server_instance.watch.assert_any_call(str(watch_paths[1]), ANY)

    mock_server_instance.serve.assert_called_once_with(
        port=8080, root=mock_config.public_dir, open_url_delay=None
    )

    mock_shutil.rmtree.assert_called_once_with(mock_config.public_dir)


@patch('nkssg.command.build.build')
@patch('nkssg.command.build.shutil')
@patch('nkssg.command.build.Server')
def test_start_server_cleans_up_on_exception(
    MockServer, mock_shutil, mock_build, mock_config
):
    mock_server_instance = MockServer.return_value
    mock_server_instance.serve.side_effect = KeyboardInterrupt

    watch_paths = [Path('/path/one')]

    with pytest.raises(KeyboardInterrupt):
        start_server(mock_config, watch_paths, port=8080)

    mock_shutil.rmtree.assert_called_once_with(mock_config.public_dir)
