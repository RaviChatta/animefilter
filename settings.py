import os
class Settings:
    PREMIUM_MODE = False
    RESTRICT_ADULT = True
    MAX_DAILY_DOWNLOADS = {
        0: 3,   # Normal
        1: 20,  # Premium
        2: -1   # H-Premium
    }
    DELETE_TIMER_MINUTES = 1
    MAX_SEARCH_RESULTS = 10
    MAX_EPISODES_PER_PAGE = 30
    PM_SEARCH = True
    PROTECT_CONTENT = False
    RATE_LIMIT = 5  # messages per second
    OWNERS = list(map(int, os.getenv("OWNERS", "").split(","))) if os.getenv("OWNERS") else []

# Singleton instance
config = Settings()
