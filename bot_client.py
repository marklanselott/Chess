from telethon import TelegramClient
from config import apiId, apiHash, botToken

bot = TelegramClient("session_file", apiId, apiHash)
bot.start(bot_token=botToken)
