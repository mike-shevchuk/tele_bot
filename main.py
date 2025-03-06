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

from aiogram import F, Bot, Dispatcher, types, Router
from aiogram.filters.command import Command
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from src.MiddleWare import SharedContextMiddleware
from handlers import test_bot, media_bot

# from aiogram.filters import Text

from src.Users import UserTele
from src.bot import Bot_Func
from src import utils as ut
from src.bot import CommonParam

user_data = {}
load_dotenv()

API_TOKEN = os.getenv('TOKEN')
bot = Bot(token=API_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def start_user(message:types.Message):
    users_reg_df: pd.DataFrame  = ut.get_reg_users()
    user_org = message.from_user

    try:
        usr = UserTele(
            id = user_org.id,
            # chat_id = user.chat_id,
            first_name = user_org.first_name,
            full_name = user_org.full_name,
            username = user_org.username,
            is_bot = user_org.is_bot,
            is_premium = user_org.is_premium,
            language_code = user_org.language_code,
            last_name = user_org.last_name
        )
    except Exception as e:
        logger.exception(f'Except user reg {e}')

    user = ut.get_user_by_id(usr.id)

    if user.empty:
        df = ut.pydantic2pandas(usr)
        all_df = pd.concat([users_reg_df, df])   #.reset_index(drop=True)
        ut.save_reg_user(all_df)
        logger.debug(f'Add new user {usr.id} ')
        await message.answer(f'Ти хто {usr.id}? ми тебе пробиваємо')
    else:
        await message.answer(f'Скучали за тобою {usr.id}')
        return 


@dp.message(lambda msg: any(link in msg.text for link in ['youtu.be', 'youtube.com']))
async def cmd_numbers(message: types.Message):
    #TODO: add user tele
    user = message.from_user
    wait_bot_msg = await message.reply("Твоя лінка на youtube повідомлення опрацьовується!")
    link = ut.expand_url(message.text)
    #TODO: make better not now
    logger.success(f'Хапнули лінку {link} --> {user.id}')
    user_data[message.from_user.id] = link  # Save the link to user_data
    yt_info, all_butons = bot_func.get_keyboard(link)
    video_name = yt_info['title']
    id_video = yt_info['id']
    await message.reply(
                        f"Яке хочете розширення? \n {link}\n повідомлення {user.full_name} \n\n" + 
                        f"Vidoe --> {video_name}\nId --> {id_video} ",
                        reply_markup=all_butons)
    # await message.delete()
    await wait_bot_msg.delete()



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
    sharedContextMiddleware = SharedContextMiddleware(logger=logger, foo = 42,bar = "Bazz", bot_func=bot_func, user_data=user_data)
    # dp.message.middleware(sharedContextMiddleware)
    dp.update.middleware(sharedContextMiddleware)
    
    dp.include_routers(test_bot.router, media_bot.router_med)
    await dp.start_polling(bot)




if __name__ == "__main__":
    asyncio.run(main())
    # executor.start_polling(dp, loop=loop, skip_updates=True)
