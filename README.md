# Autism Guide

Autism Guide from the Farmhill Learning Community.

## Setup

Install the dependencies:

```
$ python -m pip install -r requirements.txt
```

## Build and Run

Build the website:

```
$ make build
```

Start a local server:

```
$ make serve
```

The site will be available at <http://localhost:8000>.

## Content Organization

All content lives under the `content/` directory.

### Resource

The primary content unit. A directory with `index.md` and optional numbered sub-pages or sections.

    content/overview-of-autism/
      index.md
      1-what-is-autism.md
      2-life-as-an-adult-autistic.md

URLs: `/overview-of-autism/`, `/overview-of-autism/what-is-autism/`

### Collection

A curated grouping of Resources. A single `.md` file in `content/collections/` with a `resources:` list in frontmatter.

    content/collections/resources-daily-living.md

URL: `/resources-daily-living/`

### Article

Standalone posts with optional date and author. Single `.md` files in `content/articles/`, sorted by date (newest first). Has an index page at `/articles/`.

    content/articles/some-article.md

URL: `/articles/some-article/`

### Simple Page

Standalone pages. Single `.md` files in `content/pages/`.

    content/pages/about.md

URL: `/about/`

### Configuration and Static Files

- `content/home.yml` — homepage layout (hero section, sections referencing collections)
- `content/site.yml` — site-wide config (title, navbar links, footer)
- `content/static/` — static assets (CSS, JS), copied as-is to `_site/static/`
- `content/images/`, `content/downloads/` — copied as-is to `_site/`

## Comments

Comments are enabled by self-hosted instance of Isso.

### Enabling comments

To enable comments on an article, please add the following at the beginning of the `qmd` file.

```
---
format:
  html:
    include-after-body:
       - "_includes/load-comments.html"
---
```

Only the articles that have this dire will have comments enabled.

### Moderating comments

To moderate comments, please login to:
<https://comments.farmhill.in/admin/>

## Tools

The resository has a script to resize images.

To use the tools, make sure you have all the dependencies installed. You can do that by running the following command:

```
$ python -m pip install -r requirements.txt
```

To resize an image:

```
$ python tools/resize-image.py --width 200 --height 200 --output images/goodhands.jpg original-images/goodhands.jpg
Original image path: images/mat_goodhands.jpg
Image size: (1280, 960)
File size: 108 KB
---
Saved the resized image to a.jpg
Image size: (400, 300)
File size: 19 KB
```