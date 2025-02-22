import time
from datetime import datetime
import glob
import os
import requests
from pathlib import Path

import asyncio
import yt_dlp
from dotenv import load_dotenv
import loguru
from loguru import logger


from aiogram import F
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.utils.markdown import hide_link
from aiogram.enums import ParseMode


user_data = {}
load_dotenv()

API_TOKEN = os.getenv('TOKEN')

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

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
    # Add more mappings as needed
}


def human_readable(file_size, unit='B'):
    if file_size > 1024 * 1024:
        file_size /=  1024 * 1024
        unit = 'MB'
    elif file_size > 1024:
        file_size /= 1024
        unit = 'KB'
    return f"{file_size:.2f} {unit}"


def expand_url(url):
    try:
        response = requests.head(url, allow_redirects=True)
        return response.url
    except requests.RequestException as e:
        print(f"Error expanding URL: {e}")
        return url


def list_formats(video_url):
    video_url = expand_url(video_url)

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
            logger.debug(f"An error occurred: {e}")
        except Exception as e:
            logger.debug(f"An unexpected error occurred: {e}")


def get_keyboard(link):
    formats = list_formats(link)
    buttons = []
    for fmt in formats:
        format_id = fmt.get('format_id')
        filesize = fmt.get('filesize')
        if filesize:
            resolution = fmt.get('resolution')
            ext = fmt['ext']
            if ext == 'webm':
                continue

            resolution = vid_format_dict.get(resolution, resolution)

            buttons.append(types.InlineKeyboardButton(text=f"{resolution} {ext} {human_readable(filesize)}", callback_data=f"vid_{format_id}"))

    if not buttons:
        buttons.append(types.InlineKeyboardButton(text="No formats with filesize available", callback_data="no_formats"))

    paired_buttons = ([buttons[i:i+2] for i in range(0, len(buttons), 2)])
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=paired_buttons)
    return keyboard


def setup_logger(LOGGER: loguru.logger, data_name="", log_dir=""):
    # Set up loguru
    timestr = time.strftime("%Y-%m-%d_%H:%M:%S")
    logfile_name = f'tele_bot_{data_name}'
    dir_logs = f"logs/{log_dir}"
    logfile_name = f"{dir_logs}/{logfile_name}_{timestr}.log"
    fmt = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {name} | <level>{level}</level> | <level>{message}</level>"
    LOGGER.remove(0)
    LOGGER.add(logfile_name, level="DEBUG", format=fmt, colorize=False, backtrace=False, diagnose=True)
    LOGGER.add(os.sys.stdout, level="TRACE", format=fmt, colorize=True, backtrace=True, diagnose=True)

    global logger
    logger = LOGGER


@dp.message(Command("start"))
async def start_user(message:types.Message):
    await message.answer("Hello!")


@dp.message(Command("test1"))
async def cmd_test1(message: types.Message):
    user = message.from_user
    logger.trace(f'{user.id} run test1')
    await message.answer(
        f"Харе писати, <b>{user.full_name}</b>",
        parse_mode=ParseMode.HTML
    )


@dp.message(Command("test2"))
async def cmd_test2(message: types.Message):
    user = message.from_user
    logger.trace(f'{user.id} run test2')
    url_image = 'https://telegra.ph/file/562a512448876923e28c3.png'
    await message.answer(
        f"{hide_link(url_image)}"
        f"your user_id {user.id}"
    )



@dp.message(lambda msg: any(link in msg.text for link in ['youtu.be', 'youtube.com']))
async def cmd_numbers(message: types.Message):
    user = message.from_user
    wait_bot_msg = await message.reply("Твоя лінка на youtube повідомлення опрацьовується!")
    link = message.text
    #TODO: make better not now
    logger.success(f'Хапнули лінку {link} --> {user.id}')
    user_data[message.from_user.id] = link  # Save the link to user_data
    await message.reply(f"Яке хочете розширення? \n {link}\n повідомлення {user.username}", reply_markup=get_keyboard(link))
    # await message.delete()
    await wait_bot_msg.delete()
    




@dp.callback_query(F.data.startswith("vid"))
async def handle_callback(callback_query: types.CallbackQuery):
    # Extract the format ID from the callback data
    format_id = callback_query.data.split('_')[1]
    user = callback_query.from_user
    youtube_url = user_data.get(user.id)  # Retrieve the saved link

    if not youtube_url:
        # TODO: add logger
        await callback_query.message.reply("Помилка: URL не знайдено.")
        return

    current_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    # TODO: loc video must to be with real name
    # TODO: create dir for every user the path will be look like media/{user_id}/{video_name}
    loc_video = f"media/{user.id}/{current_date}"


    # Options for yt-dlp without post-processing
    ydl_opts = {
        # 'format': f'{format_id}+bestaudio/best[ext=m4a]',  # Combine video format with best audio
        'format': f'{format_id}+m4a/bestaudio/best',
        #'format': 'bestvideo[ext=mp4]+bestaudio[ext=mp4]/mp4+best[height<=480]', 
        'outtmpl': loc_video,
    }

    try:
        # TODO: Add async not now
        strt_dwn_msg = await callback_query.message.answer("Start downloading ...")
        logger.debug(f'Start download video {loc_video}') 
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
        await strt_dwn_msg.delete()
        logger.debug(f"✅ Download successful! {loc_video=}")
    except yt_dlp.utils.DownloadError as e:
        #TODO: logger
        logger.exception(f"❌ Download error: {e}")
        await callback_query.message.reply(f"Download error: {e}")
        return
    except Exception as e:
        #TODO: logger
        logger.exception(f"❌ An error occurred: {e}")
        await callback_query.message.reply(f"An error occurred: {e}")
        return

    info_wait_button = await callback_query.message.reply(f"✅ Download successful!\nSending video")

    # Check if the file exists
    loc_video = glob.glob(os.path.join('.', f'{loc_video}*'))[0]
    if not os.path.exists(loc_video):
        await callback_query.message.reply(f"The video file does not exist. {loc_video=}")
        return

    # Print the file size
    #TODO: logger
    logger.debug(f"File size: {human_readable(os.path.getsize(loc_video))}")

    # Send the video file
    #TODO: logger
    try:

        #HACK: delete later
        if loc_video.endswith('mp4'):
            await callback_query.message.answer_video(video=types.FSInputFile(loc_video))
        else:
            await callback_query.message.answer_audio(audio=types.FSInputFile(loc_video), caption = 'music', title='shit music')
        # If audio only send message.answer_musick or answer_audio check it
        # await callback_query.message.answer_music(video=types.FSInputFile(loc_video))
        
    except Exception as e:
        await callback_query.message.reply(f"An error occurred while sending the video: {e}")
    
    await callback_query.message.delete()
    await info_wait_button.delete()




        
@dp.message(lambda msg: 'tiktok.com' in msg.text)
async def handle_tiktok(message: types.Message):
    tiktok_url = message.text
    user = message.from_user

    current_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    loc_video = f"media/{user.id}/{current_date}"

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': loc_video,
        # 'outtmpl' : '%(title)s.%(ext)s'
    }

    try:
        # TODO: make async not now
        # TODO: add captions not now
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([tiktok_url])
        # await message.edit_caption(caption="✅ Download successful!")
        # TODO: make logger
        print(f"✅ Download successful! {loc_video=}")
    except yt_dlp.utils.DownloadError as e:
        # TODO: make logger
        print(f"❌ Download error: {e}")
    except Exception as e:
        # TODO: make logger
        print(f"❌ An error occurred: {e}")


    loc_video = glob.glob(os.path.join('.', f'{loc_video}*'))[0]

      # Check if the file exists
    if not os.path.exists(loc_video):
        await message.reply(f"The video file does not exist. {loc_video=}")
        return

    logger.debug(f"File size: {human_readable(os.path.getsize(loc_video))}")

    # await message.edit_caption(caption=f"File size: {os.path.getsize(loc_video)} bytes")
    try:
        await message.answer_video(video=types.FSInputFile(loc_video))
    except Exception as e:
        await message.reply(f"An error occurred while sending the video: {e}")

    #TODO: show awailable limit for user
    # await message.answer(f'Твоє відео {tiktok_url}')


async def main():
    setup_logger(logger)
    logger.info('Logger setuped')
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
