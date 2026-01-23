from pyrogram import Client
from environs import Env

env = Env()
env.read_env()

API_ID = env.int("TG_API_ID")
API_HASH = env.str("TG_API_HASH")

with Client(
        name="user_session",
        api_id=API_ID,
        api_hash=API_HASH
) as app:
    session_string = app.export_session_string()
    print("\n=== TELEGRAM SESSION STRING ===\n")
    print(session_string)
