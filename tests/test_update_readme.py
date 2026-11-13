import datetime
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import update_readme as u  # noqa: E402

RSS = """<?xml version="1.0"?><rss><channel>
<item><title>Old [one]</title><link>https://x/old</link><pubDate>Mon, 30 Mar 2026 00:00:00 GMT</pubDate></item>
<item><title>New</title><link>https://x/new</link><pubDate>Mon, 20 Apr 2026 00:00:00 GMT</pubDate></item>
</channel></rss>"""

NOW = ('<html><head><meta name="description" content="Short summary."></head>'
       '<body><time datetime="2026-04-10T00:00:00.000Z"> April 10, 2026 </time></body></html>')


class ReplaceSection(unittest.TestCase):
    def test_replaces_only_between_markers(self):
        text = "a\n<!-- now:start -->\nold\n<!-- now:end -->\nb\n"
        out = u.replace_section(text, "now", "new")
        self.assertEqual(out, "a\n<!-- now:start -->\nnew\n<!-- now:end -->\nb\n")

    def test_is_idempotent(self):
        text = "<!-- writing:start -->\nx\n<!-- writing:end -->\n"
        once = u.replace_section(text, "writing", "y\nz")
        self.assertEqual(u.replace_section(once, "writing", "y\nz"), once)

    def test_missing_markers_raise(self):
        with self.assertRaises(ValueError):
            u.replace_section("nothing", "now", "x")

    def test_replacement_with_backslashes_is_literal(self):
        text = "<!-- now:start -->\n<!-- now:end -->\n"
        self.assertIn(r"\[a\]", u.replace_section(text, "now", r"\[a\]"))


class Parsing(unittest.TestCase):
    def test_posts_newest_first_and_limited(self):
        posts = u.parse_posts(RSS, limit=1)
        self.assertEqual([p[0] for p in posts], ["New"])

    def test_render_posts_escapes_brackets_and_formats_date(self):
        out = u.render_posts(u.parse_posts(RSS))
        self.assertIn(r"- [Old \[one\]](https://x/old) (Mar 30, 2026)", out)
        self.assertTrue(out.index("New") < out.index("Old"))

    def test_now_parsing(self):
        summary, updated = u.parse_now(NOW)
        self.assertEqual(summary, "Short summary.")
        self.assertEqual(updated, datetime.date(2026, 4, 10))
        self.assertIn("Updated Apr 10, 2026", u.render_now(summary, updated))

    def test_now_without_summary_raises(self):
        with self.assertRaises(ValueError):
            u.parse_now("<html></html>")


if __name__ == "__main__":
    unittest.main()
