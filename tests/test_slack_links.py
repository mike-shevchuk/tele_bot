"""Unit tests for slack_main.extract_url (Slack link markup → media URL).

Needs requirements.txt installed (imports slack_main). Run:
    python tests/test_slack_links.py
or under pytest:
    pytest tests/test_slack_links.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SLACK_BOT_TOKEN", "xoxb-test")

from slack_main import extract_url  # noqa: E402

CASES = [
    ("<https://youtu.be/abc>", "https://youtu.be/abc"),
    ("look <https://www.tiktok.com/@a/video/1|tiktok.com/@a/video/1> lol",
     "https://www.tiktok.com/@a/video/1"),
    ("<https://www.youtube.com/watch?v=x&amp;list=PL1>", "https://www.youtube.com/watch?v=x"),
    ("<https://example.com> then <https://instagram.com/reel/1>", "https://instagram.com/reel/1"),
    ("<https://example.com/youtube>", None),  # no supported domain
    ("youtube.com without markup", None),
    ("", None),
    (None, None),
]


def test_extract_url():
    for text, expected in CASES:
        assert extract_url(text) == expected, (text, extract_url(text))


if __name__ == "__main__":
    test_extract_url()
    print(f"OK: {len(CASES)} cases")
