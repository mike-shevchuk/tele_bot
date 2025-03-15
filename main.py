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
from src.bot import CommonParamYouTube

import glob

user_data = {}
load_dotenv()

API_TOKEN = os.getenv('TOKEN')
bot = Bot(token=API_TOKEN)
dp = Dispatcher()


# BOT_NAME = 'med_soc_bot'

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
    user_bot = message.from_user
    link = ut.expand_url(message.text)
    df_t = ut.get_user_by_id(user_bot.id)

    if df_t.empty:
        await message.reply(f"Ти не зареганий натисни /start")
        return
    user = ut.pandas2pydentic(df_t)
    available_memory = user.level.value - user.use_memory
    logger.info(f'User {user.id} has {ut.h_readable(available_memory)=}')
    
    if available_memory < 0:
        await message.reply(f"Ви використали свій ліміт({ut.h_readable(user.level.value)})"+
                             f" на цей місяць, підніміть свій статус")
        return
    
    wait_bot_msg = await message.reply(f"Твоя лінка на youtube повідомлення опрацьовується!\
                                        У тебе лишилося {ut.h_readable(available_memory)}")
    logger.success(f'Хапнули лінку {link} --> {user.id}')
    user_data[message.from_user.id] = link  # Save the link to user_data
    yt_info, all_butons = bot_func.get_keyboard(link)
    video_name = yt_info['title']
    id_video = yt_info['id']
    await message.reply(
                        f"Яке хочете розширення? \n {link}\n повідомлення {user.full_name} \n\n" + 
                        f"Vidoe --> {video_name}\nId --> {id_video} \n" +
                        f"У тебе лишилося {ut.h_readable(available_memory)}",
                        reply_markup=all_butons)
    # await message.delete()
    await wait_bot_msg.delete()



@dp.message(lambda msg: any(soc in msg.text for soc in ['instagram.com', 'tiktok.com']))
async def handle_inst_tick(message: types.Message, cfg):
    user_bot = message.from_user
    df_t = ut.get_user_by_id(user_bot.id)
    if df_t.empty:
        await message.reply(f"Ти не зареганий натисни /start")
        return
    
    user = ut.pandas2pydentic(df_t)
    availMemory = user.level.value - user.use_memory
    logger.info(f'User {user.id} has {ut.h_readable(availMemory)=}')
    if availMemory < 0:
        await message.reply(
            f"Ви використали свій ліміт({ut.h_readable(user.level.value)}) на цей місяць,"+
              f"підніміть свій статус"
            )
        return

    current_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    loc_video = f"media/{user.id}/{current_date}"

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': loc_video,
    }

    loc_video, file_size = await bot_func.get_dwn_media(ydl_opts, message)
    availMemory -= file_size
    
    try:
        await message.answer_video(video=types.FSInputFile(loc_video), 
                                   caption=f'@{cfg.shared_vars.bot_name}\n\nУ тебе лишилося {
                                       ut.h_readable(availMemory)
                                       }\n\n{message.text}')
    except Exception as e:
        await message.reply(f"An error occurred while sending the video: {e}")
    user.use_memory += file_size
    loc_match = glob.glob(os.path.join('.', f'{loc_video}*'))
    assert loc_match
    loc_video  = loc_match[0]
    ut.update_row(user)
    ut.delete_video_file(loc_video)


async def main():
    root_prj = Path(__file__).parent.absolute()
    # os.remove(root_prj / 'data' / 'reg_user.csv' )
    cfg = ut.load_config('configs/cfg.yml')
    global logger
    logger = ut.setup_logger(loguru.logger)
    logger.info('Logger setuped')
    #HACK: delete in future
    global bot_func
    bot_func = Bot_Func(log=logger, root_prj=root_prj)
    logger.info('Bot Func setuped')
    sharedContextMiddleware = SharedContextMiddleware(
        logger=logger, foo = 42,bar = "Bazz", bot_func=bot_func, user_data=user_data, cfg=cfg
    )
    # dp.message.middleware(sharedContextMiddleware)
    dp.update.middleware(sharedContextMiddleware)
    
    dp.include_routers(test_bot.router, media_bot.router_med)
    await dp.start_polling(bot)





if __name__ == "__main__":
    asyncio.run(main())
    # executor.start_polling(dp, loop=loop, skip_updates=True)
