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
            await event.reply("❌ Имя должно быть от 2 до 16 символов. Попробуйте еще раз:")
            return

        if not text.isalnum():
            await event.reply("❌ Имя может содержать только буквы и цифры!")
            return

        user_state[event.sender_id]["first_name"] = text
        user_state[event.sender_id]["step"] = "reg_unique"
        await event.respond(f"Приятно познакомиться, {text}! Придумайте логин (unique):")

    elif step == "reg_unique":
        if not text.isalnum():
            await event.reply("❌ Логин может содержать только буквы и цифры!")
            return

        if len(text) < 2 or len(text) > 16:
            await event.reply("❌ Логин должен быть от 2 до 16 символов:")
            return

        user_state[event.sender_id]["unique"] = text
        user_state[event.sender_id]["step"] = "reg_password"
        await event.respond("🔒 Теперь придумайте пароль (от 6 до 12 символов):")

    elif step == "reg_password":
        if len(text) < 6 or len(text) > 12:
            await event.reply("❌ Пароль должен быть от 6 до 12 символов. Введите еще раз:")
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
            await event.respond(f"✅ Регистрация завершена! Добро пожаловать, {data['first_name']}.", buttons=main_menu)
        except Exception as e:
            await event.respond("⚠️ Произошла ошибка при регистрации. Попробуйте позже.")
            print(f"Reg error: {e}")

    elif step == "auth_unique":
        user_state[event.sender_id]["login_try"] = text
        user_state[event.sender_id]["step"] = "auth_password"
        await event.respond("🔒 Введите ваш пароль:")

    elif step == "auth_password":
        login = user_state.get(event.sender_id, {}).get("login_try")
        password = text
        token = get_token()

        user_data = get_user_by_unique(token, login)

        if user_data and str(user_data.get("password")) == password:
            user_state[event.sender_id] = None
            await event.respond(f"✅ Вход выполнен! Привет, {user_data.get('first_name')}!", buttons=main_menu)
        else:
            await event.respond("❌ Ошибка: логин или пароль неверны. Попробуйте снова через /start")
            user_state[event.sender_id] = None
