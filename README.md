# NKSSG

NakaKen Static Site Generator (alpha)

[日本語のドキュメントはこちら](https://nkssg.nakaken88.com/ja/)


## Requirements

Python 3.10+


## Install

**Project-level (recommended):**

```
uv add git+https://github.com/nakaken88/NKSSG
```

Run with `uv run nkssg`, or activate the virtual environment first to use `nkssg` directly.

**Global install:**

```
uv tool install git+https://github.com/nakaken88/NKSSG
```

or using pip:

```
pip install git+https://github.com/nakaken88/NKSSG
```


## Quick Start

```
nkssg new site
nkssg build
```

or with a site name:

```
nkssg new site {site-name}
cd {site-name}
nkssg build
```


## Commands

### Build

```
nkssg build
```

Output will be in the `public/` folder.

### Local Server

```
nkssg serve
```

### Clean

```
nkssg clean
```

Removes the output directory and cache.

### Add Post from Template

```
nkssg new post
```

The post template is under `/themes/default/new/new_post.html`.
