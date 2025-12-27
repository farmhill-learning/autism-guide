"""
Custom markdown extensions for Autism Bharat website.
"""

import re
import markdown
from markdown.preprocessors import Preprocessor
from markdown.extensions import Extension


class VideoPreprocessor(Preprocessor):
    """Preprocessor to convert {{< video URL >}} to YouTube embed iframe."""
    
    pattern = r'\{\{<\s*video\s+([^\s>]+)\s*>\}\}'
    
    def run(self, lines):
        """Process lines and replace video shortcodes with iframe embeds."""
        new_lines = []
        for line in lines:
            match = re.search(self.pattern, line)
            if match:
                url = match.group(1)
                # Extract video ID from YouTube embed URL or regular YouTube URL
                video_id = self.extract_video_id(url)
                if video_id:
                    # Replace the shortcode with an iframe
                    iframe = f'<div class="video-container" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; margin: 2rem 0;"><iframe style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;" src="https://www.youtube.com/embed/{video_id}" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe></div>'
                    # Replace the entire line or just the shortcode
                    line = re.sub(self.pattern, iframe, line)
            new_lines.append(line)
        return new_lines
    
    def extract_video_id(self, url):
        """Extract YouTube video ID from various URL formats."""
        # Handle embed URLs: https://www.youtube.com/embed/VIDEO_ID
        embed_match = re.search(r'youtube\.com/embed/([a-zA-Z0-9_-]+)', url)
        if embed_match:
            return embed_match.group(1)
        
        # Handle regular YouTube URLs: https://www.youtube.com/watch?v=VIDEO_ID
        watch_match = re.search(r'youtube\.com/watch\?v=([a-zA-Z0-9_-]+)', url)
        if watch_match:
            return watch_match.group(1)
        
        # Handle youtu.be short URLs: https://youtu.be/VIDEO_ID
        short_match = re.search(r'youtu\.be/([a-zA-Z0-9_-]+)', url)
        if short_match:
            return short_match.group(1)
        
        # If it's already just a video ID
        if re.match(r'^[a-zA-Z0-9_-]+$', url):
            return url
        
        return None


class VideoExtension(Extension):
    """Markdown extension for video shortcodes."""
    
    def extendMarkdown(self, md):
        """Register the preprocessor."""
        md.preprocessors.register(VideoPreprocessor(md), 'video', 175)


class DownloadThisPreprocessor(Preprocessor):
    """Preprocessor to convert {{< downloadthis ... >}} to download button."""
    
    pattern = r'\{\{<\s*downloadthis\s+([^\s>]+)([^>]*?)\s*>\}\}'
    
    def run(self, lines):
        """Process lines and replace downloadthis shortcodes with Bootstrap buttons."""
        new_lines = []
        for line in lines:
            # Find all matches in the line (handle multiple shortcodes)
            matches = list(re.finditer(self.pattern, line))
            if matches:
                # Process matches in reverse order to preserve positions
                for match in reversed(matches):
                    file_path = match.group(1)
                    attr_string = match.group(2)
                    
                    # Parse attributes
                    attrs = self.parse_attributes(attr_string)
                    
                    # Set defaults
                    dname = attrs.get('dname', self.extract_filename(file_path))
                    label = attrs.get('label', 'Download')
                    icon = attrs.get('icon', 'download')
                    btn_type = attrs.get('type', 'primary')
                    
                    # Generate button HTML
                    button_html = self.generate_button_html(file_path, dname, label, icon, btn_type)
                    
                    # Replace the shortcode
                    line = line[:match.start()] + button_html + line[match.end():]
            new_lines.append(line)
        return new_lines
    
    def parse_attributes(self, attr_string):
        """Extract attributes from attribute string.
        
        Handles both quoted and unquoted values:
        - label="Download Circle Family Worksheet" (quoted)
        - dname=circle-family-ws (unquoted)
        - icon=file-earmark-pdf (unquoted)
        """
        attrs = {}
        if not attr_string.strip():
            return attrs
        
        # Pattern to match key=value pairs
        # Handles: key="value with spaces" or key=value-without-spaces
        attr_pattern = r'(\w+)=(?:"([^"]*)"|([^\s]+))'
        
        for match in re.finditer(attr_pattern, attr_string):
            key = match.group(1)
            # Group 2 is quoted value, group 3 is unquoted value
            value = match.group(2) if match.group(2) is not None else match.group(3)
            attrs[key] = value
        
        return attrs
    
    def extract_filename(self, file_path):
        """Extract filename from file path for default dname."""
        # Extract just the filename from the path
        # e.g., downloads/file.pdf -> file.pdf
        return file_path.split('/')[-1] if '/' in file_path else file_path
    
    def generate_button_html(self, file_path, dname, label, icon, btn_type):
        """Generate Bootstrap button HTML for download link."""
        # Ensure file path starts with / for proper URL
        if not file_path.startswith('/'):
            url_path = '/' + file_path
        else:
            url_path = file_path
        
        # Generate Bootstrap button with icon
        button_html = (
            f'<a href="{url_path}" download="{dname}" class="btn btn-{btn_type} downloadthis">'
            f'<i class="bi bi-{icon}"></i> {label}'
            f'</a>'
        )
        return button_html


class DownloadThisExtension(Extension):
    """Markdown extension for downloadthis shortcodes."""
    
    def extendMarkdown(self, md):
        """Register the preprocessor."""
        md.preprocessors.register(DownloadThisPreprocessor(md), 'downloadthis', 175)


def makeExtension(**kwargs):
    """Return an instance of the VideoExtension."""
    return VideoExtension(**kwargs)
