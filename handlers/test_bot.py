from aiogram import F, Bot, Dispatcher, types, Router
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton
from uuid import uuid4
import os
import html
from aiogram.filters.command import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.markdown import hide_link
from aiogram.fsm.storage.memory import MemoryStorage
from src.bot import CommonParamYouTube
from src.MiddleWare import SharedContextMiddleware
from src import utils as ut
import pandas as pd
from src.Users import Level



class CommonParamTick(CallbackData, prefix="tick"):
    # id: str
    title: str
    vid_data: str

router = Router()
# router.message.middleware(SharedContextMiddleware())


# @router.inline_query()
# async def inline_query_handler(inline_query: types.InlineQuery, logger):
#     logger.trace('Inline  MOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOD')
#     article = InlineQueryResultArticle(
#         id=uuid4().hex,
#         title="Check my profile",
#         input_message_content=InputTextMessageContent(message_text="Check my profile by button bellow:"),
#         article = InlineQueryResultArticle(
#             id=uuid4().hex,
#             title="Check my profile",
#             input_message_content=InputTextMessageContent(message_text="Check my profile by button bellow:"),
#             reply_markup=InlineKeyboardMarkup(
#                 inline_keyboard=[[
#                     InlineKeyboardButton(text="text")
#                 ]]
#             )
#         )
#     )
#     await inline_query.answer(results=[article])
#     ...

@router.inline_query()
async def inline_query_handler(inline_query: types.InlineQuery, logger):
    query = inline_query.query.strip()
    logger.trace(f'Inline Query: {query=}')

    articles = []

    if 'tiktok.com' in query:
        articles.append(
            InlineQueryResultArticle(
                id='1',
                title="TikTok Download",
                input_message_content=InputTextMessageContent(message_text="TikTok video is downloading..."),
                description="Download the video from the provided TikTok link.",
                reply_markup=types.InlineKeyboardMarkup(
                    inline_keyboard=[[types.InlineKeyboardButton(
                        text="Download",
                        callback_data=CommonParamTick(title="TikTok", vid_data='ticktock_test').pack()
                    )]]
                )
            )
        )
    else:
        articles.append(
            InlineQueryResultArticle(
                id='2',
                title="Invalid Link",
                input_message_content=InputTextMessageContent(message_text="This link is not supported."),
                description="The provided link is not supported."
            )
        )

    await inline_query.answer(results=articles)


@router.message(Command("test0"))
async def cmd_start(message: Message, logger, foo: int, bar: str):
    logger.info(f"Received /test0 command with foo={foo} and bar={bar}")
    await message.answer(f"Hello! foo={foo}, bar={bar}")

@router.message(Command("test1"))
async def cmd_test1(message: types.Message, logger):
    user = message.from_user
    logger.trace(f'{user.id} run test1')
    await message.answer(f"Харе писати, <b>{user.full_name}</b>",parse_mode=ParseMode.HTML)


@router.message(Command("test2"))
async def cmd_test2(message: types.Message, logger):
    user = message.from_user
    logger.trace(f'{user.id} run test2')
    url_image = 'https://telegra.ph/file/562a512448876923e28c3.png'
    await message.answer(
        f"{hide_link(url_image)}"
        f"your user_id {user.id}"
    )

@router.message(Command("bugaga"))
async def cmd_mem_0(message: types.Message, logger, cfg):
    user = message.from_user
    
    id = int(message.text.split(' ')[1])
    try:
        user_df = ut.get_user_by_id(id)
        user = ut.pandas2pydentic(user_df)
        user.use_memory = 0
        ut.update_row(user)
        logger.info(f'set memory on 0 for {id}')
        await message.answer(
            f"скинули {id} використану пам'ять 0"
        )
    except IndexError:
        logger.info(f'{id} dont reg')
        await message.answer(f"Ти не зареганий натисни /start")
    except Exception as e:
        logger.exception(f'{id} dont reg')
        await message.answer(f"помилка {e}")

@router.message(Command("chels"))
async def cmd_users(message: types.Message, logger, cfg):
    user = message.from_user
    logger.trace(f'{user.id} run show   users')
    prj_root = cfg.shared_vars.get('prj_root')

    csv_path = f'{prj_root}/data/reg_user.csv'

    if not os.path.isfile(csv_path):
        await message.reply("⚠️ Файл з користувачами не знайдено.")
        return

    try:
        df_user = pd.read_csv(csv_path)
        df_user = df_user.loc[:, ['id', 'username', 'full_name', 'level', 'use_memory']]
        if df_user.empty:
            await message.reply("🗃️ Таблиця користувачів порожня.")
            return
        
        df_display =  df_user.rename(columns={'id': 'ID', 'username': 'nick', 'full_name': 'name'})

        # change value in column use_memmory to percent 0 to 100 using column level . Level it iis max 100 %  
        get_bytes4level = lambda x: Level.__members__.get((x).split('.')[-1]).value
        df_display['level'] = df_display['level'].map(get_bytes4level)
        df_display['size%'] = round((100 - (df_display['level'] - df_display['use_memory']) / df_display['level'] * 100), 1).astype(str) + '%'
        df_display['nick/name'] = df_display['nick'] + '/' + df_display['name']
        df_display = df_display.loc[:, ['ID', 'nick/name', 'size%']]
        logger.trace(df_display)


        # df_display['use_mem'] = df_display['use_mem'] / df_display['level'] * 100
        # Преобразуємо таблицю в текст, екрануємо HTML
        text_table = html.escape(df_display.to_string(index=False, justify='left', col_space=10))

        await message.reply(f"<pre>{text_table}</pre>", parse_mode="HTML")

    except Exception as e:
        logger.exception(f"Помилка при зчитуванні користувачів: {e}")
        await message.reply("❌ Виникла помилка при зчитуванні таблиці користувачів.")
