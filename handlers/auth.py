from telethon import events

from api import get_token, get_user
from menus import authreg, main_menu
from state import user_state


def register_auth_handlers(bot):
    bot.add_event_handler(start, events.NewMessage(pattern='/start'))
    bot.add_event_handler(start_reg, events.CallbackQuery(data="userreg"))
    bot.add_event_handler(start_auth, events.CallbackQuery(data="userauth"))


async def start(event: events.NewMessage.Event):
    token = get_token()
    result = get_user(token, event.chat_id)

    if not result.get("searched"):
        await event.respond("Привет! Ты не зарегистрирован. Выбери действие:", buttons=authreg)
    else:
        user = result["searched"][0]
        await event.respond(f"С возвращением, {user.get('first_name')}!", buttons=main_menu)


async def start_reg(event):
    user_state[event.sender_id] = {"step": "reg_name"}
    await event.edit("📝 Введите ваше Имя:")


async def start_auth(event):
    user_state[event.sender_id] = {"step": "auth_unique"}
    await event.edit("🔑 Введите ваш логин (unique):")
