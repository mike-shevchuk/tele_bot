from datetime import datetime
from aiogram import F, Bot, types, Router
from src.bot import CommonParamYouTube, CommonParamInline
import jinja2
from src import utils as ut

from handlers.test_bot import CommonParamTick


router_med = Router()
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
        #HACK: delete later
        if loc_media.endswith('mp4'):
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




@router_med.callback_query(F.data.startswith("tick"))
async def handle_callback_reel(callback_query: types.CallbackQuery, logger, user_data, bot_func):
    cb1 = CommonParamTick.unpack(callback_query.data)
    logger.info(f'callback catch {cb1}')
    await callback_query.answer("This button is outdated, use the new inline search.")


@router_med.callback_query(F.data.startswith("idl"))
async def handle_inline_download(callback_query: types.CallbackQuery, logger, user_data, bot_func, cfg, bot: Bot):
    cb = CommonParamInline.unpack(callback_query.data)
    data = user_data.get(cb.key)
    logger.info(f'Inline download callback: {cb.key=} {data=}')

    if not data:
        await callback_query.answer("Link expired. Try searching again.")
        return

    # Support both old format (string) and new format (dict)
    if isinstance(data, str):
        url = data
        mode = 'social'
        media_title = ''
    else:
        url = data['url']
        mode = data.get('mode', 'social')
        media_title = data.get('title', '')

    user_bot = callback_query.from_user
    user_id = user_bot.id
    df_t = ut.get_user_by_id(user_id)
    if df_t.empty:
        await callback_query.answer("You are not registered. Send /start to the bot first.")
        return

    user = ut.pandas2pydentic(df_t)
    available_memory = user.level.value - user.use_memory
    if available_memory < 0:
        await callback_query.answer("You've exceeded your download limit.")
        return

    await callback_query.answer("Downloading...")

    inline_msg_id = callback_query.inline_message_id
    if inline_msg_id:
        try:
            await bot.edit_message_text(
                "Downloading...",
                inline_message_id=inline_msg_id,
            )
        except Exception:
            pass

    status_msg = await bot.send_message(user_id, "Start downloading ...")

    environment = jinja2.Environment()
    answer_template = environment.from_string(
        "@{{bot_name}}\n\nУ тебе лишилося {{avail_mem}}\n\n{{progress_bar_str_value}}\n\n{{url}}"
    )

    current_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    loc_media = f"media/{user_id}/{current_date}"

    if mode == 'audio':
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': loc_media,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
    elif mode == 'video':
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': loc_media,
            'merge_output_format': 'mp4',
        }
    else:  # social
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': loc_media,
            'merge_output_format': 'mp4',
        }

    res = await bot_func.get_dwn_media(ydl_opts, status_msg, youtubeLink=url)
    if not res:
        await bot.send_message(user_id, 'Failed to download. Check the link and try again.')
        if inline_msg_id:
            try:
                await bot.edit_message_text(
                    "Download failed",
                    inline_message_id=inline_msg_id,
                )
            except Exception:
                pass
        logger.warning(f'Failed inline download {url} for user {user_id}')
        return
    loc_media, file_size = res

    available_memory -= file_size
    answer_cap = answer_template.render(
        bot_name=cfg.shared_vars.bot_name,
        avail_mem=ut.h_readable(available_memory),
        progress_bar_str_value=ut.progress_bar_str(user.use_memory, user.level.value),
        url=url,
    )

    try:
        is_audio = loc_media.endswith('mp3') or loc_media.endswith('m4a')

        if is_audio:
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

        # Replace the inline message with the actual video/audio
        logger.info(f'inline_msg_id={inline_msg_id}, has_video={bool(dm_msg.video)}, '
                     f'has_document={bool(dm_msg.document)}, has_audio={bool(dm_msg.audio)}')
        if inline_msg_id and dm_msg:
            file_id = None
            if is_audio and dm_msg.audio:
                file_id = dm_msg.audio.file_id
                media = types.InputMediaAudio(media=file_id, caption=f'@{cfg.shared_vars.bot_name}')
            elif dm_msg.video:
                file_id = dm_msg.video.file_id
                media = types.InputMediaVideo(media=file_id, caption=answer_cap)
            elif dm_msg.document:
                file_id = dm_msg.document.file_id
                media = types.InputMediaDocument(media=file_id, caption=answer_cap)
            else:
                media = None

            logger.info(f'edit_message_media: file_id={bool(file_id)}, media_type={type(media).__name__ if media else None}')
            if media:
                try:
                    await bot.edit_message_media(
                        media=media,
                        inline_message_id=inline_msg_id,
                    )
                    await dm_msg.delete()
                    logger.info('Inline message replaced with media successfully')
                except Exception as e:
                    logger.error(f'edit_message_media failed: {e}')

    except Exception as e:
        await bot.send_message(user_id, f"Error sending media: {e}")

    user.use_memory += file_size
    ut.update_row(user)

    loc_match = glob.glob(os.path.join('.', f'{loc_media}*'))
    if loc_match:
        ut.delete_video_file(loc_match[0])

    user_data.pop(cb.key, None)
