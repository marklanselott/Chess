from telethon import events
import asyncio

from chess_handler import ChessTest
from menus import main_menu, play_menu, level
from state import user_state

console_active = asyncio.Event()


def register_game_handlers(bot):
    bot.add_event_handler(play, events.CallbackQuery(data="play"))
    bot.add_event_handler(playback, events.CallbackQuery(data="play_back"))
    bot.add_event_handler(choosecolor, events.CallbackQuery(data="offline"))



async def play(event: events.CallbackQuery.Event):
    await event.edit("Выберите режим:", buttons=play_menu)


async def playback(event: events.CallbackQuery.Event):
    console_active.clear()
    await event.edit("Вернулись, выбирайте:", buttons=main_menu)


async def choosecolor(event: events.CallbackQuery.Event):
    await event.edit("Выберите уровень сложности", buttons=level)