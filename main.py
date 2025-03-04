from datetime import datetime
import os
from pathlib import Path

import asyncio
from dotenv import load_dotenv
import pandas as pd
import loguru

from aiogram import F
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.utils.markdown import hide_link
from aiogram.enums import ParseMode

from src.UserTele import UserTele
from src.UserTele import Level
from src.bot import Bot_Func
from src import utils as ut

from src.ExceptionClass import CSVError

user_data = {}
load_dotenv()

API_TOKEN = os.getenv('TOKEN')
bot = Bot(token=API_TOKEN)
dp = Dispatcher()




def get_user_tele(user):

    try:
        usr = UserTele(
            id = user.id,
            # chat_id = user.chat_id,
            first_name = user.first_name,
            full_name = user.full_name,
            username = user.username,
            is_bot = user.is_bot,
            is_premium = user.is_premium,
            language_code = user.language_code,
            last_name = user.last_name
        )
    except Exception as e:
        logger.exception(f'Except user reg {e}')

    return usr


        
# except Exception as e:
#     logger.exception(f'Exception {e}')







@dp.message(Command("start"))
async def start_user(message:types.Message):
    user_telegram = message.from_user

    usr = get_user_tele(user_telegram)

    try:
        user_tele = ut.get_user_by_id(usr.id)
    except CSVError:
        # INFO: db is empty

        ut.reg_user_db(usr)
        # TODO: check later
        # users = [usr_tele]
        # df = pd.DataFrame([us.to_dict() for us in users])
        # df.set_index('id')
        # logger.trace(df)
        # ut.save_reg_user(df)
        logger.success('First user reg {usr_tele.id}')
        await  message.answer(f"You are the best, you are the first {usr.id}")
        return 
    
    if user_tele.empty:
        await message.answer(f'Ти хто {usr}? ми тебе пробиваємо')
        ut.reg_user_db(usr)
        
    else:
        logger.success('oldfun {user_tele.id}')
        await message.answer(f'Скучали за тобою {user_tele.id}')
        return
        



@dp.message(Command("test1"))
async def cmd_test1(message: types.Message):
    user = message.from_user
    logger.trace(f'{user.id} run test1')
    await message.answer(f"Харе писати, <b>{user.full_name}</b>",parse_mode=ParseMode.HTML)


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
    #TODO: add user tele
    user = message.from_user
    wait_bot_msg = await message.reply("Твоя лінка на youtube повідомлення опрацьовується!")
    link = ut.expand_url(message.text)
    #TODO: make better not now
    logger.success(f'Хапнули лінку {link} --> {user.id}')
    user_data[message.from_user.id] = link  # Save the link to user_data
    await message.reply(f"Яке хочете розширення? \n {link}\n повідомлення {user.username}", reply_markup=bot_func.get_keyboard(link))
    # await message.delete()
    await wait_bot_msg.delete()


@dp.callback_query(F.data.startswith("vid"))
async def handle_callback(callback_query: types.CallbackQuery):
    # Extract the format ID from the callback data
    format_id = callback_query.data.split('_')[1]
    user = callback_query.from_user
    youtube_url = user_data.get(user.id)  # Retrieve the saved link
    bot_msg = callback_query.message

    if not youtube_url:
        # TODO: add logger
        await bot_msg.reply(f"Помилка: URL не знайдено. {youtube_url}")
        return

    current_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    # TODO: loc video must to be with real name
    loc_media = f"media/{user.id}/{current_date}"

    # Options for yt-dlp without post-processing
    ydl_opts = {
        # 'format': f'{format_id}+bestaudio/best[ext=m4a]',  # Combine video format with best audio  #'format': 'bestvideo[ext=mp4]+bestaudio[ext=mp4]/mp4+best[height<=480]', 
        'format': f'{format_id}+m4a/bestaudio/best',
        'outtmpl': loc_media,
    }

    loc_media = await bot_func.get_dwn_media(ydl_opts, bot_msg, youtubeLink=youtube_url)
    info_wait_button = await bot_msg.reply(f"✅ Download successful!\nSending video")

    try:
        #HACK: delete later
        if loc_media.endswith('mp4'):
            await bot_msg.answer_video(video=types.FSInputFile(loc_media), caption = f'@med_link_bot\n\n{youtube_url}')
        else:
            await bot_msg.answer_audio(audio=types.FSInputFile(loc_media), caption = f'@med_link_bot\n\nmusic', title='shit music')
        # If audio only send message.answer_musick or answer_audio check it
        file_size = ut.get_file_size(loc_media)
        logger.info(f'{file_size}')
        logger.trace(f'{loc_media=}')
        ut.delete_video_file(loc_media)
    except Exception as e:
        await bot_msg.reply(f"An error occurred while sending the video: {e}")
    
    await bot_msg.delete()
    await info_wait_button.delete()


@dp.message(lambda msg: any(soc in msg.text for soc in ['instagram.com', 'tiktok.com']))
async def handle_inst_tick(message: types.Message):
    user = message.from_user

    user = message.from_user

    user_tele = get_user_tele(user)
    print(user_tele)
    try:
        user = ut.get_user_by_id(user_tele.id)
        logger.info(f'{user=}')
    except CSVError as e:
        logger.warning('csv is empty or not exist {e}')
        await message.reply('Перевірте чи ви є учасником групи команда /start, якщо є то наразі бот на технічній перерві')
        return
    except Exception as e:
        await message.reply('Бот на технічній перерві')
        logger.error(f'exception in tiktok instagram {e}')
        return

    if not user:
        await message.reply('ТИ не зареєстований пропиши команду /start')
        return
    

    avail_mem = user.level.value * 1024 * 1024 - user.use_memory
    logger.trace(f'{avail_mem=}')

    if avail_mem < 0:
        await message.reply('ТИ використав свій ліміт для збільшення ліміту пиши адміну @pishov_nahuy')
        return
    

    current_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    loc_video = f"media/{user_tele.id}/{current_date}"

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': loc_video,
    }

    loc_video = await bot_func.get_dwn_media(ydl_opts, message)


    # await message.edit_caption(caption=f"File size: {os.path.getsize(loc_video)} bytes")
    try:
        await message.answer_video(video=types.FSInputFile(loc_video), caption=f'@med_link_bot\n\n{message.text} ')
    except Exception as e:
        await message.reply(f"An error occurred while sending the video: {e}")

    file_size = ut.get_file_size(loc_video)
    user.use_memory +=  file_size


    # ut.save_reg_user(df)
    logger.trace(f'{loc_video=}')
    ut.delete_video_file(loc_video)
    ut.update_reg_user(user)


async def main():
    root_prj = Path(__file__).parent.absolute()
    
    # os.remove(root_prj / 'data' / 'reg_user.csv' )
    global logger
    logger = ut.setup_logger(loguru.logger)
    logger.info('Logger setuped')
    #HACK: delete in future
    global bot_func
    bot_func = Bot_Func(log=logger, root_prj=root_prj)
    logger.info('Bot Funk setuped')

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())