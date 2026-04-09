from aiogram import Bot, types, Router
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.types import InlineQueryResultArticle, InlineQueryResultVideo, InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton
import html
from aiogram.filters.command import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.markdown import hide_link
from src.bot import CommonParamInline
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

async def check_access(message: types.Message, allowed_levels: list[Level]):
    user_bot = message.from_user
    user_df = ut.get_user_by_id(user_bot.id)
    user = ut.pandas2pydentic(user_df)
    if user.level not in allowed_levels:
        await message.reply('Вибачте, але у вас нема доступу до цієї команди')
        return None
    return user

@router.inline_query()
async def inline_query_handler(inline_query: types.InlineQuery, logger, bot_func, user_data):
    query = inline_query.query.strip()
    user_id = inline_query.from_user.id
    logger.trace(f'Inline Query: {query=}')

    articles = []

    if query.startswith('ssoc ') and len(query) > 5:
        search_text = query[5:].strip()
        if not search_text:
            await inline_query.answer(results=[], cache_time=10)
            return

        logger.info(f'YouTube search via inline: {search_text}')
        entries = bot_func.search_youtube(search_text, max_results=3)

        for i, entry in enumerate(entries):
            title = entry.get('title', 'No title')
            channel = entry.get('channel', entry.get('uploader', 'Unknown'))
            duration = entry.get('duration')
            direct_url = entry.get('url', '')
            thumbnail = entry.get('thumbnail', '')

            duration_str = ''
            if duration:
                mins, secs = divmod(int(duration), 60)
                duration_str = f'{mins}:{secs:02d}'

            description_parts = []
            if duration_str:
                description_parts.append(duration_str)
            if channel:
                description_parts.append(channel)
            description = ' | '.join(description_parts) if description_parts else 'YouTube video'

            if direct_url:
                thumb = thumbnail or 'https://placehold.co/320x180.png'
                articles.append(
                    InlineQueryResultVideo(
                        id=str(i),
                        video_url=direct_url,
                        mime_type='video/mp4',
                        thumbnail_url=thumb,
                        title=title,
                        description=description,
                        video_duration=int(duration) if duration else None,
                    )
                )

        if not articles:
            articles.append(
                InlineQueryResultArticle(
                    id='no_results',
                    title='No results found',
                    input_message_content=InputTextMessageContent(
                        message_text='No YouTube results found.',
                    ),
                    description=f'No videos found for "{search_text}"',
                )
            )

    elif any(domain in query for domain in ['tiktok.com', 'instagram.com', 'youtube.com', 'youtu.be']):
        link = query.strip()
        if 'tiktok.com' in link:
            label = 'TikTok'
        elif 'instagram.com' in link:
            label = 'Instagram'
        else:
            label = 'YouTube'

        # Extract direct video URL so it sends directly in chat (like @LyBot)
        info = bot_func.extract_video_info(link)
        if info and info['url']:
            thumb = info['thumbnail'] or 'https://placehold.co/320x180.png'
            articles.append(
                InlineQueryResultVideo(
                    id='dl_social',
                    video_url=info['url'],
                    mime_type='video/mp4',
                    thumbnail_url=thumb,
                    title=info['title'],
                    description=f'{label} video',
                    video_duration=int(info['duration']) if info['duration'] else None,
                )
            )
        else:
            # Fallback to callback button approach if extraction fails
            key = f"inl_{user_id}_social"
            user_data[key] = link
            cb = CommonParamInline(key=key)
            articles.append(
                InlineQueryResultArticle(
                    id='dl_social',
                    title=f'Download {label} video',
                    input_message_content=InputTextMessageContent(
                        message_text=f"Downloading {label} video...\n{link}",
                    ),
                    description=f'Download video from {label}',
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[[InlineKeyboardButton(
                            text="Download",
                            callback_data=cb.pack(),
                        )]]
                    ),
                )
            )

    else:
        articles.append(
            InlineQueryResultArticle(
                id='help',
                title='How to use',
                input_message_content=InputTextMessageContent(
                    message_text='Use @bot ssoc <query> to search YouTube, or paste a TikTok/Instagram/YouTube link.',
                ),
                description='ssoc <query> | or paste a social link',
            )
        )

    await inline_query.answer(results=articles, cache_time=10)


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
        await message.reply("Ти не зареганий натисни /start")
        return
    logger.info(f'User {caller.id} {caller.full_name} run to clear memory')

    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.reply("Використання: /bugaga <user_id>")
        return

    target_id = int(parts[1])
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
        await message.answer("Ти не зареганий натисни /start")
    except Exception as e:
        logger.exception(f'{target_id} dont reg')
        await message.answer(f"помилка {e}")

@router.message(Command("me"))
async def cmd_me(message: types.Message):
    user_bot = message.from_user
    df_t = ut.get_user_by_id(user_bot.id)
    if df_t.empty:
        await message.reply("Ти не зареганий натисни /start")
        return
    user = ut.pandas2pydentic(df_t)
    total_mb = round(user.level.value/(1024**2), 2)
    used_mb = round(user.use_memory/(1024**2), 2)
    left_mb = max(0, total_mb-used_mb)
    await message.reply(
        f"Тебе звати: {ut.get_name_from_pydantic(user)}, твоє ID: {user.id}\n" 
        f"Твій рівень: {user.level.name}\n"
        f"Ти використав {used_mb } з {total_mb} MB\n"
        f"У тебе лишилось: {left_mb} MB"
        )

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.reply(
        "Вітаю! Я твій універсальний помічник для завантаження контенту та роботи з медіа.\n"
        "\n"                       
        "Що я вмію?\n"
        "\n"                    
        "Відео: Надішли посилання (YT, TikTok, Insta), обери якість — і отримуй файл у чат.\n"
        "\n"
        "Текст: Перешли мені голосове, і я миттєво зроблю з нього розшифровку.\n"
        "\n"
        "Команди:\n"
        "/me — твій профіль та залишок пам'яті.\n"
        "\n"
        "Просто надішли посилання або \"войс\", щоб почати!"
        )


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
    get_level_name = lambda x: str(Level.__members__.get((x).split('.')[-1])).split('.')[-1]
    df_display['level'] = df_display['level_memory'].map(get_level_name)
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
    user = await check_access(message, [Level.admin, Level.vip])
    try:
        df_display = await _load_users_df(message, logger, cfg)
        if df_display is None:
            return
        df_display['size%'] = round(df_display['use_memory'] / df_display['level_memory'] * 100, 1)
        if not user:
            return
        await _reply_users_table(df_display, 'size%', message, logger)
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
        df_display['mb_left'] = round((df_display['level_memory'] - df_display['use_memory']) / (1024 * 1024), 1).astype(str)[:-2]
        if user.level == Level.admin or user.level == Level.vip:
            await _reply_users_table(df_display, 'mb_left', message, logger)
        else:
            await message.reply('Вибачте, але у вас нема доступу до цієї команди')
    except Exception as e:
        logger.exception(f"Проблема при зчитуванні користувачів: {e}")
        await message.reply("❌ Виникла помилка при зчитуванні таблиці користувачів.")
