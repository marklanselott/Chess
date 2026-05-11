from telethon import events, Button
import asyncio

from menus import main_menu, play_menu, level, play_back, cancel_search_btn
from state import user_state
from api import await_opponent, get_token, get_user, start_search_opponent, stop_search_opponent, await_opponent

console_active = asyncio.Event()


def register_game_handlers(bot):
    bot.add_event_handler(play, events.CallbackQuery(data="play"))
    bot.add_event_handler(playback, events.CallbackQuery(data="play_back"))
    bot.add_event_handler(offline, events.CallbackQuery(data="offline"))
    bot.add_event_handler(search_opponent, events.CallbackQuery(data="online"))
    bot.add_event_handler(cancel_search, events.CallbackQuery(data="cancel_search"))
    bot.add_event_handler(callback_force_api_stop, events.CallbackQuery(data="force_api_stop"))



async def play(event: events.CallbackQuery.Event):
    await event.edit("Выберите режим:", buttons=play_menu)


async def playback(event: events.CallbackQuery.Event):
    console_active.clear()
    await event.edit("Вернулись, выбирайте:", buttons=main_menu)


async def offline(event: events.CallbackQuery.Event):
    await event.edit("Выберите уровень сложности", buttons=level)

async def search_opponent(event: events.CallbackQuery.Event):
    user_id = event.sender_id
    token = get_token()
    
    me = get_user(token, user_id)
    if not me.get("searched"):
        await event.answer("❌ Ошибка профиля", alert=True)
        return

    user_uuid = me["searched"][0].get("id")

    # Если уже ищем - игнорим
    if user_state.get(user_id, {}).get("searching"):
        return

    user_state[user_id] = {"searching": True}

    # --- ШАГ 1: ПРИНУДИТЕЛЬНЫЙ СБРОС ПЕРЕД СТАРТОМ ---
    # Мы сначала "выбиваем" старую сессию на всякий случай
    await asyncio.to_thread(stop_search_opponent, token, user_uuid)
    await asyncio.sleep(1) # Даем серверу 1 секунду "прожевать" отмену

    # --- ШАГ 2: СТАРТ НОВОЙ СЕССИИ ---
    res_start = await asyncio.to_thread(start_search_opponent, token, user_uuid)
    
    if res_start.status_code != 200:
        user_state[user_id]["searching"] = False
        
        if res_start.status_code == 400:
            # Если все еще пишет, что в игре - выводим кнопку с глубокой очисткой
            btn_fix = [[Button.inline("⚙️ Глубокий сброс сессии", data="force_api_stop")]]
            await event.edit(
                "⚠️ **Сервер все еще не отпустил сессию.**\n"
                "Нажмите 'Глубокий сброс' и подождите пару секунд перед новым поиском.", 
                buttons=btn_fix
            )
        else:
            await event.edit(f"❌ Ошибка: {res_start.status_code}\n{res_start.text}")
        return

    await event.edit("🔎 **Поиск оппонента...**", buttons=cancel_search_btn)

    try:
        while user_state.get(user_id, {}).get("searching") is True:
            data = await asyncio.to_thread(await_opponent, token, user_uuid)
            if not user_state.get(user_id, {}).get("searching"): break

            if isinstance(data, dict) and data.get("oponent"):
                opponent = data["oponent"]
                user_state[user_id]["searching"] = False
                await event.edit(f"✅ **Игра найдена!**\n👤 Противник: **{opponent.get('first_name')}**")
                return 
            await asyncio.sleep(0.5)
    except:
        pass
    finally:
        if user_id in user_state:
            user_state[user_id]["searching"] = False

async def callback_force_api_stop(event):
    user_id = event.sender_id
    token = get_token()
    
    # 1. Сбрасываем флаг поиска в памяти бота
    if user_id in user_state:
        user_state[user_id]["searching"] = False

    # 2. Получаем UUID и пинаем сервер методом STOP
    me = get_user(token, user_id)
    if me.get("searched"):
        user_uuid = me["searched"][0].get("id")
        await asyncio.to_thread(stop_search_opponent, token, user_uuid)
        
    await event.answer("✅ Сессия сброшена!", alert=True)
    await event.edit("❌ Старая сессия закрыта. Теперь можно искать снова.", buttons=play_menu)

async def cancel_search(event: events.CallbackQuery.Event):
    user_id = event.sender_id
    token = get_token()

    # Сначала меняем состояние и UI, чтобы бот не "тупил"
    if user_id in user_state:
        user_state[user_id]["searching"] = False

    await event.answer("Поиск отменен")
    await event.edit("❌ Поиск отменен.", buttons=play_menu)

    # Уведомляем сервер об отмене в фоне
    me = get_user(token, user_id)
    if me.get("searched"):
        user_uuid = me["searched"][0].get("id")
        await asyncio.to_thread(stop_search_opponent, token, user_uuid)