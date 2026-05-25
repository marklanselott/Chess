from telethon import events

from api import get_token, reg_user, get_user_by_unique
from menus import main_menu
from state import user_state
from handlers.profile import handle_profile_step
from handlers.friends import handle_friend_step


def register_fsm_handlers(bot):
    bot.add_event_handler(handle_user_text, events.NewMessage)


async def handle_user_text(event):
    if not event.text or event.text.startswith('/'):
        return

    state = user_state.get(event.sender_id)
    if not state:
        return

    step = state.get("step")
    text = event.text.strip()

    auth_steps = {
        "reg_name",
        "reg_unique",
        "reg_password",
        "auth_unique",
        "auth_password",
    }
    profile_steps = {
        "wait_new_name",
        "wait_new_unique",
        "wait_new_password",
        "wait_delete_login",
        "wait_delete_password_final",
    }
    friend_steps = {"wait_friend_nickname"}

    if step in auth_steps:
        await handle_auth_step(event, step, text)
    elif step in profile_steps:
        await handle_profile_step(event, step, text)
    elif step in friend_steps:
        await handle_friend_step(event, step, text)


async def handle_auth_step(event, step, text):
    if step == "reg_name":
        if len(text) < 2 or len(text) > 16:
            await event.reply("❌ Ім'я має бути від 2 до 16 символів. Спробуйте ще раз:")
            return

        if not text.isalnum():
            await event.reply("❌ Ім'я може містити тільки літери та цифри!")
            return

        user_state[event.sender_id]["first_name"] = text
        user_state[event.sender_id]["step"] = "reg_unique"
        await event.respond(f"Приємно познайомитися, {text}! Придумайте логін (unique):")

    elif step == "reg_unique":
        if not text.isalnum():
            await event.reply("❌ Логін може містити тільки літери та цифри!")
            return

        if len(text) < 2 or len(text) > 16:
            await event.reply("❌ Логін має бути від 2 до 16 символів:")
            return

        user_state[event.sender_id]["unique"] = text
        user_state[event.sender_id]["step"] = "reg_password"
        await event.respond("🔒 Тепер придумайте пароль (від 6 до 12 символів):")

    elif step == "reg_password":
        if len(text) < 6 or len(text) > 12:
            await event.reply("❌ Пароль має бути від 6 до 12 символів. Введіть ще раз:")
            return

        data = user_state[event.sender_id]
        token = get_token()

        try:
            reg_user(
                token=token,
                unique=data["unique"],
                first_name=data["first_name"],
                password=text,
                tg_id=event.sender_id,
            )

            user_state[event.sender_id] = None
            await event.respond(f"✅ Реєстрацію завершено! Ласкаво просимо, {data['first_name']}.", buttons=main_menu)
        except Exception as e:
            await event.respond("⚠️ Виникла помилка під час реєстрації. Спробуйте пізніше.")
            print(f"Reg error: {e}")

    elif step == "auth_unique":
        user_state[event.sender_id]["login_try"] = text
        user_state[event.sender_id]["step"] = "auth_password"
        await event.respond("🔒 Введіть ваш пароль:")

    elif step == "auth_password":
        login = user_state.get(event.sender_id, {}).get("login_try")
        password = text
        token = get_token()

        user_data = get_user_by_unique(token, login)

        if user_data and str(user_data.get("password")) == password:
            user_state[event.sender_id] = None
            await event.respond(f"✅ Вхід виконано! Привіт, {user_data.get('first_name')}!", buttons=main_menu)
        else:
            await event.respond("❌ Помилка: логін або пароль неправильні. Спробуйте знову через /start")
            user_state[event.sender_id] = None