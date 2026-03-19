import os
from io import BytesIO

import httpx
from aiogram import Bot, Router, types, F

router_stt = Router()

STT_HOST = os.getenv("STT_HOST", "192.168.50.48")
STT_PORT = os.getenv("STT_PORT", "8069")
STT_LANG = os.getenv("STT_LANG", "uk")
STT_MODEL = os.getenv("STT_MODEL", "large-v3-turbo")
STT_URL = f"http://{STT_HOST}:{STT_PORT}/transcribe"

STT_TIMEOUT = httpx.Timeout(connect=5, read=300, write=30, pool=5)

TG_MSG_LIMIT = 4096


async def _transcribe(audio: bytes, suffix: str) -> httpx.Response:
    """Send audio to STT service."""
    async with httpx.AsyncClient(timeout=STT_TIMEOUT) as client:
        return await client.post(
            STT_URL,
            params={"language": STT_LANG, "model": STT_MODEL},
            files={"file": (f"audio{suffix}", audio)},
        )


@router_stt.message(F.voice | F.audio)
async def handle_voice(message: types.Message, bot: Bot, logger):
    """Download voice/audio from Telegram -> send to STT service -> reply with text."""

    if message.voice:
        file_id = message.voice.file_id
        suffix = ".ogg"
    else:
        file_id = message.audio.file_id
        suffix = f".{message.audio.file_name.rsplit('.', 1)[-1]}" if message.audio.file_name else ".mp3"

    logger.info(f"STT request from {message.from_user.id}")

    wait_msg = await message.reply("Транскрибую аудіо...", disable_notification=True)

    try:
        tg_file = await bot.get_file(file_id)
        buf = BytesIO()
        await bot.download_file(tg_file.file_path, buf)
        audio_bytes = buf.getvalue()

        resp = await _transcribe(audio_bytes, suffix)

        if resp.status_code != 200:
            logger.error(f"STT error {resp.status_code}: {resp.text}")
            await wait_msg.edit_text(f"STT error: {resp.status_code}")
            return

        data = resp.json()
        text = data.get("text", "").strip()
        proc_time = data.get("processing_time", "?")

        if not text:
            await wait_msg.edit_text("Не вдалося розпізнати текст.")
            return

        reply = f"{text}\n\n{proc_time}s"
        if len(reply) > TG_MSG_LIMIT:
            reply = reply[: TG_MSG_LIMIT - 3] + "..."
        await wait_msg.edit_text(reply)
        logger.success(f"STT done for {message.from_user.id}: {proc_time}s, len={len(text)}")

    except httpx.ConnectError:
        logger.error(f"STT service unreachable at {STT_URL}")
        await wait_msg.edit_text(f"STT сервіс недоступний ({STT_HOST}:{STT_PORT})")
    except (httpx.RemoteProtocolError, httpx.ReadError) as e:
        logger.error(f"STT server disconnected: {e}")
        await wait_msg.edit_text(f"STT сервер розірвав з'єднання. Спробуйте ще раз.")
    except Exception as e:
        logger.exception(f"STT failed: {e}")
        await wait_msg.edit_text(f"Помилка: {e}")
