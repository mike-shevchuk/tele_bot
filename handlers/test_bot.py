from aiogram import F, Bot, Dispatcher, types, Router
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton
from uuid import uuid4

from aiogram.filters.command import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.markdown import hide_link

from src.bot import CommonParamYouTube
from src.MiddleWare import SharedContextMiddleware
from src import utils as ut

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
async def cmd_mem_0(message: types.Message, logger):
    user = message.from_user
    

    try:
        user_df = ut.get_user_by_id(user.id)
        user = ut.pandas2pydentic(user_df)
        user.use_memory = 0
        ut.update_row(user)
        logger.info(f'set memory on 0 for {user.id}')
        await message.answer(
            f"скинули твою використану пам'ять 0"
        )
    except IndexError:
        logger.info(f'{user.id} dont reg')
        await message.answer(
        f"Ти не зареганий натисни /start"
        )
    except Exception as e:
        logger.exception(f'{user.id} dont reg')
        await message.answer(
        f"помилка {e}"
        )
