import html as html_entities

from bs4 import BeautifulSoup


def strip_html(html: str) -> str:
    if not html:
        return ""
    # Greenhouse's job "content" field comes back HTML-entity-escaped (e.g.
    # "&lt;h2&gt;" instead of a literal "<h2>"), so the raw string has no real
    # tags for BeautifulSoup to strip until entities are decoded first.
    unescaped = html_entities.unescape(html)
    soup = BeautifulSoup(unescaped, "html.parser")
    return soup.get_text(separator=" ", strip=True)
