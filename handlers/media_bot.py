from datetime import datetime
from aiogram import F, types, Router
from src.bot import CommonParamYouTube
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
    info_wait_button = await bot_msg.reply(f"✅ Download successful!\nSending video", disable_notification=True)
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
    title = cb1.title
    vid_data = cb1.vid_data
    # logger.trace(f'{cb1=}')

    logger.info(f'callback catch {cb1}')
