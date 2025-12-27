#!/usr/bin/env python3
"""
Search index builder for Autism Bharat website.
Generates a JSON search index from all pages.
"""

import json
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from website import Page, Resource

# Import project_root at runtime to avoid circular import
from website import project_root


class SearchIndexBuilder:
    """Builds a search index from all resources and pages."""
    
    def __init__(self, resources):
        self.resources = resources
        self.index_data = {"pages": []}
    
    def build_index(self):
        """Build the search index from all resources."""
        for resource in self.resources:
            for page in resource.pages:
                page_entry = self._extract_page_data(page, resource)
                self.index_data["pages"].append(page_entry)
    
    def _extract_page_data(self, page, resource):
        """Extract searchable data from a page."""
        description = page.metadata.get('description-meta') or page.metadata.get('description') or ""
        
        return {
            "title": page.title,
            "url": page.get_url(),
            "description": description,
            "resource": resource.title,
            "resource_key": resource.name,
            "content": page.get_searchable_text(),
            "headings": page.get_headings()
        }
    
    def save_index(self, output_path: Path):
        """Save the search index to a JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.index_data, f, indent=2, ensure_ascii=False)
        print(f'Search index: {output_path.relative_to(project_root)}')


def build_search_index(resources, output_path):
    """Build and save the search index."""
    builder = SearchIndexBuilder(resources)
    builder.build_index()
    builder.save_index(output_path)
