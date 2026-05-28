from aiogram import Bot, types, Router
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.types import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
import html
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from aiogram.filters.command import Command
from aiogram.utils.markdown import hide_link
from src.bot import CommonParamInline
from src import utils as ut
import pandas as pd
from src.Users import Level

REVIEW_QUEUE_DIR = Path('/tmp/tele-bot-review-queue/pending')

_last_query_time: dict[int, float] = {}

router = Router()

async def check_access(message: types.Message, allowed_levels: list[Level]):
    user_bot = message.from_user
    user_df = ut.get_user_by_id(user_bot.id)
    user = ut.pandas2pydentic(user_df)
    if user.level not in allowed_levels:
        await message.reply('Вибачте, але у вас нема доступу до цієї команди')
        return None
    return user


def _fmt_duration(secs):
    if not secs:
        return ''
    m, s = divmod(int(secs), 60)
    return f'{m}:{s:02d}'


def _fmt_views(count):
    if not count:
        return ''
    if count >= 1_000_000:
        return f'{count / 1_000_000:.1f}M views'
    if count >= 1_000:
        return f'{count / 1_000:.1f}K views'
    return f'{count} views'


@router.inline_query()
async def inline_query_handler(inline_query: types.InlineQuery, logger, bot_func, user_data):
    query = inline_query.query.strip()
    user_id = inline_query.from_user.id
    logger.trace(f'Inline Query: {query=}')

    if query:
        now = time.time()
        _last_query_time[user_id] = now
        await asyncio.sleep(1)
        if _last_query_time.get(user_id) != now:
            return
        # Bound the debounce dict
        if len(_last_query_time) > 1000:
            cutoff = now - 300
            for uid in [k for k, v in _last_query_time.items() if v < cutoff]:
                _last_query_time.pop(uid, None)

    articles = []

    if any(domain in query for domain in ['tiktok.com', 'instagram.com']):
        link = query
        label = 'TikTok' if 'tiktok.com' in link else 'Instagram'

        key = f"inl_{user_id}_social"
        user_data[key] = {'url': link, 'mode': 'social', 'title': ''}
        cb = CommonParamInline(key=key)

        info = await asyncio.to_thread(bot_func.extract_video_info, link)
        if info:
            preview_title = info.get('title') or f'Download {label} video'
            preview_thumb = info.get('thumbnail') or None
            duration_str = _fmt_duration(info.get('duration'))
            preview_desc = f'{label} | {duration_str}' if duration_str else label
            user_data[key]['title'] = info.get('title', '')
        else:
            preview_title = f'Download {label} video'
            preview_thumb = None
            preview_desc = f'Download video from {label}'

        articles.append(
            InlineQueryResultArticle(
                id='dl_social',
                title=preview_title,
                input_message_content=InputTextMessageContent(
                    message_text=f"Downloading {label} video...\n{link}",
                ),
                description=preview_desc,
                thumbnail_url=preview_thumb,
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(
                        text="Download",
                        callback_data=cb.pack(),
                    )]]
                ),
            )
        )

    elif query:
        if query.startswith('v ') and len(query) > 2:
            search_text = query[2:].strip()
            mode = 'video'
            btn_label = 'Download MP4'
        else:
            search_text = query
            mode = 'audio'
            btn_label = 'Download MP3'

        if search_text:
            logger.info(f'YouTube {mode} search: {search_text}')
            entries = await asyncio.to_thread(bot_func.search_youtube, search_text, 5)

            for i, entry in enumerate(entries):
                title = entry.get('title', 'No title')
                channel = entry.get('channel') or entry.get('uploader', '')
                video_url = entry.get('url') or entry.get('webpage_url', '')
                video_id = entry.get('id', '')
                thumb = f'https://i.ytimg.com/vi/{video_id}/hqdefault.jpg' if video_id else 'https://placehold.co/320x180.png'

                key = f"inl_{user_id}_{i}"
                user_data[key] = {'url': video_url, 'mode': mode, 'title': title}

                parts = [p for p in (
                    _fmt_duration(entry.get('duration')),
                    _fmt_views(entry.get('view_count')),
                    channel,
                ) if p]
                description = ' | '.join(parts) if parts else 'YouTube'

                cb = CommonParamInline(key=key)
                articles.append(
                    InlineQueryResultArticle(
                        id=str(i),
                        title=title,
                        input_message_content=InputTextMessageContent(
                            message_text=f"{title}\n{video_url}",
                        ),
                        description=description,
                        thumbnail_url=thumb,
                        reply_markup=InlineKeyboardMarkup(
                            inline_keyboard=[[InlineKeyboardButton(
                                text=btn_label,
                                callback_data=cb.pack(),
                            )]]
                        ),
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

    else:
        articles.append(
            InlineQueryResultArticle(
                id='help',
                title='How to use',
                input_message_content=InputTextMessageContent(
                    message_text='Type a search query for MP3, "v query" for video, or paste a TikTok/Instagram link.',
                ),
                description='<query> = MP3 | v <query> = video | TikTok/Insta link',
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
    progress_bar_str_value = ut.progress_bar_str(used_mb, total_mb)
    await message.reply(
        f"Тебе звати: {ut.get_name_from_pydantic(user)}, твоє ID: {user.id}\n" 
        f"Твій рівень: {user.level.name}\n"
        f"Ти використав {used_mb} з {total_mb} MB\n"
        f"{progress_bar_str_value}\n"
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
    df_display['level'] = df_display['level'].str[:5]
    df_display['level_memory'] = df_display['level_memory'].map(level_to_bytes)
    df_display[['nick', 'name']] = df_display[['nick', 'name']].fillna('-')
    df_display['nick/name'] = df_display['nick'].str[:8] + '/' + df_display['name'].str[:7]
    return df_display


async def _reply_users_table(df_display, col: str, message: types.Message, logger):
    """Sort by col, select display columns, and reply with formatted table."""
    df_display = df_display.sort_values(by=col, ascending=False)
    df_display = df_display.loc[:, ['ID', 'level', 'nick/name', col]]
    logger.trace(df_display)
    text_table = html.escape(df_display.to_string(index=False, justify='left', col_space=1))
    await message.reply(f"<pre>{text_table}</pre>", parse_mode="HTML")


@router.message(Command("chels"))
async def cmd_show_users_pct(message: types.Message, logger, cfg):
    user = await check_access(message, [Level.admin, Level.vip])
    try:
        df_display = await _load_users_df(message, logger, cfg)
        if df_display is None:
            return
        df_display['size%'] = round(df_display['use_memory'] / df_display['level_memory'] * 100)
        df_display['size%'] = df_display['size%'].map(lambda p: int(p))
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
        df_display['mb_left'] = round((df_display['level_memory'] - df_display['use_memory']) / (1024 * 1024), 1)
        df_display['mb_left'] = df_display['mb_left'].map(lambda p: int(p))
        if user.level == Level.admin or user.level == Level.vip:
            await _reply_users_table(df_display, 'mb_left', message, logger)
        else:
            await message.reply('Вибачте, але у вас нема доступу до цієї команди')
    except Exception as e:
        logger.exception(f"Проблема при зчитуванні користувачів: {e}")
        await message.reply("❌ Виникла помилка при зчитуванні таблиці користувачів.")


@router.message(Command('setlevel'))
async def cmd_setlevel(message: types.Message, logger, bot: Bot):
    user = await check_access(message, [Level.admin])
    if not user:
        logger.warning('user levele is not admin')
        return
    
    try:
        args = message.text.split()
        if len(args) != 3:
            logger.warning(f'args length doesn\'t equal 3. len(args)= {len(args)}')
            await message.reply('Формат: /setlevel <user_id> <user_new_level>')
            return
        if not args[1].isdigit():
            logger.warning('user_id is not int.')
            await message.reply("❌ user_id має бути числом")
            return
        
        target_id = int(args[1])
        level_name = args[2]

        if level_name not in Level.__members__:
            levels = ', '.join(Level.__members__)
            logger.warning('Unknown level.')
            await message.reply(f'❌ Невідомий рівень. Доступні рівні: {levels}')
            return
        
        new_level = Level[level_name]
        target_df = ut.get_user_by_id(target_id)

        if target_df.empty:
            logger.warning('Target user is empty')
            await message.reply('Незнайдено вказаного користувача')
            return
        
        target_user = ut.pandas2pydentic(target_df)
        old_level = target_user.level
        logger.info(f'/setlevel {target_id} ({target_user.full_name}): {old_level.name} -> {new_level.name}')
        target_user.level = new_level
        ut.update_row(target_user)
        try:
            await bot.send_message(target_id, f'Твій новий рівень: {target_user.level.name}.')
        except Exception:
            logger.warning(f'Невдалось повідомити користувача про зміну рівня{target_id}.')
        await message.reply(f'✅ Рівень користувача {target_user.full_name} змінено на {target_user.level.name}')
    except Exception:
        logger.exception(f"Проблема в /setlevel")
        await message.reply("❌ Виникла несподівана помилка")


@router.message(Command('review'))
async def cmd_review(message: types.Message, logger):
    caller = message.from_user
    logger.info(f'/review called by {caller.id} ({caller.full_name}): {message.text!r}')

    user = await check_access(message, [Level.admin, Level.vip])
    if not user:
        return

    args = message.text.split()
    if len(args) != 2 or not args[1].isdigit() or int(args[1]) <= 0:
        logger.warning(f'/review bad args: {args}')
        await message.reply('Формат: /review <pr_number>')
        return
    pr_number = int(args[1])

    now = datetime.now(timezone.utc)
    payload = {
        'pr_number': pr_number,
        'caller_id': caller.id,
        'caller_username': caller.username,
        'caller_full_name': caller.full_name,
        'requested_at': now.isoformat(timespec='seconds'),
    }
    filename = f'pr-{pr_number}-{now.strftime("%Y%m%dT%H%M%S")}-{caller.id}.json'
    request_file = REVIEW_QUEUE_DIR / filename

    try:
        REVIEW_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
        request_file.write_text(json.dumps(payload, ensure_ascii=False))
    except Exception:
        logger.exception(f'/review failed to write queue file {request_file}')
        await message.reply('❌ Не вдалося записати запит у чергу. Перевір логи.')
        return

    logger.info(f'/review queued payload={payload} file={request_file}')
    await message.reply(
        f'✅ Запит на review PR #{pr_number} поставлено в чергу.\n'
        f'Файл: {filename}\n'
        f'Результат зʼявиться на GitHub за кілька хвилин.'
    )


@router.message(Command('check_pr'))
async def cmd_check_pr(message: types.Message, logger):
    caller = message.from_user
    logger.info(f'/check_pr called by {caller.id} ({caller.full_name}): {message.text!r}')

    user = await check_access(message, [Level.admin, Level.vip])
    if not user:
        return

    args = message.text.split()
    if len(args) != 2 or not args[1].isdigit() or int(args[1]) <= 0:
        logger.warning(f'/check_pr bad args: {args}')
        await message.reply('Формат: /check_pr <pr_number>')
        return
    pr_number = int(args[1])

    today = datetime.now(timezone.utc).date()
    queue_root = REVIEW_QUEUE_DIR.parent
    records = []
    for subdir in ('pending', 'processed'):
        d = queue_root / subdir
        if not d.exists():
            continue
        for f in sorted(d.glob('*.json')):
            try:
                data = json.loads(f.read_text())
            except Exception:
                continue
            if data.get('pr_number') != pr_number or data.get('caller_id') != caller.id:
                continue
            rq_str = str(data.get('requested_at', '')).replace('Z', '+00:00')
            try:
                rq_dt = datetime.fromisoformat(rq_str)
            except ValueError:
                continue
            if rq_dt.astimezone(timezone.utc).date() != today:
                continue
            records.append((subdir, data))

    if not records:
        await message.reply(f'Нема записів для PR #{pr_number} сьогодні від тебе.')
        return

    records.sort(key=lambda r: r[1].get('requested_at', ''))
    icons = {'success': '✅', 'failed': '❌'}
    lines = [f'📋 PR #{pr_number} сьогодні ({caller.full_name}) — {len(records)} запис(ів):', '']
    for i, (state, data) in enumerate(records, 1):
        status = data.get('status', state)
        icon = icons.get(status, '⏳' if state == 'pending' else '⌛')
        line = f'{i}. {icon} {status} | req={data.get("requested_at", "?")}'
        if data.get('completed_at'):
            line += f' | done={data["completed_at"]}'
        if 'exit_code' in data:
            line += f' | rc={data["exit_code"]}'
        lines.append(line)

    await message.reply('\n'.join(lines))
