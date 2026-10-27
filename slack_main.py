"""Slack front-end for the same download core as the Telegram bot.

Paste a YouTube / Instagram / TikTok link in a DM or a channel the bot is in →
the bot downloads it via Bot_Func.get_dwn_media and uploads the file in a thread.
Runs in Socket Mode: no public URL needed. Setup → README "Slack bot".
"""

import asyncio
import html
import os
import re
from pathlib import Path
from types import SimpleNamespace

import loguru
from dotenv import load_dotenv
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_bolt.async_app import AsyncApp

from handlers.media_bot import _YDL_OPTS_BY_MODE
from src import utils as ut
from src.bot import Bot_Func

SUPPORTED_DOMAINS = ("youtu.be", "youtube.com", "instagram.com", "tiktok.com")
# Slack sends links as <https://url> or <https://url|label>
_SLACK_LINK_RE = re.compile(r"<(https?://[^|>]+)(?:\|[^>]*)?>")


def extract_url(text: str | None) -> str | None:
    """First supported media link in a Slack message text, or None."""
    for url in _SLACK_LINK_RE.findall(text or ""):
        url = html.unescape(url)  # Slack escapes & as &amp;
        if any(d in url for d in SUPPORTED_DOMAINS):
            return url.split("&list")[0]
    return None


class SlackMsg:
    """Duck-types the parts of aiogram Message that Bot_Func.get_dwn_media uses:
    .text, .chat.id, answer/reply/edit_text/delete. Everything goes into one thread."""

    def __init__(self, client, channel, ts, text="", thread_ts=None):
        self.client = client
        self.channel = channel
        self.ts = ts
        self.text = text
        self.thread_ts = thread_ts
        self.chat = SimpleNamespace(id=channel)

    async def answer(self, text):
        r = await self.client.chat_postMessage(
            channel=self.channel, thread_ts=self.thread_ts, text=text
        )
        return SlackMsg(self.client, self.channel, r["ts"], text, self.thread_ts)

    reply = answer

    async def edit_text(self, text):
        await self.client.chat_update(channel=self.channel, ts=self.ts, text=text)

    async def delete(self):
        await self.client.chat_delete(channel=self.channel, ts=self.ts)


load_dotenv()
app = AsyncApp(token=os.getenv("SLACK_BOT_TOKEN"))
logger = ut.setup_logger(loguru.logger, data_name="slack")
bot_func = Bot_Func(log=logger, root_prj=Path(__file__).parent.absolute())


# ponytail: no per-user MB limits / registration here — workspace membership is
# the access gate. Port src/Users.py limits keyed by Slack user id if needed.
@app.message(re.compile("|".join(re.escape(d) for d in SUPPORTED_DOMAINS)))
async def on_link(message, client):
    if message.get("bot_id"):
        return
    url = extract_url(message.get("text"))
    if not url:
        return
    user = message.get("user")
    thread = message.get("thread_ts") or message["ts"]
    msg = SlackMsg(client, message["channel"], message["ts"], url, thread)
    logger.info(f"Slack link {url} from {user} in {message['channel']}")

    opts = {**_YDL_OPTS_BY_MODE["social"], "outtmpl": f"media/slack_{user}/%(title)s.%(ext)s"}
    res = await bot_func.get_dwn_media(opts, msg, user_id=user)
    if not res:
        return  # get_dwn_media already replied with the error
    loc_media, file_size = res
    try:
        await client.files_upload_v2(
            channel=message["channel"],
            thread_ts=thread,
            file=loc_media,
            title=os.path.basename(loc_media),
            initial_comment=f"{url}\n{ut.h_readable(file_size)}",
        )
        logger.success(f"Slack upload done {loc_media} → {user}")
    except Exception as e:
        logger.exception(f"Slack upload failed: {e}")
        await msg.reply(f"An error occurred while sending the file: {e}")
    finally:
        ut.delete_video_file(loc_media)


async def main():
    await AsyncSocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start_async()


if __name__ == "__main__":
    asyncio.run(main())
