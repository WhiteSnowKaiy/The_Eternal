from decouple import config

BOT_PREFIX: str = config("sokkatto_prefix", "!") # type: ignore

BOT_TOKEN: str = config("sokkatto_token", None) # type: ignore
if BOT_TOKEN is None:
    raise RuntimeError("No token specified!")
if BOT_TOKEN == "bot.token.here" or BOT_TOKEN.count(".") != 2:
    raise RuntimeError("Invalid token specified!")
DEFAULT_ROLE: int = config("default_role", None)
if DEFAULT_ROLE is None:
    raise RuntimeError("No role ID specified")
GUILD: int = config("guild", None)
if GUILD is None:
    raise RuntimeError("No guild ID specified")
WELCOME_CHANNEL: int = config("welcome_channel", None)
if WELCOME_CHANNEL is None:
    raise RuntimeError("No welcome channel ID specified")