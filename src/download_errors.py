"""Classification of yt-dlp download failures.

Pure, dependency-free logic (no yt-dlp / aiogram imports) so it can be unit
tested in isolation. ``src.bot`` imports the public names from here.
"""

from enum import Enum


class DownloadErrorKind(Enum):
    """Category of a yt-dlp download failure, inferred from its error text.

    Drives three things: whether we retry (transient kinds only), what message
    the user sees, and how the failure is tagged in logs/download_issues.jsonl.
    """

    AGE_RESTRICTED = "age_restricted"  # site wants sign-in to confirm age
    LOGIN_REQUIRED = "login_required"  # private / sign-in / bot-check
    UNAVAILABLE = "unavailable"  # removed / deleted / private / not found
    GEO_BLOCKED = "geo_blocked"  # not available in this country
    RATE_LIMITED = "rate_limited"  # HTTP 429 / too many requests
    UNSUPPORTED = "unsupported"  # unsupported URL / no extractor / no formats
    NETWORK = "network"  # timeout / connection / 5xx (transient)
    EXTRACTION = "extraction"  # rehydration / "unable to extract" (flaky)
    UNKNOWN = "unknown"  # anything we could not classify


# Ordered most-specific → most-generic: the first kind with a matching
# substring wins, so AGE/LOGIN/UNAVAILABLE are checked before the broad
# EXTRACTION markers. Match is a case-insensitive substring of the message.
_ERROR_KIND_MARKERS: dict[DownloadErrorKind, tuple[str, ...]] = {
    DownloadErrorKind.AGE_RESTRICTED: (
        "confirm your age",
        "age-restricted",
        "age restricted",
        "inappropriate for some users",
    ),
    DownloadErrorKind.LOGIN_REQUIRED: (
        "sign in to confirm you're not a bot",
        "sign in",
        "log in to",
        "login required",
        "requires authentication",
        "private video",
        "this video is private",
        "this account is private",
        "use --cookies",
    ),
    DownloadErrorKind.GEO_BLOCKED: (
        "not available in your country",
        "in your country",
        "geo restricted",
        "geo-restricted",
    ),
    DownloadErrorKind.RATE_LIMITED: (
        "http error 429",
        "too many requests",
        "rate-limit",
        "rate limit",
    ),
    DownloadErrorKind.UNAVAILABLE: (
        "video unavailable",
        "no longer available",
        "has been removed",
        "was deleted",
        "this post may not be available",
        "http error 404",
        "account has been terminated",
    ),
    DownloadErrorKind.UNSUPPORTED: (
        "unsupported url",
        "no suitable extractor",
        "no video formats found",
        "is not a valid url",
    ),
    DownloadErrorKind.NETWORK: (
        "timed out",  # also covers "read timed out"
        "timeout",
        "connection",
        "temporarily",
        "http error 5",
        "remote end closed",
    ),
    DownloadErrorKind.EXTRACTION: (
        "rehydration",
        "universal data",
        "unable to extract",
        "unable to download webpage",
        "challenge",
    ),
}

# Kinds where retrying has a real chance of succeeding.
_RETRIABLE_KINDS = frozenset(
    {
        DownloadErrorKind.NETWORK,
        DownloadErrorKind.EXTRACTION,
        DownloadErrorKind.RATE_LIMITED,
    }
)

# User-facing (Ukrainian) message per kind. Kinds absent here (e.g. UNKNOWN)
# fall back to the raw error text at the call site.
ERROR_USER_MESSAGES = {
    DownloadErrorKind.AGE_RESTRICTED: (
        "🔞 Відео з віковим обмеженням — сайт вимагає вхід/підтвердження віку, "
        "тож завантажити не вдалося."
    ),
    DownloadErrorKind.LOGIN_REQUIRED: (
        "🔒 Відео приватне або потребує входу — завантажити не можу."
    ),
    DownloadErrorKind.UNAVAILABLE: (
        "🚫 Відео недоступне (видалене, приватне або не існує)."
    ),
    DownloadErrorKind.GEO_BLOCKED: "🌍 Відео недоступне у цьому регіоні.",
    DownloadErrorKind.RATE_LIMITED: (
        "⏳ Забагато запитів до сайту. Спробуй, будь ласка, трохи згодом."
    ),
    DownloadErrorKind.UNSUPPORTED: "❓ Це посилання не підтримується.",
    DownloadErrorKind.NETWORK: (
        "📡 Проблема з мережею під час завантаження. Спробуй ще раз."
    ),
    DownloadErrorKind.EXTRACTION: (
        "⚠️ Сайт тимчасово не віддає відео. Спробуй ще раз за хвилину."
    ),
}


def classify_download_error(msg: str) -> DownloadErrorKind:
    """Map a yt-dlp error message to a DownloadErrorKind (first match wins)."""
    low = msg.lower()
    for kind, markers in _ERROR_KIND_MARKERS.items():
        if any(marker in low for marker in markers):
            return kind
    return DownloadErrorKind.UNKNOWN


def is_retriable_error(msg: str) -> bool:
    """True if the error is a transient kind worth retrying."""
    return classify_download_error(msg) in _RETRIABLE_KINDS
