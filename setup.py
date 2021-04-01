from setuptools import setup, find_packages

setup(
    name='nkssg',
    version='0.0.1-alpha',
    description='NakaKen Static Site Generator',
    author='nakaken88',
    packages=find_packages(),
    include_package_data=True
    python_requires='>=3.6',
    install_requires=[
        'beautifulsoup4',
        'click',
        'Jinja2',
        'livereload',
        'Markdown',
        'ruamel.yaml',
        'tornado',
    ],
    extras_require={
        'develop': [
            'tox',
            'pytest'
        ]
    },
    entry_points={
        'console_scripts': [
            'nkssg=nkssg.__main__:cli',
        ],
        'nkssg.plugins': [
            'autop=nkssg.plugins.auto_p:AutoPPlugin',
            'awesome-page-link=nkssg.plugins.awesome_page_link:AwesomePageLinkPlugin',
            'awesome-img-link=nkssg.plugins.awesome_img_link:AwesomeImgLinkPlugin',
            'select-pages=nkssg.plugins.select_pages:SelectPagesPlugin',
        ],
    },
)