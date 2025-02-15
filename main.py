import asyncio

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher,types
import yt_dlp
from datetime import datetime

from aiogram.filters.command import Command
from aiogram.utils.markdown import hide_link
from aiogram.enums import ParseMode

import glob
import os

from pathlib import Path


load_dotenv()

API_TOKEN = os.getenv('TOKEN')

print(API_TOKEN)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

@dp.message(Command("test1"))
async def cmd_test1(message: types.Message):
    await message.answer(
        f"Харе писати, <b>{message.from_user.full_name}</b>",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("test2"))
async def cmd_test2(message: types.Message):
    user = message.from_user
    url_image = 'https://telegra.ph/file/562a512448876923e28c3.png'
    await message.answer(
        f"{hide_link(url_image)}"
        f"your user_id {user.id}"
    )


@dp.message(lambda msg: 'tiktok.com' in msg.text)
async def handle_tiktok(message: types.Message):
    tiktok_url = message.text
    user = message.from_user
    
    current_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    loc_video = f"media/{user.id}_{current_date}"

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': loc_video,
        # 'outtmpl' : '%(title)s.%(ext)s'
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([tiktok_url])
        # await message.edit_caption(caption="✅ Download successful!")
        print(f"✅ Download successful! {loc_video=}")
    except yt_dlp.utils.DownloadError as e:
        print(f"❌ Download error: {e}")
    except Exception as e:
        print(f"❌ An error occurred: {e}")

    loc_video = glob.glob(os.path.join('.', f'{loc_video}*'))[0]

      # Check if the file exists
    if not os.path.exists(loc_video):
        await message.reply(f"The video file does not exist. {loc_video=}")
        return

    # Print the file size
    print(f"File size: {os.path.getsize(loc_video)} bytes")
    # await message.edit_caption(caption=f"File size: {os.path.getsize(loc_video)} bytes")

    # await bot.send_video(user.id, video)

    # Open and send the video file
    try:
        await message.answer_video(video=types.FSInputFile(loc_video))
    except Exception as e:
        await message.reply(f"An error occurred while sending the video: {e}")

    #TODO: show awailable limit for user
    # await message.answer(f'Твоє відео {tiktok_url}')



async def main():
    print('Start bot')
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

