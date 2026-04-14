from datetime import datetime
import os
from aiogram import F, Bot, types, Router
from src.bot import CommonParamYouTube, CommonParamInline
import jinja2
from src import utils as ut


router_med = Router()

_YDL_OPTS_BY_MODE = {
    'audio': {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    },
    'video': {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'merge_output_format': 'mp4',
    },
    'social': {
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
    },
}

_CAPTION_TEMPLATE = jinja2.Environment().from_string(
    "@{{bot_name}}\n\nУ тебе лишилося {{avail_mem}}\n\n{{progress_bar_str_value}}\n\n{{url}}"
)
# BOT_NAME = 'med_soc_bot'



# @dp.callback_query(CommonParamYouTube.filter(F.vid_data == "vid_140"))
# @dp.callback_query(CommonParamYouTube.filter(F.vid_data.startwith("vid")))
@router_med.callback_query(F.data.startswith("vid"))
async def handle_callback(callback_query: types.CallbackQuery, logger, user_data, bot_func, cfg):
    cb1 = CommonParamYouTube.unpack(callback_query.data)
    title = cb1.title
    environment = jinja2.Environment()

    answer_template = environment.from_string(
        "@{{bot_name}}\n\n{{name}}\n\nУ тебе лишилося {{avail_mem}}\n\n{{progress_bar_str_value}}\n\n{{youtube_url}}"
    )
    # TODO: make norm translate for cyrilic
    if ut.is_ltn(title):
        ...
    vid_dt = cb1.vid_data
    logger.trace(f'{cb1=}')
    format_id = vid_dt.split('_')[1]
    
    user_bot = callback_query.from_user
    youtube_url = user_data.get(user_bot.id)  # Retrieve the saved link
    bot_msg = callback_query.message

    if not youtube_url:
        # TODO: add logger
        await bot_msg.reply(f"Помилка: URL не знайдено. {youtube_url}")
        return

    user_df = ut.get_user_by_id(user_bot.id)
    user = ut.pandas2pydentic(user_df)

    total_mem_user_level = user.level.value
    used_memory_per_user = user.use_memory
    available_memory = total_mem_user_level - used_memory_per_user  
    progress_bar_str_value = ut.progress_bar_str(used_memory_per_user, total_mem_user_level)

    current_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    # TODO: loc video must to be with real name
    full_name_video = current_date +'__'+ title
    loc_media = f"media/{user.id}/{full_name_video}.%(ext)s"

    # Options for yt-dlp without post-processing
    ydl_opts = {
        # 'format': f'{format_id}+bestaudio/best[ext=m4a]',  # Combine video format with best audio  
        # #'format': 'bestvideo[ext=mp4]+bestaudio[ext=mp4]/mp4+best[height<=480]', 
        'format': f'{format_id}+bestaudio[ext=m4a]/{format_id}+bestaudio/best',
        'outtmpl': loc_media,
        # 'outtmpl': '%(title)s.%(ext)s'
    }

    res = await bot_func.get_dwn_media(ydl_opts, bot_msg, youtubeLink=youtube_url)
    if not res:
        await bot_msg.answer('Не вдалося завантажити. Перевір посилання і спробуй ще раз.')
        logger.warning(f'Failed to download media with link {youtube_url}\n\n\n')
        return
    loc_media, file_size = res
    info_wait_button = await bot_msg.reply("✅ Download successful!\nSending video", disable_notification=True)
    # loc_match = glob.glob(os.path.join('.', f'{loc_media}*'))
    # assert loc_match
    # loc_video  = loc_match[0]
    answer_cap = answer_template.render(
        bot_name = cfg.shared_vars.bot_name, 
        avail_mem = ut.h_readable(available_memory-file_size),
        progress_bar_str_value = progress_bar_str_value,
        youtube_url = youtube_url,
        name = title)
    try:
        ext = os.path.splitext(loc_media)[1].lower()
        if ext in ('.mp4', '.mkv', '.webm'):
            logger.info(f'Sending as video: {loc_media}')
            await bot_msg.answer_video(
                                        video=types.FSInputFile(loc_media),
                                        caption=answer_cap,
                                        title=title)
        else:
            logger.info(f'Sending as audio: {loc_media}')
            await bot_msg.answer_audio(audio=types.FSInputFile(loc_media),
                                    caption = f'@{cfg.shared_vars.bot_name}',
                                    title=title)
        # If audio only send message.answer_musick or answer_audio check it
        # ut.recalc_used_mem(loc_video, user)
        user.use_memory += file_size
        ut.update_row(user)
    except Exception as e:
        await bot_msg.reply(f"An error occurred while sending the video: {e}")
    
    
    ut.delete_video_file(loc_media)
    


    await bot_msg.delete()
    await info_wait_button.delete()




@router_med.callback_query(F.data.startswith("idl"))
async def handle_inline_download(callback_query: types.CallbackQuery, logger, user_data, bot_func, cfg, bot: Bot):
    cb = CommonParamInline.unpack(callback_query.data)
    data = user_data.get(cb.key)
    logger.info(f'Inline download callback: {cb.key=} {data=}')

    if not data:
        await callback_query.answer("Link expired. Try searching again.")
        return

    url = data['url']
    mode = data.get('mode', 'social')
    media_title = data.get('title', '')

    user_id = callback_query.from_user.id
    df_t = ut.get_user_by_id(user_id)
    if df_t.empty:
        await callback_query.answer("Ти не зареганий натисни /start")
        return

    user = ut.pandas2pydentic(df_t)
    available_memory = user.level.value - user.use_memory
    if available_memory < 0:
        await callback_query.answer("Ви використали свій ліміт на цей місяць")
        return

    await callback_query.answer("Downloading...")

    inline_msg_id = callback_query.inline_message_id
    if inline_msg_id:
        try:
            await bot.edit_message_text("Downloading...", inline_message_id=inline_msg_id)
        except Exception as e:
            logger.debug(f'edit inline status failed: {e}')

    status_msg = await bot.send_message(user_id, "Start downloading ...")

    loc_media = f"media/{user_id}/{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
    ydl_opts = {**_YDL_OPTS_BY_MODE[mode], 'outtmpl': loc_media}

    res = await bot_func.get_dwn_media(ydl_opts, status_msg, youtubeLink=url)
    await status_msg.delete()
    if not res:
        await bot.send_message(user_id, 'Не вдалося завантажити. Перевір посилання і спробуй ще раз.')
        if inline_msg_id:
            try:
                await bot.edit_message_text("Download failed", inline_message_id=inline_msg_id)
            except Exception as e:
                logger.debug(f'edit inline failure status failed: {e}')
        logger.warning(f'Failed inline download {url} for user {user_id}')
        return
    loc_media, file_size = res

    available_memory -= file_size
    answer_cap = _CAPTION_TEMPLATE.render(
        bot_name=cfg.shared_vars.bot_name,
        avail_mem=ut.h_readable(available_memory),
        progress_bar_str_value=ut.progress_bar_str(user.use_memory, user.level.value),
        url=url,
    )

    try:
        if mode == 'audio':
            dm_msg = await bot.send_audio(
                chat_id=user_id,
                audio=types.FSInputFile(loc_media),
                title=media_title or None,
                caption=f'@{cfg.shared_vars.bot_name}',
            )
        else:
            dm_msg = await bot.send_video(
                chat_id=user_id,
                video=types.FSInputFile(loc_media),
                caption=answer_cap,
            )

        if inline_msg_id and dm_msg:
            if mode == 'audio' and dm_msg.audio:
                media = types.InputMediaAudio(
                    media=dm_msg.audio.file_id,
                    caption=f'@{cfg.shared_vars.bot_name}',
                )
            elif dm_msg.video:
                media = types.InputMediaVideo(media=dm_msg.video.file_id, caption=answer_cap)
            elif dm_msg.document:
                media = types.InputMediaDocument(media=dm_msg.document.file_id, caption=answer_cap)
            else:
                media = None

            if media:
                try:
                    await bot.edit_message_media(media=media, inline_message_id=inline_msg_id)
                    await dm_msg.delete()
                except Exception as e:
                    logger.error(f'edit_message_media failed: {e}')

    except Exception as e:
        await bot.send_message(user_id, f"Error sending media: {e}")
        ut.delete_video_file(loc_media)
        user_data.pop(cb.key, None)
        return

    user.use_memory += file_size
    ut.update_row(user)
    ut.delete_video_file(loc_media)

    user_data.pop(cb.key, None)
