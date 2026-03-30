from aiogram import F, Bot, Dispatcher, types, Router
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton
from uuid import uuid4
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
async def cmd_test0(message: Message, logger, foo: int, bar: str):
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
async def cmd_reset_memory(message: types.Message, logger, cfg, bot: Bot):
    caller = message.from_user
    if ut.get_user_by_id(caller.id).empty:
        await message.reply(f"Ти не зареганий натисни /start")
        return
    logger.info(f'User {caller.id} {caller.full_name} run to clear memory')

    target_id = int(message.text.split(' ')[1])
    try:
        target_df = ut.get_user_by_id(target_id)
        target_user = ut.pandas2pydentic(target_df)
        target_user.use_memory = 0
        ut.update_row(target_user)
        logger.info(f'set memory on 0 for {target_id}')
        await message.answer(f"скинули {target_id} використану пам'ять 0")
        logger.info(f'Sending reset notification to {target_id}')
        await bot.send_message(
            chat_id=target_id,
            text="Йоу! 🎉 Твій ліміт щойно обнулили!\nКачай скільки душа забажає (але не дуже, бо знову скінчиться 😏)"
        )
        logger.info(f'Notification sent to {target_id}')
    except IndexError:
        logger.info(f'{target_id} dont reg')
        await message.answer(f"Ти не зареганий натисни /start")
    except Exception as e:
        logger.exception(f'{target_id} dont reg')
        await message.answer(f"помилка {e}")

@router.message(Command("me"))
async def cmd(message: types.Message):
    user_bot = message.from_user
    df_t = ut.get_user_by_id(user_bot.id)
    if df_t.empty:
        await message.reply(f"Ти не зареганий натисни /start")
        return
    user = ut.pandas2pydentic(df_t)
    await message.reply(f"""Тебе звати: {ut.get_name_from_pydantic(user)}, твоє ID: {user.id}. Ти {user.level}.
У тебе лишилось: {round((user.level.value - user.use_memory)/(1024*1024), 2)} з {round(user.level.value/(1024*1024), 2)} MB""")

@router.message(Command("help"))
async def cmd(message: types.Message):
    user_bot = message.from_user
    df_t = ut.get_user_by_id(user_bot.id)
    if df_t.empty:
        await message.reply(f"Ти не зареганий натисни /start")
    await message.reply("""Вітаю! Я твій універсальний помічник для завантаження контенту та роботи з медіа.
                        
Що я вмію?
                        
Відео: Надішли посилання (YT, TikTok, Insta), обери якість — і отримуй файл у чат.

Текст: Перешли мені голосове, і я миттєво зроблю з нього розшифровку.

Команди:
/me — твій профіль та залишок пам'яті.

Просто надішли посилання або "войс", щоб почати!""")


async def _load_users_df(message: types.Message, logger, cfg):
    """Load CSV user data. Returns df_display or None if error (reply already sent)."""
    caller = message.from_user
    if ut.get_user_by_id(caller.id).empty:
        await message.reply("Ти не зареганий натисни /start")
        return None
    logger.info(f'User {caller.id} run show all users')

    prj_root = cfg.shared_vars.get('prj_root')
    csv_path = f'{prj_root}/data/reg_user.csv'

    try:
        df_user = pd.read_csv(csv_path)
    except FileNotFoundError:
        await message.reply("⚠️ Файл з користувачами не знайдено.")
        return None

    df_user = df_user.loc[:, ['id', 'username', 'full_name', 'level', 'use_memory']]
    if df_user.empty:
        await message.reply("🗃️ Таблиця користувачів порожня.")
        return None

    df_display = df_user.rename(columns={'id': 'ID', 'username': 'nick', 'full_name': 'name', 'level': 'level_memory'})
    level_to_bytes = lambda x: Level.__members__.get((x).split('.')[-1]).value
    name4bytes = lambda x: str(Level.__members__.get((x).split('.')[-1])).split('.')[-1]
    df_display['level'] = df_display['level_memory'].map(name4bytes)
    df_display['level_memory'] = df_display['level_memory'].map(level_to_bytes)
    df_display[['nick', 'name']] = df_display[['nick', 'name']].fillna('-')
    df_display['nick/name'] = df_display['nick'].str[:13] + '/' + df_display['name'].str[:7]
    return df_display


async def _reply_users_table(df_display, col: str, message: types.Message, logger):
    """Sort by col, select display columns, and reply with formatted table."""
    df_display = df_display.sort_values(by=col, ascending=False)
    df_display = df_display.loc[:, ['level', 'ID', 'nick/name', col]]
    logger.trace(df_display)
    text_table = html.escape(df_display.to_string(index=False, justify='left', col_space=10))
    await message.reply(f"<pre>{text_table}</pre>", parse_mode="HTML")


@router.message(Command("chels"))
async def cmd_show_users_pct(message: types.Message, logger, cfg):
    user_bot = message.from_user
    user_df = ut.get_user_by_id(user_bot.id)
    user = ut.pandas2pydentic(user_df)
    try:
        df_display = await _load_users_df(message, logger, cfg)
        if df_display is None:
            return
        df_display['size%'] = round(df_display['use_memory'] / df_display['level_memory'] * 100, 1)
        logger.info(f'>>>>>>>>>>>>{user.level}')
        if user.level == Level.vip or user.level == Level.admin:
            await _reply_users_table(df_display, 'size%', message, logger)
        else:
            await message.reply('Вибачте, але у вас нема доступу до цієї команди')    
    except Exception as e:
        logger.exception(f"Помилка при зчитуванні користувачів: {e}")
        await message.reply("❌ Виникла помилка при зчитуванні таблиці користувачів.")


@router.message(Command("specs"))
async def cmd_show_users_mb(message: types.Message, logger, cfg):
    user_bot = message.from_user
    user_df = ut.get_user_by_id(user_bot.id)
    user = ut.pandas2pydentic(user_df)
    try:
        df_display = await _load_users_df(message, logger, cfg)
        if df_display is None:
            return
        df_display['size_left'] = round((df_display['level_memory'] - df_display['use_memory']) / (1024 * 1024), 2).astype(str) + " MB"
        if user.level == 'admin' or user.level == 'vip':
            await _reply_users_table(df_display, 'size_left', message, logger)
        else:
            await message.reply('Вибачте, але у вас нема доступу до цієї команди')
    except Exception as e:
        logger.exception(f"Проблема при зчитуванні користувачів: {e}")
        await message.reply("❌ Виникла помилка при зчитуванні таблиці користувачів.")
