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
    
    # 1. Сначала делаем твой старый рабочий запрос по Telegram ID
    user_search_result = await asyncio.to_thread(get_user, token, tg_id)

    # Проверяем, нашел ли бот юзера через старый метод
    if not user_search_result or not user_search_result.get("searched"):
        await event.answer("❌ Ошибка: пользователь не найден в базе данных.", alert=True)
        return

    # Вытаскиваем базовые данные юзера
    user_base = user_search_result["searched"][0]
    
    # ДОСТАЕМ ТОТ САМЫЙ UUID ИЗ БАЗЫ (поле "id" внутри searched)
    user_uuid = user_base.get("id") 
    
    if not user_uuid:
        await event.answer("❌ Ошибка: не удалось получить UUID пользователя.", alert=True)
        return

    # 2. Теперь дергаем эндпоинт статистики, передавая туда UUID, как просил админ!
    stats_data = await asyncio.to_thread(get_user_stats, token, user_uuid)

    if stats_data and "user" in stats_data:
        user_info = stats_data["user"]
        first_name = user_info.get("first_name", "Не указано")
        unique = user_info.get("unique", "Не указано")
        
        # Забираем статистику с верхнего уровня JSON
        rating = stats_data.get("rating", 0)
        games = stats_data.get("games_total", 0)
        wins = stats_data.get("wins", 0)
        losses = stats_data.get("losses", 0)
        wl = stats_data.get("win_loss_ratio", 0)

        profile_text = (
            f"👤 **Ваш профиль**\n\n"
            f"🆔 Логин: `{unique}`\n"
            f"📝 Имя: {first_name}\n"
            f"--- --- --- ---\n"
            f"♟ Ваш рейтинг: {rating}\n"
            f"👾 Количество игр: {games}\n"
            f"🏆 Побед: {wins}\n"
            f"🏳️ Поражений: {losses}\n"
            f"📊 W/L: {wl}"
        )

        await event.edit(profile_text, buttons=profile_menu)
    else:
        await event.answer("❌ Ошибка бэкенда при получении статистики.", alert=True)


async def nameremake(event):
    user_state[event.sender_id] = {"step": "wait_new_name"}
    await event.edit("✏️ Введите новое **Имя** (2-20 символов):", buttons=remake_back)


async def loginremake(event):
    user_state[event.sender_id] = {"step": "wait_new_unique"}
    await event.edit("✏️ Введите новый **Логин** (2-16 символов, только буквы и цифры):", buttons=remake_back)


async def passwordremake(event):
    user_state[event.sender_id] = {"step": "wait_new_password"}
    await event.edit("🔒 Введите **новый пароль** (от 6 до 12 символов):", buttons=remake_back)


async def confirmdelete(event):
    user_state[event.sender_id] = {"step": "wait_delete_login"}
    await event.edit(
        "⚠️ **УДАЛЕНИЕ АККАУНТА**\n\nДля подтверждения введите ваш **Логин (unique)**:",
        buttons=remake_back,
    )


async def remakeback(event):
    user_state[event.sender_id] = None

    try:
        token = get_token()
        result = get_user(token, event.sender_id)

        if result.get("searched"):
            user = result["searched"][0]
            first_name = user.get("first_name", "Не указано")
            unique = user.get("unique", "Не указано")
            rating = user.get("rating", 0)
            games = user.get("games_count", 0)
            wins = user.get("wins", 0)
            losses = user.get("losses", 0)
            wl = round(wins / losses, 2) if losses > 0 else wins

            profile_text = (
                f"👤 **Ваш профиль**\n\n"
                f"🆔 Логин: `{unique}`\n"
                f"📝 Имя: {first_name}\n"
                f"--- --- --- ---\n"
                f"♟ Ваш рейтинг: {rating}\n"
                f"👾 Количество игр: {games}\n"
                f"🏆 Побед: {wins}\n"
                f"🏳️ Поражений: {losses}\n"
                f"📊 W/L: {wl}"
            )

            await event.edit(profile_text, buttons=profile_menu)
        else:
            await event.edit("❌ Ошибка: профиль не найден.", buttons=main_menu)
    except Exception as e:
        print(f"Ошибка в remakeback: {e}")
        await event.answer()


async def profileback(event: events.CallbackQuery.Event):
    await event.edit("Вернулись, выбирайте:", buttons=main_menu)


async def handle_profile_step(event, step, text):
    token = get_token()
    current_user = get_user(token, event.sender_id)

    if not current_user.get("searched"):
        await event.respond("❌ Пользователь не найден.", buttons=main_menu)
        user_state[event.sender_id] = None
        return

    user_data = current_user["searched"][0]
    user_id = user_data.get("id")

    if step == "wait_new_name":
        if len(text) < 2 or len(text) > 20:
            await event.reply("❌ Имя должно быть от 2 до 20 символов!")
            return

        if not text.replace(" ", "").isalpha():
            await event.reply("❌ Имя должно состоять только из букв!")
            return

        payload = _build_update_payload(user_data, first_name=text)
        res = update_user(token, user_id, payload)

        if res.status_code == 200:
            user_state[event.sender_id] = None
            await event.respond(f"✅ Имя успешно изменено на: **{text}**", buttons=main_menu)
        else:
            await event.respond(f"❌ Ошибка {res.status_code}: {res.text}")

    elif step == "wait_new_unique":
        if len(text) < 3 or len(text) > 15:
            await event.reply("❌ Логин должен быть от 3 до 15 символов!")
            return

        if not text.isalnum():
            await event.reply("❌ Логин может содержать только буквы и цифры без спецсимволов!")
            return

        payload = _build_update_payload(user_data, unique=text)
        res = update_user(token, user_id, payload)

        if res.status_code == 200:
            user_state[event.sender_id] = None
            await event.respond(f"✅ Логин успешно изменен на: **{text}**", buttons=main_menu)
        elif res.status_code == 400:
            await event.respond("⚠️ Этот логин уже занят или совпадает с текущим.")
        else:
            await event.respond(f"❌ Ошибка {res.status_code}")

    elif step == "wait_new_password":
        if len(text) < 6 or len(text) > 12:
            await event.reply("❌ **Ошибка:** Пароль должен быть от 6 до 12 символов!")
            return

        payload = _build_update_payload(user_data, password=text)
        res = update_user(token, user_id, payload)

        if res.status_code == 200:
            user_state[event.sender_id] = None
            await event.respond("✅ **Успешно!** Ваш пароль был обновлен.", buttons=main_menu)
        elif res.status_code == 400:
            try:
                reason = res.json().get("detail", "")
            except Exception:
                reason = ""

            if "No changes detected" in str(reason):
                await event.respond(
                    "⚠️ **Вы ввели тот же самый пароль.**\nПридумайте новую комбинацию или нажмите «Назад»."
                )
            else:
                await event.respond(f"❌ **Ошибка запроса:** {reason}")
        elif res.status_code == 422:
            await event.respond("❌ **Ошибка валидации:** Сервер не принял формат данных. Проверьте пароль.")
        else:
            await event.respond(f"❌ **Ошибка:** {res.status_code}")

    elif step == "wait_delete_login":
        user_state[event.sender_id] = {
            "step": "wait_delete_password_final",
            "delete_unique": text.strip(),
        }
        await event.respond("🔐 Теперь введите ваш **Пароль** для окончательного удаления:")

    elif step == "wait_delete_password_final":
        delete_login = user_state[event.sender_id].get("delete_unique")
        delete_password = text.strip()
        res = delete_user(token, delete_login, delete_password)

        user_state[event.sender_id] = None
        if res.status_code == 200:
            await event.respond("🗑 **Ваш аккаунт и все данные успешно удалены.**\nДо новых встреч!", buttons=authreg)
        elif res.status_code == 404:
            await event.respond("❌ **Ошибка:** Неверный логин или пароль. Удаление отменено.", buttons=main_menu)
        else:
            await event.respond(f"❌ **Ошибка сервера ({res.status_code}):** {res.text}")


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
