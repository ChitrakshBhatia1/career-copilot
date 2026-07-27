from career_copilot.htmltext import strip_html


def test_strip_html_empty_string_returns_empty_string():
    assert strip_html("") == ""


def test_strip_html_none_returns_empty_string():
    # strip_html's `if not html` guard should treat None the same as "".
    assert strip_html(None) == ""


def test_strip_html_strips_plain_html_tags():
    result = strip_html("<p>Hello <strong>world</strong></p>")

    assert "Hello" in result
    assert "world" in result
    assert "<" not in result
    assert ">" not in result


def test_strip_html_unescapes_then_strips_double_escaped_html():
    # This is the real bug M5 caught: Greenhouse's "content" field comes back
    # HTML-entity-escaped HTML, e.g. the raw string literally contains
    # "&lt;h2&gt;" rather than "<h2>". If strip_html only ran BeautifulSoup
    # without first calling html.unescape(), the "&lt;" / "&gt;" sequences
    # aren't real tags, so BeautifulSoup would leave them as visible text
    # instead of stripping them.
    escaped = (
        "&lt;h2&gt;&lt;strong&gt;Responsibilities&lt;/strong&gt;&lt;/h2&gt;"
        "&lt;ul&gt;&lt;li&gt;Write code&lt;/li&gt;&lt;/ul&gt;"
    )

    result = strip_html(escaped)

    assert "Responsibilities" in result
    assert "Write code" in result
    assert "<" not in result
    assert ">" not in result
