# NKSSG
NakaKen Static Site Generator  
(This is still alpha ver.)


## Install

Install using pip:

```
> pip install git+https://github.com/nakaken88/NKSSG
```

## A Simple Example

```
> nkssg new site
> nkssg new build
```

or

```
> nkssg new site {site-name}
> cd {site-name}
> nkssg new build
```


## How to Use

### Local server

```
> nkssg serve
```

### Add Post from Template

```
> nkssg new post
```

The post template is under '/themes/default/new/new_post.html'. If you use markdown file, you can change like below.

```
file: "post/%Y/%m/%Y%m%d-%H%M%S.md"
```



