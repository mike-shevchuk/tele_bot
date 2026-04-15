# import utils as ut
from src import utils as ut
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

    def extract_video_info(self, url):
        """Extract video metadata (title, thumbnail, duration). Blocking."""
        try:
            with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True}) as ydl:
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

            ydl_opts_with_hook = {**ydl_opts, "progress_hooks": [progress_hook]}

            def download():
                with yt_dlp.YoutubeDL(ydl_opts_with_hook) as ydl:
                    ydl.download([med_url])

            await asyncio.to_thread(download)
            await strt_dwn_msg.delete()
            self.log.success(f"✅ Download successful! {loc_video}")
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

        # Resolve actual file path: prefer hook-captured name, fall back to glob
        if finished_file and os.path.exists(finished_file):
            loc_video = finished_file
        else:
            base_path = re.sub(r"\.?%\([^)]+\)s", "", loc_video)
            if not base_path or base_path.endswith("/"):
                await user_msg.reply(
                    f"Download finished but file not found. {loc_video=}"
                )
                return
            loc_match = glob.glob(os.path.join(".", glob.escape(base_path) + "*"))
            if not loc_match:
                await user_msg.reply(
                    f"Download finished but file not found. {loc_video=}"
                )
                return
            loc_video = loc_match[0]

        # Write sidecar .txt named {title}__{date}.txt
        date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        stem, _ = ut.parse_media_filename(loc_video)
        sidecar = f"{os.path.dirname(loc_video)}/{stem}__{date_str}.txt"
        Path(sidecar).touch()

        self.log.info(f"File size: {ut.h_readable(os.path.getsize(loc_video))}")

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
