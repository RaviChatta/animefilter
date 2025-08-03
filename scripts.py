# scripts.py

class Scripts(object):
    WELCOME_TEXT = """
<blockquote><b>Hi {first_name}, welcome to <u>Anime Downloader</u>! 🎉</b></blockquote>
<blockquote>
<b>Your anime journey starts here:</b><br><br>
<b>•</b> <i>Search for any anime title instantly</i><br>
<b>•</b> <i>Browse the full anime collection</i><br>
<b>•</b> <i>Download episodes in various quality options</i><br>
<b>•</b> <i>Save shows to your personal watchlist</i><br>
<b>•</b> <i>Track your ongoing  anime easily</i><br><br>
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
- /myplan - to see premium and max daily limit
- /help — Show this help message

📌 *Usage Tips:*
- Just send an anime name to search instantly
- In groups, use `/search <anime>` to look up shows
- Save ongoing/releasing/upcoming anime in your watchlist to get back to them quickly
- Files auto-delete after *{delete_timer} minutes*
- For support and updates, join our group: [Click here]({group_link})

🔐 *Premium Features:*
- 🚀 Unlimited downloads
- 🎬 Access to adult content (if enabled) and users want 
- 🎧 Higher quality video options
- ⚡ Faster response and download priority

🆘 *Need Help?*
- Reach out to admins in our support group or ask your question there!
- Developed by [RAVI]({developer_link})
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
