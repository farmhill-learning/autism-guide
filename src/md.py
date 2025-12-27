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


def makeExtension(**kwargs):
    """Return an instance of the VideoExtension."""
    return VideoExtension(**kwargs)
