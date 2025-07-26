# scripts.py

class Scripts(object):
    WELCOME_TEXT = """
<blockquote>Hi {first_name}! Welcome 🎉</blockquote>
<blockquote>
  🔎 Search for your favorite anime<br>
  📚 Explore our extensive anime library<br>
  📥 Download episodes in multiple qualities<br>
  📋 Add anime to your watchlist<br><br>
  ⭐ Manage your personal watchlist
  Get started with the buttons below!
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
- /search <anime name> — Search for anime (you can also just send the anime name)
- /index — Browse anime alphabetically
- /recent — View recently updated anime
- /ongoing — See currently airing/releasing anime
- /watchlist — View and manage your saved anime
- /todayschedule — View today's anime release schedule
- /request <anime name> — Request an anime to be added
- /help — Show this help message

📌 *Usage Tips:*
- Just send an anime name to search instantly
- In groups, use `/search <anime>` to look up shows
- Use inline mode anywhere: `@{bot_name} <anime name>`
- Save ongoing/releasing anime in your watchlist to get back to them quickly
- Files auto-delete after *{delete_timer} minutes*
- For support and updates, join our group: [Click here]({group_link})

🔐 *Premium Features:*
- 🚀 Unlimited downloads
- 🎬 Access to adult content (if enabled)
- 🎧 Higher quality video options
- ⚡ Faster response and download priority

🆘 *Need Help?*
- Reach out to admins in our support group or ask your question there!
"""


    ANIME_INFO_TEXT = """
<font face="Georgia" size="4"><b>{title}</b></font><br>
<font face="Arial" size="2">
✦ <b>Type:</b> <i>{type_display}</i> &nbsp; | &nbsp; <b>Status:</b> <i>{status}</i> &nbsp; | &nbsp; <b>Score:</b> <i>{score_html}</i><br>
✦ <b>Episodes:</b> <i>{episodes}{ep_text}</i> &nbsp; | &nbsp; <b>Year:</b> <i>{year}</i><br>
✦ <b>Genres:</b> <i>{genres}</i><br><br>
✦ <b>Synopsis:</b><br>
<i>{synopsis}</i>
</font>
"""
