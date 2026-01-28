from pyrogram import Client
from environs import Env

env = Env()
env.read_env()


def build_client() -> Client:
    return Client(
        name="user_session",
        api_id=env.int("TG_API_ID"),
        api_hash=env.str("TG_API_HASH"),
        session_string=env.str("TG_SESSION_STRING"),
        in_memory=True,
    )
