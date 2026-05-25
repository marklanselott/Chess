from telethon import events
import asyncio

from api import get_token, get_user, update_user, delete_user, get_user_stats
from menus import authreg, main_menu, profile_menu, remake_back
from state import user_state


def register_profile_handlers(bot):
    bot.add_event_handler(profile, events.CallbackQuery(data="profile"))
    bot.add_event_handler(nameremake, events.CallbackQuery(data="remake_name"))
    bot.add_event_handler(loginremake, events.CallbackQuery(data="remake_unique"))
    bot.add_event_handler(passwordremake, events.CallbackQuery(data="remake_password"))
    bot.add_event_handler(confirmdelete, events.CallbackQuery(data="confirm_delete"))
    bot.add_event_handler(remakeback, events.CallbackQuery(data="remake_back"))
    bot.add_event_handler(profileback, events.CallbackQuery(data="profile_back"))


async def profile(event: events.CallbackQuery.Event):
    token = get_token()
    tg_id = event.chat_id
    
    # 1. Спочатку робимо старий робочий запит за Telegram ID
    user_search_result = await asyncio.to_thread(get_user, token, tg_id)

    # Перевіряємо, чи знайшов бот юзера через старий метод
    if not user_search_result or not user_search_result.get("searched"):
        await event.answer("❌ Помилка: користувача не знайдено в базі даних.", alert=True)
        return

    # Витягуємо базові дані юзера
    user_base = user_search_result["searched"][0]
    
    # ДІСТАЄМО UUID З БАЗИ (поле "id" всередині searched)
    user_uuid = user_base.get("id") 
    
    if not user_uuid:
        await event.answer("❌ Помилка: не вдалося отримати UUID користувача.", alert=True)
        return

    # 2. Тепер смикаємо ендпоінт статистики, передаючи туди UUID
    stats_data = await asyncio.to_thread(get_user_stats, token, user_uuid)

    if stats_data and "user" in stats_data:
        user_info = stats_data["user"]
        first_name = user_info.get("first_name", "Не вказано")
        unique = user_info.get("unique", "Не вказано")
        
        # Забираємо статистику з верхнього рівня JSON
        rating = stats_data.get("rating", 0)
        games = stats_data.get("games_total", 0)
        wins = stats_data.get("wins", 0)
        losses = stats_data.get("losses", 0)
        wl = stats_data.get("win_loss_ratio", 0)

        profile_text = (
            f"👤 **Ваш профіль**\n\n"
            f"🆔 Логін: `{unique}`\n"
            f"📝 Ім'я: {first_name}\n"
            f"--- --- --- ---\n"
            f"♟ Ваш рейтинг: {rating}\n"
            f"👾 Кількість ігор: {games}\n"
            f"🏆 Перемог: {wins}\n"
            f"🏳️ Поразок: {losses}\n"
            f"📊 W/L: {wl}"
        )

        await event.edit(profile_text, buttons=profile_menu)
    else:
        await event.answer("❌ Помилка бекенду при отриманні статистики.", alert=True)


async def nameremake(event):
    user_state[event.sender_id] = {"step": "wait_new_name"}
    await event.edit("✏️ Введіть нове **Ім'я** (2-20 символів):", buttons=remake_back)


async def loginremake(event):
    user_state[event.sender_id] = {"step": "wait_new_unique"}
    await event.edit("✏️ Введіть новий **Логін** (2-16 символів, тільки букви та цифри):", buttons=remake_back)


async def passwordremake(event):
    user_state[event.sender_id] = {"step": "wait_new_password"}
    await event.edit("🔒 Введіть **новий пароль** (від 6 до 12 символів):", buttons=remake_back)


async def confirmdelete(event):
    user_state[event.sender_id] = {"step": "wait_delete_login"}
    await event.edit(
        "⚠️ **ВИДАЛЕННЯ АКАУНТУ**\n\nДля підтвердження введіть ваш **Логін (unique)**:",
        buttons=remake_back,
    )


async def remakeback(event):
    user_state[event.sender_id] = None

    try:
        token = get_token()
        result = get_user(token, event.sender_id)

        if result.get("searched"):
            user = result["searched"][0]
            first_name = user.get("first_name", "Не вказано")
            unique = user.get("unique", "Не вказано")
            rating = user.get("rating", 0)
            games = user.get("games_count", 0)
            wins = user.get("wins", 0)
            losses = user.get("losses", 0)
            wl = round(wins / losses, 2) if losses > 0 else wins

            profile_text = (
                f"👤 **Ваш профіль**\n\n"
                f"🆔 Логін: `{unique}`\n"
                f"📝 Ім'я: {first_name}\n"
                f"--- --- --- ---\n"
                f"♟ Ваш рейтинг: {rating}\n"
                f"👾 Кількість ігор: {games}\n"
                f"🏆 Перемог: {wins}\n"
                f"🏳️ Поразок: {losses}\n"
                f"📊 W/L: {wl}"
            )

            await event.edit(profile_text, buttons=profile_menu)
        else:
            await event.edit("❌ Помилка: профіль не знайдено.", buttons=main_menu)
    except Exception as e:
        print(f"Помилка в remakeback: {e}")
        await event.answer()


async def profileback(event: events.CallbackQuery.Event):
    await event.edit("Повернулися, обирайте:", buttons=main_menu)


async def handle_profile_step(event, step, text):
    token = get_token()
    current_user = get_user(token, event.sender_id)

    if not current_user.get("searched"):
        await event.respond("❌ Користувача не знайдено.", buttons=main_menu)
        user_state[event.sender_id] = None
        return

    user_data = current_user["searched"][0]
    user_id = user_data.get("id")

    if step == "wait_new_name":
        if len(text) < 2 or len(text) > 20:
            await event.reply("❌ Ім'я має бути від 2 до 20 символів!")
            return

        if not text.replace(" ", "").isalpha():
            await event.reply("❌ Ім'я має складатися тільки з літер!")
            return

        payload = _build_update_payload(user_data, first_name=text)
        res = update_user(token, user_id, payload)

        if res.status_code == 200:
            user_state[event.sender_id] = None
            await event.respond(f"✅ Ім'я успішно змінено на: **{text}**", buttons=main_menu)
        else:
            await event.respond(f"❌ Помилка {res.status_code}: {res.text}")

    elif step == "wait_new_unique":
        if len(text) < 3 or len(text) > 15:
            await event.reply("❌ Логін має бути від 3 до 15 символів!")
            return

        if not text.isalnum():
            await event.reply("❌ Логін може містити тільки літери та цифри без спецсимволів!")
            return

        payload = _build_update_payload(user_data, unique=text)
        res = update_user(token, user_id, payload)

        if res.status_code == 200:
            user_state[event.sender_id] = None
            await event.respond(f"✅ Логін успішно змінено на: **{text}**", buttons=main_menu)
        elif res.status_code == 400:
            await event.respond("⚠️ Цей логін вже зайнятий або збігається з поточним.")
        else:
            await event.respond(f"❌ Помилка {res.status_code}")

    elif step == "wait_new_password":
        if len(text) < 6 or len(text) > 12:
            await event.reply("❌ **Помилка:** Пароль має бути від 6 до 12 символів!")
            return

        payload = _build_update_payload(user_data, password=text)
        res = update_user(token, user_id, payload)

        if res.status_code == 200:
            user_state[event.sender_id] = None
            await event.respond("✅ **Успішно!** Ваш пароль було оновлено.", buttons=main_menu)
        elif res.status_code == 400:
            try:
                reason = res.json().get("detail", "")
            except Exception:
                reason = ""

            if "No changes detected" in str(reason):
                await event.respond(
                    "⚠️ **Ви увели той самий пароль.**\nПридумайте нову комбінацію або натисніть «Назад»."
                )
            else:
                await event.respond(f"❌ **Помилка запиту:** {reason}")
        elif res.status_code == 422:
            await event.respond("❌ **Помилка валідації:** Сервер не прийняв формат даних. Перевірте пароль.")
        else:
            await event.respond(f"❌ **Помилка:** {res.status_code}")

    elif step == "wait_delete_login":
        user_state[event.sender_id] = {
            "step": "wait_delete_password_final",
            "delete_unique": text.strip(),
        }
        await event.respond("🔐 Тепер введіть ваш **Пароль** для остаточного видалення:")

    elif step == "wait_delete_password_final":
        delete_login = user_state[event.sender_id].get("delete_unique")
        delete_password = text.strip()
        res = delete_user(token, delete_login, delete_password)

        user_state[event.sender_id] = None
        if res.status_code == 200:
            await event.respond("🗑 **Ваш акаунт та всі дані успішно видалено.**\nДо нових зустрічей!", buttons=authreg)
        elif res.status_code == 404:
            await event.respond("❌ **Помилка:** Неправильний логін або пароль. Видалення скасовано.", buttons=main_menu)
        else:
            await event.respond(f"❌ **Помилка сервера ({res.status_code}):** {res.text}")


def _build_update_payload(user_data, unique=None, first_name=None, password=None):
    return {
        "unique": unique if unique is not None else user_data.get("unique", ""),
        "first_name": first_name if first_name is not None else user_data.get("first_name", ""),
        "middle_name": user_data.get("middle_name", ""),
        "last_name": user_data.get("last_name", ""),
        "password": password if password is not None else user_data.get("password", ""),
        "phone": user_data.get("phone", 0),
        "email": user_data.get("email", ""),
    }
