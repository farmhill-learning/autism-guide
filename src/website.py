#!/usr/bin/env python3
"""
Website generator for Autism Bharat.
Generates index.html from Jinja2 templates by auto-discovering resources from content directories.
"""

from __future__ import annotations
import yaml
import re
import shutil
import sys
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
import markdown
from typing import Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

src_root = Path(__file__).parent
project_root = src_root.parent
content_root = project_root / "content"

jinja_env = Environment(
    loader=FileSystemLoader(str(src_root / 'templates')),
    autoescape=select_autoescape(['html', 'xml'])
)

def render_template(template_name, **kwargs):
    template = jinja_env.get_template(template_name)
    return template.render(**kwargs)

DEFAULT_IMAGE_URL = "/overview-of-autism/overview-of-autism.jpg"

class Website:
    def __init__(self):
        self.resources = self.load_resources()
        self._resources_dict = {r.name: r for r in self.resources}

        # Register resources_dict as a Jinja2 global so all templates can access it
        resources_dict = {r.name: {'title': r.title} for r in self.resources}
        jinja_env.globals['resources'] = resources_dict

        self.collections = self.load_collections()
        self._collections_dict = {c.name: c for c in self.collections}
        self.simple_pages = self.load_simple_pages()
        self.articles = self.load_articles()
        self._articles_dict = {a.name: a for a in self.articles}
        self.site_config = self.load_site_config()

        # Register site config as a Jinja2 global so all templates can access it
        jinja_env.globals['site'] = self.site_config

    def get_resource(self, name):
        return self._resources_dict[name]

    def get_collection(self, name):
        return self._collections_dict[name]

    def load_resources(self):
        resources = []
        for item in content_root.iterdir():
            if item.is_dir() and item.name != 'static':
                index_file = item / 'index.md'
                if index_file.exists():
                    resource = Resource.load(item)
                    resources.append(resource)
        return resources

    def load_collections(self):
        collections = []
        collections_dir = content_root / 'collections'
        if collections_dir.exists() and collections_dir.is_dir():
            for md_file in sorted(collections_dir.glob('*.md')):
                collection = Collection.load(self, md_file)
                collections.append(collection)
        return collections

    def load_simple_pages(self):
        """Load all simple pages from content/pages/ directory."""
        simple_pages = []
        pages_dir = content_root / 'pages'
        if pages_dir.exists() and pages_dir.is_dir():
            for md_file in sorted(pages_dir.glob('*.md')):
                simple_page = SimplePage.load(md_file)
                simple_pages.append(simple_page)
        return simple_pages

    def load_articles(self):
        """Load all articles from content/articles/ directory."""
        articles = []
        articles_dir = content_root / 'articles'
        if articles_dir.exists() and articles_dir.is_dir():
            for md_file in sorted(articles_dir.glob('*.md')):
                article = Article.load(md_file)
                articles.append(article)
        
        # Sort articles by date (newest first), then by filename if no date
        def sort_key(article):
            date_obj = article.date_obj
            if date_obj:
                # Use negative timestamp for descending order (newest first)
                return (-date_obj.timestamp(), '')
            else:
                # Articles without dates sorted alphabetically by filename
                return (float('inf'), article.name)
        
        articles.sort(key=sort_key)
        return articles

    def load_home(self):
        """Load home page configuration (sections and hero) from home.yml file."""
        home_file = content_root / 'home.yml'
        if not home_file.exists():
            return {'sections': [], 'hero': None}

        with open(home_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        if not data:
            return {'sections': [], 'hero': None}

        # Load sections
        sections = self.load_sections(data)

        # Load hero
        hero_data = data.get('hero')
        hero = None
        if hero_data:
            hero = {
                'title': hero_data.get('title', ''),
                'subtitle': hero_data.get('subtitle', ''),
                'actions': hero_data.get('actions', [])
            }

        return {'sections': sections, 'hero': hero}

    def load_sections(self, home_config):
        """Load sections from home configuration."""
        if not home_config:
            return []

        sections = []
        for section_data in home_config.get('sections', []):
            title = section_data.get('title', '')
            description = section_data.get('description', '')
            classname = section_data.get('classname', '')
            collection_names = section_data.get('collections', [])
            articles_count = section_data.get('articles_count', 0)

            # Convert collection names to Collection objects
            collections = []
            for collection_name in collection_names:
                try:
                    collection = self.get_collection(collection_name)
                    collections.append(collection)
                except KeyError:
                    print(f"Warning: Collection '{collection_name}' not found in section '{title}'", file=sys.stderr)

            # Get articles if requested
            articles = []
            if articles_count > 0:
                articles = self.articles[:articles_count]

            section = Section(
                title=title,
                description=description,
                classname=classname,
                collections=collections,
                articles=articles if articles else None
            )
            sections.append(section)

        return sections

    def load_site_config(self):
        """Load site configuration from site.yml file."""
        site_file = content_root / 'site.yml'

        # Default configuration matching current hardcoded values
        default_config = {
            'title': 'Autism Bharat',
            'navbar': {
                'links': [
                    {'label': 'Home', 'href': '/'}
                ]
            },
            'footer': {
                'copyright': '© 2024 Farmhill Learning | Licensed under Creative Commons',
                'sections': []
            }
        }

        if not site_file.exists():
            print(f"Warning: site.yml not found, using defaults", file=sys.stderr)
            return default_config

        try:
            with open(site_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not data:
                return default_config

            # Merge with defaults to ensure all keys exist
            config = default_config.copy()
            config.update(data)

            # Ensure nested structures exist
            if 'navbar' not in config or not isinstance(config['navbar'], dict):
                config['navbar'] = default_config['navbar']
            else:
                if 'links' not in config['navbar']:
                    config['navbar']['links'] = default_config['navbar']['links']

            if 'footer' not in config or not isinstance(config['footer'], dict):
                config['footer'] = default_config['footer']
            else:
                if 'copyright' not in config['footer']:
                    config['footer']['copyright'] = default_config['footer']['copyright']
                if 'sections' not in config['footer']:
                    config['footer']['sections'] = default_config['footer']['sections']

            return config

        except yaml.YAMLError as e:
            print(f"Warning: Error parsing site.yml: {e}, using defaults", file=sys.stderr)
            return default_config
        except Exception as e:
            print(f"Warning: Error loading site.yml: {e}, using defaults", file=sys.stderr)
            return default_config

    def render(self):
        self.render_static()
        self.render_home()
        for resource in self.resources:
            resource.render(self.resources)
        for collection in self.collections:
            collection.render()
        for simple_page in self.simple_pages:
            simple_page.render()
        self.render_articles()
        self.build_search_index()

    def render_static(self):
        self._copy_static_files("static")
        self._copy_static_files("images")
        self._copy_static_files("downloads")

    def _copy_static_files(self, dirname):
        static_dir = content_root / dirname
        output_static_dir = project_root / '_site' / dirname

        if static_dir.exists():
            if output_static_dir.exists():
                shutil.rmtree(output_static_dir)
            shutil.copytree(static_dir, output_static_dir)
            print(f'{output_static_dir.relative_to(project_root)}/')
        else:
            output_static_dir.mkdir(parents=True, exist_ok=True)

    def render_home(self):
        home_data = self.load_home()
        output_file = project_root / '_site' / 'index.html'
        html_content = render_template(
            'index.html',
            sections=home_data['sections'],
            hero=home_data['hero'],
            articles=self.articles,
            site_title=self.site_config.get('title', 'Autism Bharat'),
            site_description=self.site_config.get('description', 'Resources and information about autism in India')
        )
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(output_file.relative_to(project_root))

    def render_articles(self):
        """Render article index page and all individual articles."""
        # Render article index page
        output_file = project_root / '_site' / 'articles' / 'index.html'
        html_content = render_template(
            'articles/index.html',
            articles=self.articles
        )
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(output_file.relative_to(project_root))

        # Render each individual article
        for article in self.articles:
            article.render()

    def build_search_index(self):
        """Build and save the search index."""
        from search import build_search_index
        output_path = project_root / '_site' / 'search.json'
        build_search_index(self.resources, self.articles, output_path)

@dataclass
class Resource:
    name: str
    title: str
    description: str
    pages: list[ResourcePage]

    @property
    def url(self):
        return "/" + self.name

    @property
    def root(self):
        return content_root / self.name

    @property
    def image_url(self):
        pages = self.pages
        if pages and pages[0].name == 'index':
            image = pages[0].metadata.get('image')
            if image:
                image_path = self.root / image
                return "/" + str(image_path.relative_to(content_root))
        return DEFAULT_IMAGE_URL

    @staticmethod
    def load(resource_dir):
        name = resource_dir.name

        # Find all .md files and sort them
        md_files = [f.name for f in sorted(resource_dir.glob('*.md')) if f.name != 'index.md']
        md_files = ["index.md"] + md_files

        pages = [ResourcePage.load(resource_dir / filename, resource_name=name) for filename in md_files]

        # Get title from index page
        title = name.replace('-', ' ').title()  # fallback
        description = ""
        if pages and pages[0].name == 'index':
            title = pages[0].title
            description = pages[0].metadata.get("description") or ""
        return Resource(name=name, title=title, description=description, pages=pages)

    def render(self, all_resources):
        self.copy_images()
        for page in self.pages:
            self.render_page(page)

    def copy_images(self):
        """Copy all .jpg and .png files from resource directory to output directory."""
        image_extensions = ['.jpg', '.jpeg', '.png']
        output_dir = project_root / '_site' / self.name

        for ext in image_extensions:
            # Check both lowercase and uppercase extensions for case-insensitive matching
            for pattern in [f'*{ext}', f'*{ext.upper()}']:
                for image_file in self.root.glob(pattern):
                    output_file = output_dir / image_file.name
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(image_file, output_file)
                    print(f'  {output_file.relative_to(project_root)}')

    def render_page(self, page: ResourcePage):
        rendered_html = render_template(
            'resource-page.html',
            page=page,
            resource=self
        )

        output_base_dir = project_root / '_site'
        if page.name == 'index':
            output_dir = output_base_dir / self.name
        else:
            output_dir = output_base_dir / self.name / page.name

        output_file = output_dir / 'index.html'
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        print(output_file.relative_to(project_root))

    def get_next_page(self, page: ResourcePage):
        try:
            index = self.pages.index(page)
            if index < len(self.pages) - 1:
                return self.pages[index + 1]
        except ValueError:
            pass
        return None

    def get_previous_page(self, page: ResourcePage):
        try:
            index = self.pages.index(page)
            if index > 0:
                return self.pages[index - 1]
        except ValueError:
            pass
        return None

@dataclass
class Section:
    title: str
    description: str
    classname: str
    collections: list[Collection]
    articles: Optional[list[Article]] = None


@dataclass
class Collection:
    name: str
    title: str
    body: str
    resources: list[Resource]
    metadata: dict[str, Any]

    @property
    def description(self):
        return self.metadata.get("description") or ""

    @property
    def image_url(self):
        if self.resources:
            return self.resources[0].image_url
        return DEFAULT_IMAGE_URL

    @staticmethod
    def load(website, markdown_file):
        with open(markdown_file, 'r', encoding='utf-8') as f:
            content = f.read()

        frontmatter_pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
        match = re.match(frontmatter_pattern, content, re.DOTALL)

        if match:
            frontmatter_yaml = match.group(1)
            markdown_content = match.group(2)
            try:
                metadata = yaml.safe_load(frontmatter_yaml) or {}
            except yaml.YAMLError:
                metadata = {}
        else:
            metadata = {}
            markdown_content = content

        page_name = markdown_file.stem
        title = metadata.get('title')

        # If no title in frontmatter, check if first line is a header
        if not title:
            lines = markdown_content.strip().split('\n')
            if lines and lines[0].strip().startswith('#'):
                title = lines[0].strip().lstrip('#').strip()
                markdown_content = '\n'.join(lines[1:]).strip()
            else:
                title = page_name.replace('-', ' ').title()

        resource_names = metadata.get('resources', [])
        if not isinstance(resource_names, list):
            resource_names = []

        # Get resource objects using website.get_resource
        resources = []
        for resource_name in resource_names:
            try:
                resource = website.get_resource(resource_name)
                resources.append(resource)
            except KeyError:
                print(f"Warning: Resource '{resource_name}' not found in collection '{page_name}'", file=sys.stderr)

        return Collection(
            name=page_name,
            title=title,
            body=markdown_content,
            resources=resources,
            metadata=metadata
        )

    def render(self):
        rendered_html = render_template(
            'collection.html',
            collection=self
        )

        output_dir = project_root / '_site' / self.name
        output_file = output_dir / 'index.html'
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        print(output_file.relative_to(project_root))

@dataclass
class ResourcePage:
    name: str
    title: str
    body: str
    metadata: dict[str,Any]
    resource_name: str = ""

    @property
    def description(self):
        return self.metadata.get('description-meta') or self.metadata.get("description") or ""

    @property
    def url(self):
        return self.get_url()

    def get_url(self) -> str:
        """Generate the URL path for this page."""
        if self.name == 'index':
            return f"/{self.resource_name}/"
        else:
            return f"/{self.resource_name}/{self.name}/"

    def get_searchable_text(self) -> str:
        """Extract plain text from markdown body for searching."""
        # Remove markdown syntax patterns
        text = self.body

        # Remove code blocks
        text = re.sub(r'```[\s\S]*?```', '', text)
        text = re.sub(r'`[^`]+`', '', text)

        # Remove links but keep text: [text](url) -> text
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

        # Remove images: ![alt](url) -> alt
        text = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'\1', text)

        # Remove headers but keep text: # Header -> Header
        text = re.sub(r'^#{1,6}\s+(.+)$', r'\1', text, flags=re.MULTILINE)

        # Remove bold/italic markers
        text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^\*]+)\*', r'\1', text)
        text = re.sub(r'__([^_]+)__', r'\1', text)
        text = re.sub(r'_([^_]+)_', r'\1', text)

        # Remove HTML tags if any
        text = re.sub(r'<[^>]+>', '', text)

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()

        return text

    def get_headings(self) -> list[str]:
        """Extract headings from markdown content."""
        headings = []
        lines = self.body.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('#'):
                # Extract heading text (remove # markers)
                heading = re.sub(r'^#+\s+', '', line).strip()
                if heading:
                    headings.append(heading)
        return headings

    @staticmethod
    def load(markdown_file, resource_name: str = ""):
        with open(markdown_file, 'r', encoding='utf-8') as f:
            content = f.read()

        frontmatter_pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
        match = re.match(frontmatter_pattern, content, re.DOTALL)

        if match:
            frontmatter_yaml = match.group(1)
            markdown_content = match.group(2)
            try:
                metadata = yaml.safe_load(frontmatter_yaml) or {}
            except yaml.YAMLError:
                metadata = {}
        else:
            metadata = {}
            markdown_content = content

        page_name = markdown_file.stem

        # replace number prefix from page name
        page_name = re.sub("^\d+-", "", page_name)

        title = metadata.get('title')

        # If no title in frontmatter, check if first line is a header
        if not title:
            lines = markdown_content.strip().split('\n')
            if lines and lines[0].strip().startswith('#'):
                # Extract title from first header line
                title = lines[0].strip().lstrip('#').strip()
                # Remove the first line from content
                markdown_content = '\n'.join(lines[1:]).strip()
            else:
                # Fallback to filename-based title
                title = page_name.replace('-', ' ').title()

        return ResourcePage(
            name=page_name,
            title=title,
            body=markdown_content,
            metadata=metadata,
            resource_name=resource_name
        )

@dataclass
class SimplePage:
    name: str
    title: str
    body: str
    metadata: dict[str, Any]

    @property
    def description(self):
        return self.metadata.get('description-meta') or self.metadata.get("description") or ""

    @property
    def url(self):
        return f"/{self.name}/"

    def get_url(self) -> str:
        """Generate the URL path for this page."""
        return f"/{self.name}/"

    def get_searchable_text(self) -> str:
        """Extract plain text from markdown body for searching."""
        # Remove markdown syntax patterns
        text = self.body

        # Remove code blocks
        text = re.sub(r'```[\s\S]*?```', '', text)
        text = re.sub(r'`[^`]+`', '', text)

        # Remove links but keep text: [text](url) -> text
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

        # Remove images: ![alt](url) -> alt
        text = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'\1', text)

        # Remove headers but keep text: # Header -> Header
        text = re.sub(r'^#{1,6}\s+(.+)$', r'\1', text, flags=re.MULTILINE)

        # Remove bold/italic markers
        text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^\*]+)\*', r'\1', text)
        text = re.sub(r'__([^_]+)__', r'\1', text)
        text = re.sub(r'_([^_]+)_', r'\1', text)

        # Remove HTML tags if any
        text = re.sub(r'<[^>]+>', '', text)

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()

        return text

    def get_headings(self) -> list[str]:
        """Extract headings from markdown content."""
        headings = []
        lines = self.body.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('#'):
                # Extract heading text (remove # markers)
                heading = re.sub(r'^#+\s+', '', line).strip()
                if heading:
                    headings.append(heading)
        return headings

    def render(self):
        """Render this simple page to HTML file."""
        rendered_html = render_template(
            'simple-page.html',
            page=self
        )

        output_dir = project_root / '_site' / self.name
        output_file = output_dir / 'index.html'
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        print(output_file.relative_to(project_root))

    @staticmethod
    def load(markdown_file):
        """Load a simple page from a markdown file."""
        with open(markdown_file, 'r', encoding='utf-8') as f:
            content = f.read()

        frontmatter_pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
        match = re.match(frontmatter_pattern, content, re.DOTALL)

        if match:
            frontmatter_yaml = match.group(1)
            markdown_content = match.group(2)
            try:
                metadata = yaml.safe_load(frontmatter_yaml) or {}
            except yaml.YAMLError:
                metadata = {}
        else:
            metadata = {}
            markdown_content = content

        page_name = markdown_file.stem

        # replace number prefix from page name
        page_name = re.sub("^\d+-", "", page_name)

        title = metadata.get('title')

        # If no title in frontmatter, check if first line is a header
        if not title:
            lines = markdown_content.strip().split('\n')
            if lines and lines[0].strip().startswith('#'):
                # Extract title from first header line
                title = lines[0].strip().lstrip('#').strip()
                # Remove the first line from content
                markdown_content = '\n'.join(lines[1:]).strip()
            else:
                # Fallback to filename-based title
                title = page_name.replace('-', ' ').title()

        return SimplePage(
            name=page_name,
            title=title,
            body=markdown_content,
            metadata=metadata
        )

@dataclass
class Article:
    name: str
    title: str
    body: str
    metadata: dict[str, Any]

    @property
    def description(self):
        return self.metadata.get('description') or ""

    @property
    def author(self):
        return self.metadata.get('author') or None

    @property
    def date(self):
        """Return date as string from metadata, or None if not available."""
        return self.metadata.get('date') or None

    @property
    def date_obj(self):
        """Return date as datetime object if available, None otherwise."""
        date_str = self.date
        if not date_str:
            return None
        
        # Try to parse common date formats
        date_formats = ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d']
        for fmt in date_formats:
            try:
                return datetime.strptime(str(date_str), fmt)
            except (ValueError, TypeError):
                continue
        
        # If parsing fails, log warning and return None
        print(f"Warning: Could not parse date '{date_str}' for article '{self.name}'", file=sys.stderr)
        return None

    @property
    def url(self):
        return f"/articles/{self.name}/"

    def get_url(self) -> str:
        """Generate the URL path for this article."""
        return f"/articles/{self.name}/"

    def get_searchable_text(self) -> str:
        """Extract plain text from markdown body for searching."""
        # Remove markdown syntax patterns
        text = self.body

        # Remove code blocks
        text = re.sub(r'```[\s\S]*?```', '', text)
        text = re.sub(r'`[^`]+`', '', text)

        # Remove links but keep text: [text](url) -> text
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

        # Remove images: ![alt](url) -> alt
        text = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'\1', text)

        # Remove headers but keep text: # Header -> Header
        text = re.sub(r'^#{1,6}\s+(.+)$', r'\1', text, flags=re.MULTILINE)

        # Remove bold/italic markers
        text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^\*]+)\*', r'\1', text)
        text = re.sub(r'__([^_]+)__', r'\1', text)
        text = re.sub(r'_([^_]+)_', r'\1', text)

        # Remove HTML tags if any
        text = re.sub(r'<[^>]+>', '', text)

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()

        return text

    def get_headings(self) -> list[str]:
        """Extract headings from markdown content."""
        headings = []
        lines = self.body.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('#'):
                # Extract heading text (remove # markers)
                heading = re.sub(r'^#+\s+', '', line).strip()
                if heading:
                    headings.append(heading)
        return headings

    def render(self):
        """Render this article to HTML file."""
        rendered_html = render_template(
            'articles/article.html',
            article=self
        )

        output_dir = project_root / '_site' / 'articles' / self.name
        output_file = output_dir / 'index.html'
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        print(output_file.relative_to(project_root))

    @staticmethod
    def load(markdown_file):
        """Load an article from a markdown file."""
        with open(markdown_file, 'r', encoding='utf-8') as f:
            content = f.read()

        frontmatter_pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
        match = re.match(frontmatter_pattern, content, re.DOTALL)

        if match:
            frontmatter_yaml = match.group(1)
            markdown_content = match.group(2)
            try:
                metadata = yaml.safe_load(frontmatter_yaml) or {}
            except yaml.YAMLError:
                metadata = {}
        else:
            metadata = {}
            markdown_content = content

        page_name = markdown_file.stem

        # Extract title from frontmatter, first H1, or filename
        title = metadata.get('title')
        if not title:
            lines = markdown_content.strip().split('\n')
            if lines and lines[0].strip().startswith('#'):
                # Extract title from first header line
                title = lines[0].strip().lstrip('#').strip()
                # Remove the first line from content
                markdown_content = '\n'.join(lines[1:]).strip()
            else:
                # Fallback to filename-based title
                title = page_name.replace('-', ' ').title()

        # Parse date if available
        if 'date' in metadata and metadata['date']:
            date_str = str(metadata['date'])
            # Try to parse and validate date format
            date_formats = ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d']
            parsed = False
            for fmt in date_formats:
                try:
                    datetime.strptime(date_str, fmt)
                    parsed = True
                    break
                except (ValueError, TypeError):
                    continue
            if not parsed:
                print(f"Warning: Invalid date format '{date_str}' for article '{page_name}', treating as no date", file=sys.stderr)
                metadata['date'] = None

        return Article(
            name=page_name,
            title=title,
            body=markdown_content,
            metadata=metadata
        )

def load_resources(resources_file):
    with open(resources_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data.get('resources', {}) if data else {}


def setup_jinja_environment(templates_dir):
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(['html', 'xml'])
    )
    return env


def parse_markdown_file(markdown_file):
    with open(markdown_file, 'r', encoding='utf-8') as f:
        content = f.read()

    frontmatter_pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
    match = re.match(frontmatter_pattern, content, re.DOTALL)

    if match:
        frontmatter_yaml = match.group(1)
        markdown_content = match.group(2)
        try:
            frontmatter = yaml.safe_load(frontmatter_yaml) or {}
        except yaml.YAMLError:
            frontmatter = {}
    else:
        frontmatter = {}
        markdown_content = content

    return frontmatter, markdown_content


def convert_markdown_to_html(markdown_content):
    from md import VideoExtension, DownloadThisExtension
    md = markdown.Markdown(extensions=['extra', 'codehilite', 'toc', VideoExtension(), DownloadThisExtension()])
    return md.convert(markdown_content)

def to_markdown(markdown_content):
    """Convert markdown content to HTML."""
    return convert_markdown_to_html(markdown_content)

# Register to_markdown as a global function in Jinja environment
jinja_env.globals['to_markdown'] = to_markdown

def main():
    website = Website()
    website.render()

if __name__ == '__main__':
    main()
