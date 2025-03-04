from datetime import datetime
import os
from pathlib import Path

import asyncio
from dotenv import load_dotenv
import pandas as pd
import loguru


from aiogram import F, Bot, Dispatcher, types, Router
from aiogram.filters.command import Command
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from src.MiddleWare import SharedContextMiddleware
from handlers import test_bot

# from aiogram.filters import Text

from src.UserTele import UserTele
from src.bot import Bot_Func
from src import utils as ut

user_data = {}
load_dotenv()

API_TOKEN = os.getenv('TOKEN')
bot = Bot(token=API_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def start_user(message:types.Message):
    users_reg_df: pd.DataFrame  = ut.get_reg_users()
    user = message.from_user

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


    # TODO: get from db
    if len(users_reg_df) < 1:
        # TODO: check later
        users = [usr]
        df = pd.DataFrame([us.to_dict() for us in users]).reset_index(drop=True)
        # df.set_index('id')
        logger.trace(df)
        ut.save_reg_user(df)
        logger.success('First user')
        await  message.answer("You are the best")
        return 
    
    try:
        user_match = users_reg_df.loc[users_reg_df.id == usr.id]
        user_match.set_index('id', inplace=True)


        if len(user_match):
            # usr_temp = user_match.loc[usr.id]
            id_t = usr.id
            logger.debug(f'User {id_t} is already registered ')
            await message.answer(f'Скучали за тобою {id_t}')
            return 

        else:
            users = [usr]
            df = pd.DataFrame([us.to_dict() for us in users]).reset_index(drop=True)
            df.set_index('id')
            all_df = pd.concat([users_reg_df, df]).reset_index(drop=True)
            logger.debug(f'Add new user {usr.id} ')
            # users_reg_df += pd.DataFrame(usr)
            ut.save_reg_user(all_df)
            await message.answer(f'Ти хто {usr.id}? ми тебе пробиваємо')
    except Exception as e:
        logger.exception(f'Exception {e}')



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
        
    except Exception as e:
        await bot_msg.reply(f"An error occurred while sending the video: {e}")
    
    await bot_msg.delete()
    await info_wait_button.delete()


@dp.message(lambda msg: any(soc in msg.text for soc in ['instagram.com', 'tiktok.com']))
async def handle_inst_tick(message: types.Message):
    user = message.from_user
    current_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    loc_video = f"media/{user.id}/{current_date}"

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': loc_video,
    }

    loc_video = await bot_func.get_dwn_media(ydl_opts, message)
    # await message.edit_caption(caption=f"File size: {os.path.getsize(loc_video)} bytes")
    try:
        await message.answer_video(video=types.FSInputFile(loc_video), caption=f'@med_link_bot\n\n{message.text}')
    except Exception as e:
        await message.reply(f"An error occurred while sending the video: {e}")


async def main():
    root_prj = Path(__file__).parent.absolute()
    
    # os.remove(root_prj / 'data' / 'reg_user.csv' )
    global logger
    logger = ut.setup_logger(loguru.logger)
    logger.info('Logger setuped')
    #HACK: delete in future
    global bot_func
    bot_func = Bot_Func(log=logger, root_prj=root_prj)
    logger.info('Bot Func setuped')
    sharedContextMiddleware = SharedContextMiddleware(logger=logger, foo = 42,bar = "Bazz")
    # dp.message.middleware(sharedContextMiddleware)
    dp.update.middleware(sharedContextMiddleware)
    
    dp.include_routers(test_bot.router)
    await dp.start_polling(bot)




if __name__ == "__main__":
    asyncio.run(main())
    # executor.start_polling(dp, loop=loop, skip_updates=True)
