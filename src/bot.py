# import utils as ut
from src import utils as ut
import glob
import yt_dlp
import os


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



class Bot_Func:

    def __init__(self, log, root_prj):
        self.log = log
        self.root_prj = root_prj



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
            await strt_dwn_msg.delete()
            # await message.edit_caption(caption="✅ Download successful!")
            self.log.success(f"✅ Download successful! {loc_video}")
        except yt_dlp.utils.DownloadError as e:
            self.log.error(f"❌ Download error: {e}")
            await user_msg.reply(f"Download error: {e}")
            return
        except Exception as e:
            self.log.exception(f"❌ An error occurred: {e}")
            await user_msg.reply(f"An error occurred: {e}")
            return


        loc_match = glob.glob(os.path.join('.', f'{loc_video}*'))

        loc_video  = loc_match[0]
        # await info_wait_button.delete()
        # Check if the file exists
        if not os.path.exists(loc_video):
            await user_msg.reply(f"The video file does not exist. {loc_video=}")
            return 

        
        self.log.info(f"File size: {ut.human_readable(os.path.getsize(loc_video))}")

        

        #TODO: show awailable limit for user
        # await message.answer(f'Твоє відео {tiktok_url}')

        return loc_video
    


    def _list_formats(self, video_url):
        # video_url = ut.expand_url(video_url)

        # Options for yt-dlp
        # TODO: format not worl
        min_format=420
        max_format=1080
        ydl_opts = {
            'quiet': True,
            'format': f'bestvideo[height<={max_format}][height>={min_format}]+bestaudio/best[height<={max_format}][height>={min_format}]',
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info_dict = ydl.extract_info(video_url, download=False)
                formats = info_dict.get('formats', [])
                return formats
            except yt_dlp.utils.DownloadError as e:
                self.log.debug(f"An error occurred: {e}")
            except Exception as e:
                self.log.debug(f"An unexpected error occurred: {e}")


    #TODO: log that start collect formats
    def get_keyboard(self, link):
        formats = self._list_formats(link)
        buttons = []
        all_audio_size = [0]
        for fmt in formats:
            format_id = fmt.get('format_id')
            filesize = fmt.get('filesize')
            resolution = fmt.get('resolution')
            resolution = vid_format_dict.get(resolution, resolution)

            IsVideo = False
            ext = fmt['ext']


            if ext == 'webm' or not filesize:
                continue

            if ext == 'm4a':
                all_audio_size.append(filesize)

            if ext == 'mp4':
                IsVideo = True

            real_size = (filesize, filesize + max(all_audio_size))[IsVideo]

            if (filesize and real_size < LIMIT_SIZE_UPL_VIDEO * 1024 * 1024):
                buttons.append(types.InlineKeyboardButton(text=f"{resolution} {ext} {ut.human_readable(real_size)}", callback_data=f"vid_{format_id}"))

        if not buttons:
            buttons.append(types.InlineKeyboardButton(text="No formats with filesize available", callback_data="no_formats"))

        paired_buttons = ([buttons[i:i+2] for i in range(0, len(buttons), 2)])
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=paired_buttons)
        return keyboard
