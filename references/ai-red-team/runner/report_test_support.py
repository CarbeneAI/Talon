"""Render report fixtures with HTML and GFM autolinking enabled."""
from html.parser import HTMLParser

from markdown_it import MarkdownIt


class RenderedReport(HTMLParser):
    def __init__(self, markdown):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.attributes = []
        self.text = []
        self.feed(MarkdownIt("gfm-like", {"html": True}).render(markdown))

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.attributes.extend(attrs)

    def handle_data(self, data):
        self.text.append(data)

    @property
    def content(self):
        return "".join(self.text)


def rendered_text(markdown):
    return RenderedReport(markdown).content
