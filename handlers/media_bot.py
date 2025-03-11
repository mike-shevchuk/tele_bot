from datetime import datetime
from aiogram import F, Bot, Dispatcher, types, Router
from src.bot import CommonParam
from src import utils as ut
import os
import glob



router_med = Router()
BOT_NAME = 'med_soc_bot'



# @dp.callback_query(CommonParam.filter(F.vid_data == "vid_140"))
# @dp.callback_query(CommonParam.filter(F.vid_data.startwith("vid")))
@router_med.callback_query(F.data.startswith("vid"))
async def handle_callback(callback_query: types.CallbackQuery, logger, user_data, bot_func):
    # Extract the format ID from the callback data
    # dt = callback_query.data['vid_data']
    # vid_dt = dt['vid_data']
    # cb1.unpack('my:demo:42')
    cb1 = CommonParam.unpack(callback_query.data)
    title = cb1.title
    # id = cb1.id
    vid_dt = cb1.vid_data
    # vid_dt = callback_query.data
    # id_dt = dt['id']
    # title_dt = dt['title']
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
    available_memory = user.level.value - user.use_memory

    current_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    # TODO: loc video must to be with real name
    full_name_video = current_date +'__'+ title
    loc_media = f"media/{user.id}/{full_name_video}"
    # loc_media = f"media/{user.id}/{title_dt}" 

    # Options for yt-dlp without post-processing
    ydl_opts = {
        # 'format': f'{format_id}+bestaudio/best[ext=m4a]',  # Combine video format with best audio  
        # #'format': 'bestvideo[ext=mp4]+bestaudio[ext=mp4]/mp4+best[height<=480]', 
        'format': f'{format_id}+m4a/bestaudio/best',
        'outtmpl': loc_media,
        # 'outtmpl': '%(title)s.%(ext)s'
    }

    loc_media, file_size = await bot_func.get_dwn_media(ydl_opts, bot_msg, youtubeLink=youtube_url)
    info_wait_button = await bot_msg.reply(f"✅ Download successful!\nSending video")
    loc_match = glob.glob(os.path.join('.', f'{loc_media}*'))
    assert loc_match
    loc_video  = loc_match[0]
    try:
        #HACK: delete later
        if loc_media.endswith('mp4'):
            await bot_msg.answer_video(video=types.FSInputFile(loc_media), 
                                       caption = f'@{BOT_NAME}\n\n' + 
                                                 f'У тебе лишилося {
                                                     ut.h_readable(
                                                         available_memory-file_size
                                                         )
                                                     }' +
                                                 f'\n\n{youtube_url}', 
                                        title=title)
        else:
            await bot_msg.answer_audio(audio=types.FSInputFile(loc_media),
                                    caption = f'@{BOT_NAME}',
                                    title=title)
        # If audio only send message.answer_musick or answer_audio check it
        # ut.recalc_used_mem(loc_video, user)
        user.use_memory += file_size
        ut.update_row(user)
    except Exception as e:
        await bot_msg.reply(f"An error occurred while sending the video: {e}")
    
    
    ut.delete_video_file(loc_video)
    


    await bot_msg.delete()
    await info_wait_button.delete()

