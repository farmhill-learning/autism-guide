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
from typing import Any
from dataclasses import dataclass

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
        self.sections = self.load_sections()

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

    def load_sections(self):
        home_file = content_root / 'home.yml'
        if not home_file.exists():
            return []

        with open(home_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        if not data:
            return []

        sections = []
        for section_data in data.get('sections', []):
            title = section_data.get('title', '')
            description = section_data.get('description', '')
            classname = section_data.get('classname', '')
            collection_names = section_data.get('collections', [])

            # Convert collection names to Collection objects
            collections = []
            for collection_name in collection_names:
                try:
                    collection = self.get_collection(collection_name)
                    collections.append(collection)
                except KeyError:
                    print(f"Warning: Collection '{collection_name}' not found in section '{title}'", file=sys.stderr)

            section = Section(
                title=title,
                description=description,
                classname=classname,
                collections=collections
            )
            sections.append(section)

        return sections

    def render(self):
        self.render_static()
        self.render_home()
        for resource in self.resources:
            resource.render(self.resources)
        for collection in self.collections:
            collection.render()
        self.build_search_index()

    def render_static(self):
        static_dir = content_root / 'static'
        output_static_dir = project_root / '_site' / 'static'

        if static_dir.exists():
            if output_static_dir.exists():
                shutil.rmtree(output_static_dir)
            shutil.copytree(static_dir, output_static_dir)
            print(f'{output_static_dir.relative_to(project_root)}/')
        else:
            output_static_dir.mkdir(parents=True, exist_ok=True)

    def render_home(self):
        output_file = project_root / '_site' / 'index.html'
        html_content = render_template(
            'index.html',
            sections=self.sections,
            site_title="Autism Bharat",
            site_description="Resources and information about autism in India"
        )
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(output_file.relative_to(project_root))

    def build_search_index(self):
        """Build and save the search index."""
        from search import build_search_index
        output_path = project_root / '_site' / 'search.json'
        build_search_index(self.resources, output_path)

@dataclass
class Resource:
    name: str
    title: str
    description: str
    pages: list[Page]

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

        pages = [Page.load(resource_dir / filename, resource_name=name) for filename in md_files]

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

    def render_page(self, page: Page):
        rendered_html = render_template(
            'page.html',
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

    def get_next_page(self, page: Page):
        try:
            index = self.pages.index(page)
            if index < len(self.pages) - 1:
                return self.pages[index + 1]
        except ValueError:
            pass
        return None

    def get_previous_page(self, page: Page):
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
class Page:
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

        return Page(
            name=page_name,
            title=title,
            body=markdown_content,
            metadata=metadata,
            resource_name=resource_name
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
    from md import VideoExtension
    md = markdown.Markdown(extensions=['extra', 'codehilite', 'toc', VideoExtension()])
    return md.convert(markdown_content)

def to_markdown(markdown_content):
    """Convert markdown content to HTML."""
    return convert_markdown_to_html(markdown_content)

# Register to_markdown as a global function in Jinja environment
jinja_env.globals['to_markdown'] = to_markdown


def generate_page_html(env, markdown_file, resource_key, resource_title, output_dir, resources):
    frontmatter, markdown_content = parse_markdown_file(markdown_file)
    html_content = convert_markdown_to_html(markdown_content)

    page_name = markdown_file.stem
    page_title = frontmatter.get('title', page_name.replace('-', ' ').title())
    page_description = frontmatter.get('description-meta') or frontmatter.get('description')

    template = env.get_template('page.html')
    rendered_html = template.render(
        page_title=page_title,
        page_description=page_description,
        content=html_content,
        resource_key=resource_key,
        resource_title=resource_title,
        resources=resources
    )

    output_file = output_dir / 'index.html'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(rendered_html)

    print(output_file.relative_to(project_root))


def generate_all_pages(env, resources, resources_dir, output_base_dir):
    for resource_key, resource_data in resources.items():
        resource_title = resource_data.get('title', resource_key)
        pages = resource_data.get('pages', [])

        for page_file in pages:
            markdown_file = resources_dir / resource_key / page_file

            if not markdown_file.exists():
                continue

            page_name = Path(page_file).stem
            if page_file == 'index.md':
                output_dir = output_base_dir / resource_key
            else:
                output_dir = output_base_dir / resource_key / page_name

            generate_page_html(env, markdown_file, resource_key, resource_title, output_dir, resources)


def generate_index_html(env, resources, output_file):
    template = env.get_template('index.html')
    html_content = template.render(
        resources=resources,
        site_title="Autism Bharat",
        site_description="Resources and information about autism in India"
    )

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(output_file.relative_to(project_root))


def main():
    website = Website()
    website.render()

if __name__ == '__main__':
    main()
