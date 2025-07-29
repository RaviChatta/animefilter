# scripts.py

class Scripts(object):
    WELCOME_TEXT = """
<blockquote><strong>Hi {first_name}, welcome to Anime Downloader! 🎉</strong></blockquote>

<blockquote>
Easily manage and enjoy your favorite anime with the tools below:<br><br>
✔️ Search for any anime title instantly<br>
✔️ Browse our complete anime library<br>
✔️ Download episodes in multiple quality options<br>
✔️ Add shows to your personal watchlist<br>
✔️ Keep track of what you’re watching with ease<br><br>
Ready to get started? Use the buttons below to begin!
</blockquote>
"""



    HELP_TEXT = """📚 *{bot_name} Help Guide* 📚

🌟 *Main Features:*
- 🔍 Search and download anime episodes
- 📺 Browse by title or recently added
- ⭐ Save anime to your personal watchlist (including ongoing/releasing shows)
- 💾 Multiple quality options
- 📅 View today's airing schedule
- 📥 Request anime directly from the bot

🛠 *Available Commands:*
- /start — Show main menu
— Search for anime (you can also just send the anime name)
- /search <anime name> (in group use by command to search)
- /quote – Get anime quotes for a bit of inspiration 📖
- /index — Browse anime alphabetically
- /ongoing — See currently airing/releasing anime
- /watchlist — View and manage your saved anime
- /todayschedule — View today's anime release schedule
- /request <anime name> — Request an anime to be added
- /help — Show this help message

📌 *Usage Tips:*
- Just send an anime name to search instantly
- In groups, use `/search <anime>` to look up shows
- Save ongoing/releasing/upcoming anime in your watchlist to get back to them quickly
- Files auto-delete after *{delete_timer} minutes*
- For support and updates, join our group: [Click here]({https://t.me/TFIBOTS_SUPPORT})

🔐 *Premium Features:*
- 🚀 Unlimited downloads
- 🎬 Access to adult content (if enabled) and users want 
- 🎧 Higher quality video options
- ⚡ Faster response and download priority

🆘 *Need Help?*
- Reach out to admins in our support group or ask your question there!
- Developed by [R]({https://t.me/Raaaaavi})
"""


    ANIME_INFO_TEXT = """
<font face="Georgia" size="4"><b>{title}</b></font><br>
<font face="Arial" size="2">
✦ <b>Type:</b> <i>{type_display}</i> &nbsp; | &nbsp; <b>Status:</b> <i>{status}</i><br>
✦ <b>Episodes:</b> <i>{episodes}{ep_text}</i> &nbsp; | &nbsp; <b>Year:</b> <i>{year}</i><br>
✦ <b>Genres:</b> <i>{genres}</i><br><br>
✦ <b>Synopsis:</b><br>
<i>{synopsis}</i>
</font>
"""
