# import utils as ut
from src import utils as ut
import contextlib
import glob
import re
from datetime import datetime
from pathlib import Path
import yt_dlp
import os
import asyncio
import time
from aiogram.filters.callback_data import CallbackData

from aiogram import types

LIMIT_SIZE_UPL_VIDEO = 49

# How many times to retry a download when a *transient* error happens
# (e.g. TikTok "rehydration" extraction flakiness — the same link often
# succeeds on the next attempt). Backoff grows: RETRY_BASE_DELAY * attempt.
MAX_DOWNLOAD_ATTEMPTS = 4
RETRY_BASE_DELAY = 1.5

# Substrings that mark a *temporary* failure worth retrying. Anything else
# (private/removed video, unsupported URL, ...) fails immediately.
_RETRIABLE_MARKERS = (
    "rehydration",
    "universal data",
    "unable to extract",
    "unable to download webpage",
    "challenge",
    "timed out",
    "timeout",
    "connection",
    "temporarily",
    "http error 5",
    "read timed out",
)


def _is_retriable_error(msg: str) -> bool:
    """True if the yt-dlp error message looks like a transient, retriable one."""
    low = msg.lower()
    return any(marker in low for marker in _RETRIABLE_MARKERS)


# Network/extractor robustness defaults shared by every yt-dlp call.
_YDL_ROBUSTNESS_OPTS = {
    "retries": 5,
    "fragment_retries": 5,
    "extractor_retries": 3,
    "socket_timeout": 30,
}


def _strip_outtmpl_vars(template: str) -> str:
    """Strip yt-dlp template vars (e.g. ".%(ext)s") to get the base path/prefix."""
    return re.sub(r"\.?%\([^)]+\)s", "", template)


def _cleanup_partial_downloads(base: str) -> None:
    """Remove ``.part``/``.ytdl`` artifacts left by an interrupted yt-dlp run."""
    if not base:
        return
    for leftover in glob.glob(glob.escape(base) + "*"):
        if leftover.endswith((".part", ".ytdl")):
            with contextlib.suppress(OSError):
                os.remove(leftover)


vid_format_dict = {
    "audio only": "🎧",
    "256x144": "144p",
    "426x240": "240p",
    "640x360": "360p",
    "854x480": "480p",
    "1280x720": "HD",
    "1920x1080": "Full HD",
    "2560x1440": "2K",
    "3840x2160": "4K",
    "7680x4320": "8K",
}


class CommonParamYouTube(CallbackData, prefix="vid"):
    # id: str
    title: str
    vid_data: str


class CommonParamInline(CallbackData, prefix="idl"):
    key: str


class Bot_Func:
    def __init__(self, log, root_prj):
        self.log = log
        self.root_prj = root_prj

    def _log_media_info(self, info: dict | None) -> str:
        """Log codec/resolution/bitrate and return the same text for sidecar writing."""
        if not info:
            return ""
        # For merged/remuxed formats the final stream data lives under
        # requested_downloads[0]; fall back to top-level info_dict fields.
        rd = (info.get("requested_downloads") or [{}])[0]
        src = rd if rd else info

        vcodec = src.get("vcodec") or info.get("vcodec", "?")
        acodec = src.get("acodec") or info.get("acodec", "?")
        width = src.get("width") or info.get("width")
        height = src.get("height") or info.get("height")
        fps = src.get("fps") or info.get("fps")
        tbr = src.get("tbr") or info.get("tbr")  # total bitrate kbps
        ext = src.get("ext") or info.get("ext", "?")
        title = info.get("title", "")
        url = info.get("webpage_url") or info.get("original_url", "")

        res = f"{width}x{height}" if width and height else "?x?"
        fps_str = f" @ {fps:.0f}fps" if fps else ""
        tbr_str = f" | {tbr:.0f}kbps" if tbr else ""
        line = f"🎬 {title!r} | {ext} | {vcodec} / {acodec} | {res}{fps_str}{tbr_str}"
        self.log.info(line)
        return "\n".join([line, f"url: {url}", f"title: {title}"])

    # Codecs natively supported on Apple (iOS / macOS / Safari)
    _APPLE_VCODECS = (
        "avc",
        "h264",
        "hvc",
        "hevc",
        "h265",
        "av1",
    )  # av1 on newer devices

    async def _ensure_h264(self, path: str, media_info: dict | None, user_msg) -> str:
        """Transcode to H.264/AAC if the video codec is not Apple-compatible."""
        if not media_info:
            return path
        rd = (media_info.get("requested_downloads") or [{}])[0]
        vcodec = ((rd.get("vcodec") or media_info.get("vcodec")) or "").lower()
        # "none" == audio-only download (mp3 etc.): nothing to transcode.
        if not vcodec or vcodec == "none" or vcodec.startswith(self._APPLE_VCODECS):
            return path  # already fine

        self.log.warning(
            f"⚠️ Codec {vcodec!r} not Apple-compatible — transcoding to H.264"
        )
        try:
            await user_msg.answer("⚙️ Converting to H.264 for Apple compatibility…")
        except Exception:
            pass

        out_path = os.path.splitext(path)[0] + ".h264.mp4"
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-y",
            "-i",
            path,
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            out_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            self.log.error(f"Transcode failed: {stderr.decode()[-500:]}")
            return path  # send original, let the caller deal with it
        os.remove(path)
        self.log.success(f"✅ Transcoded to H.264: {out_path}")
        return out_path

    def extract_video_info(self, url):
        """Extract video metadata (title, thumbnail, duration). Blocking."""
        try:
            opts = {"quiet": True, "skip_download": True, **_YDL_ROBUSTNESS_OPTS}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    "thumbnail": info.get("thumbnail", ""),
                    "title": info.get("title", "Video"),
                    "duration": info.get("duration", 0),
                }
        except Exception as e:
            self.log.error(f"Video info extraction error: {e}")
            return None

    def search_youtube(self, query, max_results=3):
        """Search YouTube via ytsearch. Blocking."""
        try:
            with yt_dlp.YoutubeDL({"quiet": True, "extract_flat": True}) as ydl:
                result = ydl.extract_info(
                    f"ytsearch{max_results}:{query}", download=False
                )
                return result.get("entries", [])
        except Exception as e:
            self.log.error(f"YouTube search error: {e}")
            return []

    async def get_dwn_media(self, ydl_opts, user_msg, youtubeLink=""):
        med_url = youtubeLink if youtubeLink else user_msg.text

        loc_video = ydl_opts["outtmpl"]

        strt_dwn_msg = None
        finished_file: str = ""
        media_info: dict | None = None
        try:
            strt_dwn_msg = await user_msg.answer("Downloading... 0%\n⬜⬜⬜⬜⬜⬜⬜⬜")
            self.log.debug(f"Start download video {loc_video}")

            loop = asyncio.get_running_loop()
            last_update = [0.0]

            async def _edit_progress(text):
                try:
                    await strt_dwn_msg.edit_text(text)
                except Exception:
                    pass

            def pp_hook(d):
                nonlocal finished_file
                if d["status"] == "finished":
                    fp = d.get("info_dict", {}).get("filepath", "")
                    if fp:
                        finished_file = fp

            def progress_hook(d):
                nonlocal finished_file
                if d["status"] == "finished":
                    finished_file = d.get("filename", "")
                    return
                if d["status"] != "downloading":
                    return
                now = time.time()
                if now - last_update[0] < 2:
                    return
                last_update[0] = now

                total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                downloaded = d.get("downloaded_bytes", 0)
                if total <= 0:
                    return

                pct = downloaded / total * 100
                filled = int(8 * downloaded // total)
                bar = "🟩" * filled + "⬜" * (8 - filled)
                speed = d.get("speed", 0)
                speed_str = f" | {speed / 1024 / 1024:.1f} MB/s" if speed else ""
                text = f"Downloading... {pct:.0f}%\n{bar}{speed_str}"

                try:
                    asyncio.run_coroutine_threadsafe(_edit_progress(text), loop)
                except Exception:
                    pass

            ydl_opts_with_hook = {
                # Robustness defaults — caller's ydl_opts may override via spread.
                **_YDL_ROBUSTNESS_OPTS,
                **ydl_opts,
                "progress_hooks": [progress_hook],
                "postprocessor_hooks": [pp_hook],
            }

            def download():
                # Retry transient failures (TikTok rehydration flakiness, timeouts,
                # transient network errors). The same link that fails once usually
                # succeeds on the next attempt — see logs in the bug report. The
                # final attempt re-raises (attempt >= MAX), so the loop never falls
                # through.
                base = _strip_outtmpl_vars(loc_video)
                for attempt in range(1, MAX_DOWNLOAD_ATTEMPTS + 1):
                    try:
                        with yt_dlp.YoutubeDL(ydl_opts_with_hook) as ydl:
                            return ydl.extract_info(med_url, download=True)
                    except yt_dlp.utils.DownloadError as e:
                        if attempt >= MAX_DOWNLOAD_ATTEMPTS or not _is_retriable_error(
                            str(e)
                        ):
                            raise
                        self.log.warning(
                            f"⚠️ Download attempt {attempt}/{MAX_DOWNLOAD_ATTEMPTS} "
                            f"failed (retriable), retrying: {e}"
                        )
                        # Let the user know we're retrying (best-effort).
                        asyncio.run_coroutine_threadsafe(
                            _edit_progress(
                                f"⚠️ Спроба {attempt} не вдалась, пробую ще раз…"
                            ),
                            loop,
                        )
                        _cleanup_partial_downloads(base)
                        time.sleep(RETRY_BASE_DELAY * attempt)

            media_info = await asyncio.to_thread(download)
            await strt_dwn_msg.delete()
            self.log.success(f"✅ Download successful! {loc_video}")
            self._log_media_info(media_info)
        except yt_dlp.utils.DownloadError as e:
            self.log.error(f"❌ Download error: {e}")
            if strt_dwn_msg:
                await strt_dwn_msg.delete()
            await user_msg.reply(f"Download error: {e}")
            return
        except Exception as e:
            self.log.error(f"❌ An error occurred: {e}")
            if strt_dwn_msg:
                await strt_dwn_msg.delete()
            await user_msg.reply(f"An error occurred: {e}")
            return

        # Resolve actual file path: prefer postprocessor-hook result, then
        # progress-hook result, then glob fallback.
        resolved: str = ""
        if finished_file and os.path.exists(finished_file):
            resolved = finished_file
        else:
            base_path = _strip_outtmpl_vars(loc_video)
            if base_path.endswith("/"):
                # Template was directory-only — pick newest non-part file in dir
                candidates = [
                    f
                    for f in glob.glob(os.path.join(base_path, "*"))
                    if not f.endswith(".part") and os.path.isfile(f)
                ]
                if candidates:
                    resolved = max(candidates, key=os.path.getmtime)
            elif base_path:
                loc_match = glob.glob(os.path.join(".", glob.escape(base_path) + "*"))
                if loc_match:
                    resolved = loc_match[0]

        if not resolved:
            self.log.error(f"Download finished but file not found. {loc_video=}")
            await user_msg.reply(f"Download finished but file not found. {loc_video=}")
            return
        loc_video = resolved

        # Transcode to H.264 if codec is not Apple-compatible (VP9, AV1, etc.)
        loc_video = await self._ensure_h264(loc_video, media_info, user_msg)

        # Write sidecar .txt named {title}__{date}.txt
        date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        stem, _ = ut.parse_media_filename(loc_video)
        sidecar = f"{os.path.dirname(loc_video)}/{stem}__{date_str}.txt"
        file_size = os.path.getsize(loc_video)
        sidecar_text = self._log_media_info(media_info)
        Path(sidecar).write_text(
            sidecar_text + f"\nsize: {ut.h_readable(file_size)}\n", encoding="utf-8"
        )

        self.log.info(f"File size: {ut.h_readable(file_size)}")

        # TODO: show awailable limit for user
        # await message.answer(f'Твоє відео {tiktok_url}')

        return (loc_video, os.path.getsize(loc_video))

    def _list_formats(self, video_url):
        # video_url = ut.expand_url(video_url)

        # Options for yt-dlp
        # TODO: format not worl
        min_format = 420
        max_format = 1080
        ydl_opts = {
            "quiet": True,
            "format": f"bestvideo[height<={max_format}][height>={min_format}]"
            + f"+bestaudio/best[height<={max_format}][height>={min_format}]",
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                self.log.info("Скачується формати відео  .....")
                info_dict = ydl.extract_info(video_url, download=False)
                video_name = info_dict["title"]
                self.log.info(f"Скачали формати відео з назвою {video_name}")
                # pprint(json.dumps(ydl.sanitize_info(info_dict)))

                # formats = info_dict.get('formats', [])
                # return formats
                return info_dict
            except yt_dlp.utils.DownloadError as e:
                self.log.error(f"An error occurred: {e}")
                raise e
            except Exception as e:
                self.log.debug(f"An unexpected error occurred: {e}")
                raise e

    # TODO: log that start collect formats
    def get_keyboard(self, link):
        try:
            yt_info = self._list_formats(link)
        except Exception:
            self.log.error("Failed to download youtube format")
            return

        # yt_info['id']
        # yt_info['title']
        formats = yt_info.get("formats", [])

        buttons = []
        all_audio_size = [0]
        self.log.info(f"Create buttond for video {yt_info['title']}")
        for fmt in formats:
            format_id = fmt.get("format_id")
            filesize = fmt.get("filesize")

            data = {}
            # data['id'] = yt_info['id']

            data["vid_data"] = f"vid_{format_id}"

            data["title"] = yt_info["title"].replace(":", "_")

            if not ut.is_ltn(data["title"]):
                data["title"] = ut.cr_2_ln(data["title"])

            data["title"] = ut.remove_non_ascii(data["title"])

            len_txt = 64 - 2 - len("vid") - len(data["vid_data"])
            data["title"] = data["title"][:len_txt]

            resolution = fmt.get("resolution")
            resolution = vid_format_dict.get(resolution, resolution)

            IsVideo = False
            ext = fmt["ext"]

            if ext == "webm" or not filesize:
                continue

            if ext == "m4a":
                all_audio_size.append(filesize)
                ext = ""

            if ext == "mp4":
                IsVideo = True
            cb1 = CommonParamYouTube(title=data["title"], vid_data=data["vid_data"])
            self.log.trace(f"Create buuton {cb1}")

            real_size = (filesize, filesize + max(all_audio_size))[IsVideo]

            if filesize and real_size < LIMIT_SIZE_UPL_VIDEO * 1024 * 1024:
                buttons.append(
                    types.InlineKeyboardButton(
                        text=f"{resolution} {ext} {ut.h_readable(real_size)}",
                        callback_data=cb1.pack(),
                    )
                )

        if not buttons:
            buttons.append(
                types.InlineKeyboardButton(
                    text="No formats with filesize available",
                    callback_data="no_formats",
                )
            )

        paired_buttons = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=paired_buttons)
        return (yt_info, keyboard)
