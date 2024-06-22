import logging
from pathlib import Path
import shutil

from nkssg.config import Config
from nkssg.structure.themes import Themes


log = logging.getLogger(__name__)


def site(project_dir, package_dir: Path):

    project_dir = Path(project_dir)

    if project_dir.is_absolute():
        log.error('Please provide a relative path for the project directory.')
        return

    base_dir = Path.cwd()
    project_dir = base_dir / project_dir
    config_path = project_dir / 'nkssg.yml'

    if config_path.exists():
        log.warning('Project already exists.')
        return

    directories_to_create = [
        project_dir / 'docs' / 'post',
        project_dir / 'docs' / 'page',
        project_dir / 'public',
        project_dir / 'static',
    ]

    for directory in directories_to_create:
        directory.mkdir(parents=True, exist_ok=True)

    theme_from = package_dir / 'themes'
    theme_to = project_dir / 'themes'
    theme_copy(theme_from, theme_to)

    sample_post_from = Path(package_dir.parent, 'docs', 'post', 'sample.md')
    sample_post_to = Path(project_dir, 'docs', 'post', 'sample.md')
    shutil.copyfile(sample_post_from, sample_post_to)

    original_config_path = package_dir.parent / 'nkssg.yml'
    shutil.copyfile(original_config_path, config_path)


def theme_copy(theme_from: Path, theme_to: Path):
    for f in theme_from.glob('**/*'):
        if f.is_file() and f.suffix != '.py':
            rel_path = f.relative_to(theme_from)
            to_path = theme_to / rel_path
            to_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(f, to_path)


def page(name, path, config: Config):

    themes = Themes(config)
    search_list = [f'new_{name}.html']
    template_file = themes.lookup_template(search_list, full_path=True)

    if not template_file:
        log.warning(f'new_{name}.html is not found')
        return

    with open(template_file, 'r', encoding='UTF-8') as f:
        doc = f.read()

    old_lines = doc.split('\n')
    new_lines = []
    filename = config.now.strftime(r'%Y%m%d-%H%M%S.html')
    to_path = config.docs_dir / name / filename

    dash_count = 0
    for i, line in enumerate(old_lines):
        if i == 0 and line.strip() != '---':
            new_lines = old_lines
            break

        if line.strip() == '---':
            dash_count += 1

        if dash_count == 1 and line.strip().startswith('#'):
            line = line.replace(r'{path}', path)

            if '%' in line:
                line = config.now.strftime(line)

            if line.startswith('file:'):
                file_path = line[len('file:'):].strip()
                file_path = file_path.strip('/').strip('\\')
                file_path = file_path.strip('"').strip("'")
                to_path = config.docs_dir / file_path
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    to_path.parent.mkdir(parents=True, exist_ok=True)

    with open(to_path, mode='w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))

    print(f'{to_path} is created!')
