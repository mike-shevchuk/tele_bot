# tele_bot
## Slack bot

`slack_main.py` — the same download core (`src/bot.py`) behind Slack instead of
Telegram. Paste a YouTube / Instagram / TikTok link in a DM to the bot (or in a
channel it was invited to) → it downloads and uploads the file in a thread.

Setup (once, ~5 min):

1. https://api.slack.com/apps → **Create New App → From an app manifest** →
   pick your workspace → paste:

   ```yaml
   display_information:
     name: med_soc_bot
   features:
     bot_user:
       display_name: med_soc_bot
       always_online: true
     app_home:
       messages_tab_enabled: true
       messages_tab_read_only_enabled: false
   oauth_config:
     scopes:
       bot: [chat:write, files:write, channels:history, groups:history, im:history, mpim:history]
   settings:
     event_subscriptions:
       bot_events: [message.channels, message.groups, message.im, message.mpim]
     socket_mode_enabled: true
   ```

2. **Basic Information → App-Level Tokens → Generate** with scope
   `connections:write` → copy `xapp-…` into `.env` as `SLACK_APP_TOKEN`.
3. **Install App → Install to Workspace** → copy the Bot User OAuth Token
   `xoxb-…` into `.env` as `SLACK_BOT_TOKEN`.
4. `just run-slack`. In a channel, `/invite @med_soc_bot` first.

Not ported yet (Telegram-only): YouTube quality buttons, `/start` + MB limits,
voice → text (STT), inline search.
