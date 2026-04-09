# import utils as ut
from src import utils as ut
import glob
import yt_dlp
import os
from aiogram.filters.callback_data import CallbackData
# import aiogram.filters.callback_data.CallbackData

from aiogram import types

LIMIT_SIZE_UPL_VIDEO = 49

vid_format_dict = {
    'audio only': '🎧',
    '256x144': '144p',
    '426x240': '240p',
    '640x360': '360p',
    '854x480': '480p',
    '1280x720': 'HD',
    '1920x1080': 'Full HD',
    '2560x1440': '2K',
    '3840x2160': '4K',
    '7680x4320': '8K',
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
        """Extract direct video URL and metadata without downloading."""
        ydl_opts = {
            'quiet': True,
            'format': 'best',  # single combined stream for direct URL
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'url': info.get('url', ''),
                    'thumbnail': info.get('thumbnail', ''),
                    'title': info.get('title', 'Video'),
                    'duration': info.get('duration', 0),
                    'filesize': info.get('filesize') or info.get('filesize_approx') or 0,
                }
        except Exception as e:
            self.log.error(f"Video info extraction error: {e}")
            return None

    def search_youtube(self, query, max_results=5):
        """Search YouTube using yt-dlp and return up to max_results entries."""
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'force_generic_extractor': False,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(
                    f"ytsearch{max_results}:{query}", download=False
                )
                return result.get('entries', [])
        except Exception as e:
            self.log.error(f"YouTube search error: {e}")
            return []



    # TODO: remove from main
    async def get_dwn_media(self, ydl_opts, user_msg, youtubeLink=''):
        med_url = youtubeLink if youtubeLink else user_msg.text

        loc_video = ydl_opts['outtmpl']

        try:
            # TODO: make async not now
            # TODO: add captions not now
            # logger.debug(f'Start download video {loc_video}') 
            strt_dwn_msg = await user_msg.answer("Start downloading ...")
            self.log.debug(f'Start download video {loc_video}') 
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([med_url])
                # self.log.trace(f'{info=}')
            await strt_dwn_msg.delete()
            # await message.edit_caption(caption="✅ Download successful!")
            self.log.success(f"✅ Download successful! {loc_video}")
        except yt_dlp.utils.DownloadError as e:
            self.log.error(f"❌ Download error: {e}")
            await user_msg.reply(f"Download error: {e}")
            return
        except Exception as e:
            self.log.error(f"❌ An error occurred: {e}")
            await user_msg.reply(f"An error occurred: {e}")
            return

        pattern = glob.escape(loc_video.replace('.%(ext)s', '')) + '.*'
        loc_match = glob.glob(os.path.join('.', pattern))

        loc_video  = loc_match[0]
        # await info_wait_button.delete()
        # Check if the file exists
        if not os.path.exists(loc_video):
            await user_msg.reply(f"The video file does not exist. {loc_video=}")
            return 

        
        self.log.info(f"File size: {ut.h_readable(os.path.getsize(loc_video))}")

        

        #TODO: show awailable limit for user
        # await message.answer(f'Твоє відео {tiktok_url}')

        return (loc_video, os.path.getsize(loc_video))
    


    def _list_formats(self, video_url):
        # video_url = ut.expand_url(video_url)

        # Options for yt-dlp
        # TODO: format not worl
        min_format=420
        max_format=1080
        ydl_opts = {
            'quiet': True,
            'format':   f'bestvideo[height<={max_format}][height>={min_format}]' + 
                        f'+bestaudio/best[height<={max_format}][height>={min_format}]',
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                self.log.info('Скачується формати відео  .....')
                info_dict = ydl.extract_info(video_url, download=False)
                video_name = info_dict['title']
                self.log.info(f'Скачали формати відео з назвою {video_name}')
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


    #TODO: log that start collect formats
    def get_keyboard(self, link):
        try:
            yt_info = self._list_formats(link)
        except Exception:
            self.log.error('Failed to download youtube format')
            return

        # yt_info['id']
        # yt_info['title']
        formats = yt_info.get('formats', [])

        buttons = []
        all_audio_size = [0]
        self.log.info(f'Create buttond for video {yt_info['title']}')
        for fmt in formats:
            format_id = fmt.get('format_id')
            filesize = fmt.get('filesize')

            data = {}
            # data['id'] = yt_info['id']
            
            data['vid_data'] = f"vid_{format_id}"

            data['title'] = yt_info['title'].replace(':', '_')

            if not ut.is_ltn(data['title']):
                data['title'] = ut.cr_2_ln(data['title'])
            
            data['title'] = ut.remove_non_ascii(data['title'])

            len_txt = 64 - 2 - len('vid') - len(data['vid_data'])
            data['title'] = data['title'][:len_txt]

            

            resolution = fmt.get('resolution')
            resolution = vid_format_dict.get(resolution, resolution)

            IsVideo = False
            ext = fmt['ext']


            if ext == 'webm' or not filesize:
                continue

            if ext == 'm4a':
                all_audio_size.append(filesize)
                ext = ''

            if ext == 'mp4':
                IsVideo = True
            cb1 = CommonParamYouTube(title = data['title'] , vid_data=data['vid_data'])
            self.log.trace(f'Create buuton {cb1}')

            real_size = (filesize, filesize + max(all_audio_size))[IsVideo]

            if (filesize and real_size < LIMIT_SIZE_UPL_VIDEO * 1024 * 1024):
                buttons.append(
                    types.InlineKeyboardButton(text=f"{resolution} {ext} {ut.h_readable(real_size)}",
                                                           callback_data=cb1.pack()))

        if not buttons:
            buttons.append(types.InlineKeyboardButton(text="No formats with filesize available", callback_data="no_formats"))

        paired_buttons = ([buttons[i:i+2] for i in range(0, len(buttons), 2)])
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=paired_buttons)
        return (yt_info, keyboard)
