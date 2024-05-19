import logging
from pathlib import Path
import shutil

from nkssg.config import Config
from nkssg.structure.themes import Themes


log = logging.getLogger(__name__)


def site(project_dir, package_dir):

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
        project_dir / 'themes' / 'default',
        project_dir / 'themes' / 'child'
    ]

    for directory in directories_to_create:
        directory.mkdir(parents=True, exist_ok=True)

    for directory in ['default', 'child']:
        theme_from = package_dir / 'themes' / directory
        theme_to = project_dir / 'themes' / directory
        theme_copy(theme_from, theme_to)

    Path(project_dir, 'nkssg.yml').write_text('''\
site:
  site_name: "site name"
  site_url: ""
  site_desc: ""
  site_image: ""
  language: "en"

post_type:
  post:
    permalink: /%Y/%m/%d/%H%M%S/
    archive_type: "date"
  page:
    permalink: /{slug}/
    archive_type: "section"

markdown:
  fenced_code: {}
  toc:
    marker: "[toc]"

plugins:
  autop: {}
  awesome-img-link {}
  awesome-page-link:
    strip_paths:
      - /docs
  select-pages:
    start: 0
    step: 1

theme:
  name: default
  child: child

taxonomy:
  tag:
    term:
      - tag1
      - name: tag 2
        slug: tag2
      - tag3

  category:
    term:
      - cat1
      - name: cat11
        parent: cat1
      - name: cat12
        parent: cat1
      - name: cat2
        term:
          - name: cat21
          - name: cat22
          - cat23
''')

    Path(project_dir, 'docs', 'post', 'sample.md').write_text('''\
---
title: sample post
tag: ["tag1", "tag 2"]
category: ["cat11"]
---
This is a sample post.
''')


def theme_copy(theme_from: Path, theme_to: Path):
    for f in theme_from.glob('**/*'):
        if f.is_file():
            rel_path = f.relative_to(theme_from)
            to_path = theme_to / rel_path
            to_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(str(f), str(to_path))


def page(name, path, config: Config):

    config['themes'] = Themes(config)
    template_file = None

    for d in config['themes'].dirs:
        if template_file is not None:
            break
        for f in d.glob('**/*'):
            if template_file is not None:
                break
            if f.is_file() and f.stem == 'new_' + name:
                template_file = f

    if template_file is None:
        log.warning(name + ' is not found')
        return
    else:
        with open(template_file, 'r', encoding='UTF-8') as f:
            doc = f.read()

        now = config.now
        old_lines = doc.split('\n')
        new_lines = []
        to_path = ''

        dash_count = 0
        for i, line in enumerate(old_lines):
            if i == 0 and line != '---':
                new_lines = old_lines
                break

            if line == '---':
                dash_count = dash_count + 1

            if dash_count == 1 and line[0] != '#':
                parts = r'%Y %m %d %H %M %S'.split(' ')
                for part in parts:
                    if part in line:
                        line = line.replace(part, now.strftime(part))

                if r'{path}' in line:
                    line = line.replace(r'{path}', path)

                if line[:5] == 'file:':
                    value = line[5:].strip()
                    value = value.strip('/').strip('\\')
                    value = value.strip('"').strip("'")
                    to_path = Path(config['docs_dir'], value)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        if to_path == '':
            filename = now.strftime(r'%Y%m%d-%H%M%S.html')
            to_path = config['docs_dir'] / name / filename

        if str(to_path).startswith(str(to_path)):
            if not to_path.parent.exists():
                to_path.parent.mkdir(parents=True)

            with open(to_path, mode='w', encoding='utf-8') as f:
                f.write('\n'.join(new_lines))

            print(str(to_path) + ' is created!')

        else:
            log.warning('There is something wrong with the file setting.')
