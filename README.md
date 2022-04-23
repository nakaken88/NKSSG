# NKSSG
NakaKen Static Site Generator  
(This is still alpha ver.)
[日本語のドキュメントはこちら](https://nkssg.nakaken88.com/ja/)


## Install

Install using pip in terminal:

```
pip install -U git+https://github.com/nakaken88/NKSSG
```

## A Simple Example

```
nkssg new site
nkssg build
```

or

```
nkssg new site {site-name}
cd {site-name}
nkssg build
```

{site-name} is your site name.


## How to Use

### Local server

```
nkssg serve
```

### Add Post from Template

```
nkssg new post
```

The post template is under '/themes/default/new/new_post.html'. If you use markdown file, you can change the template file like below.

```
file: "post/%Y/%m/%Y%m%d-%H%M%S.md"
```

### Build Static Pages

```
nkssg build
```

Output will be in ./public/ folder.
