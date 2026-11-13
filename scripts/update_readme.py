#!/usr/bin/env python3
"""Refresh the auto-updated sections of README.md from jontobias.com.

Standard library only. Sections live between marker comments:
  <!-- writing:start --> ... <!-- writing:end -->
  <!-- now:start -->     ... <!-- now:end -->
"""
import datetime
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

SITE = "https://www.jontobias.com"
RSS_URL = f"{SITE}/rss.xml"
NOW_URL = f"{SITE}/now/"
POST_LIMIT = 5
README = Path(__file__).resolve().parent.parent / "README.md"


def replace_section(text, name, body):
    """Return text with the content between the name markers replaced by body."""
    pattern = re.compile(
        rf"(<!-- {re.escape(name)}:start -->\n).*?(\n?<!-- {re.escape(name)}:end -->)",
        re.DOTALL,
    )
    if not pattern.search(text):
        raise ValueError(f"markers for '{name}' not found")
    return pattern.sub(lambda m: f"{m.group(1)}{body.strip()}\n{m.group(2).lstrip(chr(10))}", text, count=1)


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "profile-readme-updater"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def format_date(value):
    return f"{value:%b} {value.day}, {value.year}"


def escape_link_text(text):
    return re.sub(r"([\[\]])", r"\\\1", text.strip())


def parse_posts(rss_xml, limit=POST_LIMIT):
    """Return [(title, link, date)] for the newest posts, newest first."""
    posts = []
    for item in ET.fromstring(rss_xml).iter("item"):
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        raw_date = item.findtext("pubDate", "").strip()
        if not (title and link):
            continue
        try:
            date = datetime.datetime.strptime(raw_date, "%a, %d %b %Y %H:%M:%S %Z")
        except ValueError:
            date = None
        posts.append((title, link, date))
    posts.sort(key=lambda p: p[2] or datetime.datetime.min, reverse=True)
    return posts[:limit]


def render_posts(posts):
    lines = []
    for title, link, date in posts:
        suffix = f" ({format_date(date)})" if date else ""
        lines.append(f"- [{escape_link_text(title)}]({link}){suffix}")
    lines.append("")
    lines.append(f"More on the [blog]({SITE}/blog/).")
    return "\n".join(lines)


class NowParser(HTMLParser):
    """The site has no feed for /now/, so read its description and update date."""

    def __init__(self):
        super().__init__()
        self.summary = None
        self.updated = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta" and attrs.get("name") == "description" and self.summary is None:
            self.summary = (attrs.get("content") or "").strip()
        elif tag == "time" and self.updated is None and attrs.get("datetime"):
            self.updated = attrs["datetime"][:10]


def parse_now(html):
    parser = NowParser()
    parser.feed(html)
    if not parser.summary:
        raise ValueError("no summary found on the now page")
    updated = datetime.date.fromisoformat(parser.updated) if parser.updated else None
    return parser.summary, updated


def render_now(summary, updated):
    when = f" Updated {format_date(updated)}." if updated else ""
    return f"{summary}{when} Read the full [Now page]({NOW_URL})."


def update(text, rss_xml, now_html):
    text = replace_section(text, "writing", render_posts(parse_posts(rss_xml)))
    return replace_section(text, "now", render_now(*parse_now(now_html)))


def main():
    original = README.read_text(encoding="utf-8")
    updated = update(original, fetch(RSS_URL), fetch(NOW_URL))
    if updated != original:
        README.write_text(updated, encoding="utf-8")
        print("README.md updated")
    else:
        print("README.md already up to date")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # fail the workflow loudly
        print(f"update failed: {error}", file=sys.stderr)
        sys.exit(1)
