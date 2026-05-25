from telethon import Button, events

from api import (
    get_token,
    get_user,
    get_user_by_unique,
    get_friends_list,
    send_friend_request,
    update_friend_request,
    get_friend_requests_for_me,
    get_friend_requests_my,
    cancel_friend_request,
)
from menus import friend_back, friend_menu, main_menu
from state import user_state


def register_friend_handlers(bot):
    bot.add_event_handler(show_friends_list, events.CallbackQuery(data="friend_main"))
    bot.add_event_handler(start_add_friend, events.CallbackQuery(data="friend_add"))
    bot.add_event_handler(handle_requests_menu, events.CallbackQuery(data="friend_requests"))
    bot.add_event_handler(handle_accept_request, events.CallbackQuery(pattern=r"acc_(.+)"))
    bot.add_event_handler(handle_reject_request, events.CallbackQuery(pattern=r"rej_(.+)"))
    bot.add_event_handler(show_incoming, events.CallbackQuery(data="requests_in"))
    bot.add_event_handler(show_outgoing, events.CallbackQuery(data="requests_out"))
    bot.add_event_handler(handle_cancel_request, events.CallbackQuery(pattern=r"can_(.+)"))
    bot.add_event_handler(show_unfriend_menu, events.CallbackQuery(data="unfriend_list"))
    bot.add_event_handler(handle_unfriend_action, events.CallbackQuery(pattern=r"unf_id_(.+)"))
    bot.add_event_handler(go_back_from_friends, events.CallbackQuery(data="friend_back"))


async def show_friends_list(event):
    token = get_token()
    current_user = get_user(token, event.sender_id)

    if current_user.get("searched"):
        user_id = current_user["searched"][0].get("id")
        friends = get_friends_list(token, user_id)

        if not friends:
            text = "👥 **Ваш список друзів порожній.**\n\nСаме час когось додати!"
        else:
            text = "👥 **Ваші друзі:**\n\n"
            for friend in friends:
                name = friend.get("first_name", "Гравець")
                nick = friend.get("unique", "??")
                rating = friend.get("rating", 0)
                text += f"• **{name}** (@{nick}) — 🏆 {rating}\n"

        current_buttons = [[Button.inline("🗑 Видалити когось", data="unfriend_list")]] + friend_menu
        await event.edit(text, buttons=current_buttons)
    else:
        await event.answer("❌ Спочатку зареєструйтеся!", alert=True)


async def start_add_friend(event):
    user_state[event.sender_id] = {"step": "wait_friend_nickname"}
    await event.edit("🔍 Введіть **Нік (unique)** користувача, якого хочете додати:", buttons=[[friend_back]])


async def handle_requests_menu(event):
    text = "🚀 **Керування заявками**\n\nОберіть розділ:"
    buttons = [
        [Button.inline("📥 Вхідні (вам)", data="requests_in")],
        [Button.inline("📤 Вихідні (від вас)", data="requests_out")],
        [Button.inline("⬅️ Назад у меню", data="friend_main")],
    ]
    await event.edit(text, buttons=buttons)


async def handle_accept_request(event):
    request_id = event.pattern_match.group(1).decode('utf-8')
    token = get_token()
    res = update_friend_request(token, request_id, True)

    if res.status_code == 200:
        await event.answer("✅ Заявку прийнято! Тепер ви друзі.", alert=True)
        await event.edit("✅ **Заявку в друзі прийнято!**", buttons=None)
    else:
        await event.answer(f"❌ Помилка сервера: {res.status_code}", alert=True)


async def handle_reject_request(event):
    request_id = event.pattern_match.group(1).decode('utf-8')
    token = get_token()
    res = update_friend_request(token, request_id, False)

    if res.status_code == 200:
        await event.answer("❌ Заявку відхилено.", alert=True)
        await event.edit("❌ **Заявку в друзі відхилено.**", buttons=None)
    else:
        await event.answer(f"❌ Помилка сервера: {res.status_code}", alert=True)


async def show_incoming(event):
    token = get_token()
    me = get_user(token, event.sender_id)
    my_uuid = me["searched"][0].get("id")
    reqs = get_friend_requests_for_me(token, my_uuid)

    if not reqs:
        await event.edit("📩 **Вхідних заявок немає.**", buttons=[[Button.inline("⬅️ Назад", data="friend_requests")]])
        return

    text = "📥 **Вхідні заявки:**\n"
    buttons = []

    for req in reqs:
        r_id = req.get("id")
        user_data = req.get("user") or {}
        name = user_data.get("unique") or user_data.get("first_name") or "Гравець"
        text += f"\n👤 Від: **@{name}**"
        buttons.append([
            Button.inline("✅ Прийняти", data=f"acc_{r_id}"),
            Button.inline("❌ Відхилити", data=f"rej_{r_id}"),
        ])

    buttons.append([Button.inline("⬅️ Назад", data="friend_requests")])
    await event.edit(text, buttons=buttons)


async def show_outgoing(event):
    token = get_token()
    me = get_user(token, event.sender_id)
    my_uuid = me["searched"][0].get("id")
    reqs = get_friend_requests_my(token, my_uuid)

    if not reqs:
        await event.edit("📤 **Ви не надсилали заявок.**", buttons=[[Button.inline("⬅️ Назад", data="friend_requests")]])
        return

    text = "📤 **Ваші вихідні заявки:**\n"
    buttons = []

    for req in reqs:
        r_id = req.get("id")
        friend_data = req.get("friend") or {}
        name = friend_data.get("unique") or friend_data.get("first_name") or "Гравець"
        text += f"\n👤 До: **@{name}**"
        buttons.append([Button.inline("🚫 Відкликати", data=f"can_{r_id}")])

    buttons.append([Button.inline("⬅️ Назад", data="friend_requests")])
    await event.edit(text, buttons=buttons)


async def handle_cancel_request(event):
    request_id = event.pattern_match.group(1).decode('utf-8')
    token = get_token()
    res = cancel_friend_request(token, request_id)

    if res.status_code == 200:
        await event.answer("✅ Заявку відкликано!", alert=True)
        await show_outgoing(event)
    else:
        await event.answer(f"❌ Помилка API: {res.status_code}", alert=True)


async def show_unfriend_menu(event):
    token = get_token()
    me = get_user(token, event.sender_id)
    user_id = me["searched"][0].get("id")
    friends = get_friends_list(token, user_id)

    if not friends:
        await event.edit("📭 Список порожній.", buttons=[[Button.inline("⬅️ Назад", data="friend_main")]])
        return

    buttons = []
    for friend in friends:
        f_id = friend.get('id')
        nick = friend.get('unique', 'Гравець')
        buttons.append([Button.inline(f"❌ Видалити {nick}", data=f"unf_id_{f_id}")])

    buttons.append([Button.inline("⬅️ Назад", data="friend_main")])
    await event.edit("🗑 Оберіть друга для видалення:", buttons=buttons)


async def handle_unfriend_action(event):
    target_user_id = event.pattern_match.group(1).decode('utf-8')
    token = get_token()
    res = update_friend_request(token, target_user_id, False)

    if res.status_code == 200:
        await event.answer("✅ Видалено!", alert=True)
    else:
        await event.answer("❌ Бекенд усе ще відхиляє видалення", alert=True)


async def go_back_from_friends(event):
    user_state[event.sender_id] = None
    await event.edit("🏠 Головне меню", buttons=main_menu)


async def handle_friend_step(event, step, text):
    if step != "wait_friend_nickname":
        return

    token = get_token()
    my_info = get_user(token, event.sender_id)

    if not my_info.get("searched"):
        await event.respond("❌ Користувача не знайдено.", buttons=main_menu)
        user_state[event.sender_id] = None
        return

    target_nickname = text.strip()
    friend = get_user_by_unique(token, target_nickname)

    if not friend:
        await event.respond("❌ Користувача з таким ніком не знайдено.", buttons=main_menu)
        user_state[event.sender_id] = None
        return

    my_id = my_info["searched"][0].get("id")
    add_res = send_friend_request(token, my_id, target_nickname)
    user_state[event.sender_id] = None

    if not add_res:
        await event.respond("❌ Не вдалося знайти користувача для надсилання запиту.", buttons=main_menu)
        return

    if add_res.status_code == 200:
        await event.respond(f"✅ Запит для **{target_nickname}** успішно надіслано!", buttons=main_menu)

        friend_tg_id = friend.get("tg_id")
        if friend_tg_id:
            try:
                msg = (
                    f"🔔 **Нова заявка в друзі!**\n\n"
                    f"Гравець **{my_info['searched'][0].get('first_name')}** (@{my_info['searched'][0].get('unique')}) хоче додати вас."
                )
                req_buttons = [
                    [
                        Button.inline("✅ Прийняти", data=f"acc_{add_res.json().get('id')}"),
                        Button.inline("❌ Відхилити", data=f"rej_{add_res.json().get('id')}")
                    ]
                ]
                await event.client.send_message(friend_tg_id, msg, buttons=req_buttons)
            except Exception as e:
                print(f"Помилка надсилання сповіщення: {e}")

    elif add_res.status_code in [400, 422]:
        try:
            reason = add_res.json().get("detail", "")
        except Exception:
            reason = ""

        if "already exists" in str(reason).lower():
            await event.respond(
                "⚠️ **Заявку вже було надіслано раніше.**\nВона очікує підтвердження в розділі «Заявки» у вашого друга.",
                buttons=main_menu,
            )
        else:
            await event.respond(
                f"❌ Помилка сервера: {reason if reason else add_res.status_code}",
                buttons=main_menu,
            )
    else:
        await event.respond(
            f"❌ Не вдалося надіслати запит (Код: {add_res.status_code})",
            buttons=main_menu,
        )