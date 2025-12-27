#!/usr/bin/env python3
"""
Website generator for Autism Bharat.
Generates index.html from Jinja2 templates and resources.yml configuration.
"""

from __future__ import annotations
import yaml
import re
import shutil
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


class Website:
    def __init__(self):
        self.resources = self.load_resources()
        self.home_data = self.load_home()

    def load_resources(self):
        resources_file = content_root / 'resources.yml'
        with open(resources_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        resources = []
        if data and 'resources' in data:
            for resource_name, resource_data in data['resources'].items():
                resource = Resource.load(resource_name, resource_data)
                resources.append(resource)
        return resources

    def load_home(self):
        home_file = content_root / 'home.yml'
        if home_file.exists():
            with open(home_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            return data.get('sections', []) if data else []
        return []

    def render(self):
        self.render_static()
        self.render_home()
        for resource in self.resources:
            resource.render(self.resources)
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
        resources_dict = {r.name: {'title': r.title} for r in self.resources}
        output_file = project_root / '_site' / 'index.html'
        html_content = render_template(
            'index.html',
            resources=resources_dict,
            items=self.home_data,
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
    pages: list[Page]

    @staticmethod
    def load(name, data):
        title = data.get('title', name)
        pages_data = data.get('pages', [])
        
        pages = []
        resources_dir = content_root / name
        for page_file in pages_data:
            markdown_file = resources_dir / page_file
            if markdown_file.exists():
                page = Page.load(markdown_file, resource_name=name)
                pages.append(page)
        
        return Resource(name=name, title=title, pages=pages)

    def render(self, all_resources):
        
        resources_dict = {r.name: {'title': r.title} for r in all_resources}
        
        for page in self.pages:
            self.render_page(page, resources_dict)

    def render_page(self, page: Page, resources_dict):
        html_content = convert_markdown_to_html(page.body)
        page_description = page.metadata.get('description-meta') or page.metadata.get('description')
        
        next_page = self.get_next_page(page)
        prev_page = self.get_previous_page(page)

        rendered_html = render_template(
            'page.html',
            page_title=page.title,
            page_description=page_description,
            content=html_content,
            resource_key=self.name,
            resource_title=self.title,
            resources=resources_dict,
            next_page=next_page,
            prev_page=prev_page
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
class Page:
    name: str
    title: str
    body: str
    metadata: dict[str,Any]
    resource_name: str = ""

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
