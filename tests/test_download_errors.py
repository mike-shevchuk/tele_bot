"""Unit tests for src.download_errors.

Pure logic — no yt-dlp / aiogram needed, so this runs standalone:
    python tests/test_download_errors.py
or under pytest:
    pytest tests/test_download_errors.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.download_errors import (  # noqa: E402
    DownloadErrorKind,
    ERROR_USER_MESSAGES,
    _ERROR_KIND_MARKERS,
    classify_download_error,
    is_retriable_error,
)

K = DownloadErrorKind

# (yt-dlp-style message, expected kind, expected retriable)
CASES = [
    # The bot's real flaky error — must stay retriable.
    (
        "ERROR: [TikTok] 1: Unable to extract universal data for rehydration; "
        "please report this issue on https://github.com/yt-dlp/yt-dlp/issues",
        K.EXTRACTION,
        True,
    ),
    (
        "ERROR: Sign in to confirm your age. This video may be inappropriate "
        "for some users.",
        K.AGE_RESTRICTED,
        False,
    ),
    ("ERROR: Sign in to confirm you're not a bot", K.LOGIN_REQUIRED, False),
    ("ERROR: [instagram] This account is private", K.LOGIN_REQUIRED, False),
    ("ERROR: Video unavailable. This video has been removed", K.UNAVAILABLE, False),
    (
        "ERROR: The uploader has not made this video available in your country",
        K.GEO_BLOCKED,
        False,
    ),
    ("ERROR: HTTP Error 429: Too Many Requests", K.RATE_LIMITED, True),
    ("ERROR: Unsupported URL: https://example.com/x", K.UNSUPPORTED, False),
    ("ERROR: Unable to download webpage: Read timed out.", K.NETWORK, True),
    ("ERROR: <urlopen error [Errno 111] Connection refused>", K.NETWORK, True),
    ("ERROR: HTTP Error 503: Service Unavailable", K.NETWORK, True),
    ("ERROR: something we have never seen before", K.UNKNOWN, False),
]


def test_classification_and_retriability():
    for msg, kind, retriable in CASES:
        assert classify_download_error(msg) == kind, (msg, classify_download_error(msg))
        assert is_retriable_error(msg) is retriable, (msg, is_retriable_error(msg))


def test_case_insensitive():
    assert classify_download_error("UNABLE TO EXTRACT something") == K.EXTRACTION


def test_specific_kind_wins_over_later_generic():
    # Ordering is load-bearing: a permanent AGE marker must win even though the
    # message also contains a later EXTRACTION substring ("extract").
    msg = "Sign in to confirm your age — also could not extract the page"
    assert classify_download_error(msg) == K.AGE_RESTRICTED
    assert is_retriable_error(msg) is False


def test_read_timed_out_still_classifies_as_network():
    # "read timed out" was removed as redundant; "timed out" still covers it.
    assert classify_download_error("Read timed out.") == K.NETWORK


def test_every_kind_except_unknown_has_markers_and_a_message():
    for kind in DownloadErrorKind:
        if kind is DownloadErrorKind.UNKNOWN:
            continue
        assert kind in _ERROR_KIND_MARKERS, f"{kind} has no markers"
        assert kind in ERROR_USER_MESSAGES, f"{kind} has no user message"


if __name__ == "__main__":
    import traceback

    failures = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_"):
            continue
        try:
            fn()
            print(f"PASS  {name}")
        except Exception:  # noqa: BLE001
            failures += 1
            print(f"FAIL  {name}")
            traceback.print_exc()
    print("ALL PASS" if not failures else f"{failures} TEST(S) FAILED")
    sys.exit(1 if failures else 0)
