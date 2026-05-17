from telethon import events, Button
import asyncio
from telethon.errors import MessageNotModifiedError
from menus import main_menu, play_menu, level, play_back, cancel_search_btn
from state import user_state
from api import await_opponent, get_token, get_user, start_search_opponent, stop_search_opponent, await_opponent, get_game_board, make_chess_move, surrender_game, start_ai_game
from chess_handler import generate_chess_keyboard


console_active = asyncio.Event()


def register_game_handlers(bot):
    bot.add_event_handler(play, events.CallbackQuery(data="play"))
    bot.add_event_handler(playback, events.CallbackQuery(data="play_back"))
    bot.add_event_handler(offline, events.CallbackQuery(data="offline"))
    bot.add_event_handler(search_opponent, events.CallbackQuery(data="online"))
    bot.add_event_handler(cancel_search, events.CallbackQuery(data="cancel_search"))
    bot.add_event_handler(callback_force_api_stop, events.CallbackQuery(data="force_api_stop"))
    bot.add_event_handler(handle_cell_click, events.CallbackQuery(pattern=r'^cell_[a-h][1-8]$'))
    bot.add_event_handler(handle_surrender_click, events.CallbackQuery(data="game_surrender"))
    bot.add_event_handler(start_ai_game_handler, events.CallbackQuery(pattern=r'^(easy|medium|hard)$'))

async def play(event: events.CallbackQuery.Event):
    await event.edit("Выберите режим:", buttons=play_menu)


async def playback(event: events.CallbackQuery.Event):
    console_active.clear()
    await event.edit("Вернулись, выбирайте:", buttons=main_menu)


async def offline(event: events.CallbackQuery.Event):
    await event.edit("Выберите уровень сложности", buttons=level)

async def listen_opponent_moves(client, user_id, game_id):
    from api import make_ai_move, get_game_board
    token = get_token()
    
    while True:
        try:
            state = user_state.get(user_id)
            if not state or state.get("game_id") != game_id:
                break
                
            current_fen = state.get("current_fen", "")
            fen_parts = current_fen.split()
            
            my_color = state.get("my_color")
            active_color = fen_parts[1] if len(fen_parts) > 1 else 'w'
            
            # 1. Проверяем, чей сейчас ход по правилам шахмат
            is_my_turn = False
            if active_color == 'w' and my_color == "white":
                is_my_turn = True
            elif active_color == 'b' and my_color == "black":
                is_my_turn = True
                
            # 2. Определяем, кто наш соперник (строго по имени)
            opponent_name = str(state.get("opponent_name", "")).lower()
            is_game_against_ai = "ии" in opponent_name or "ai" in opponent_name or "бот" in opponent_name
            
            # Ход ИИ нужен только если сейчас НЕ НАШ ход и мы играем против ИИ
            is_ai_action_needed = (not is_my_turn) and is_game_against_ai

            # Если сейчас НАШ ХОД в онлайн-игре, просто ждем клика игрока по кнопкам-клеткам
            if is_my_turn and not is_game_against_ai:
                await asyncio.sleep(3)
                continue

            if is_ai_action_needed:
                # === РЕЖИМ ИГРЫ С ИИ ===
                ai_res = await asyncio.to_thread(make_ai_move, token, game_id)
                
                if ai_res and ai_res.status_code == 200:
                    ai_data = ai_res.json()
                    ai_game = ai_data.get("game", {})
                    new_fen = ai_game.get("board", {}).get("fen")
                    game_status = ai_game.get("status")
                    
                    if game_status in ["finished", "surrendered"]:
                        user_state[user_id] = None
                        await client.send_message(user_id, "🏁 Игра завершена! ИИ победил.", buttons=main_menu)
                        break
                        
                    if new_fen and new_fen != current_fen:
                        user_state[user_id]["current_fen"] = new_fen
                        user_state[user_id]["selected_piece"] = None
                        await send_game_board(client, user_id)
            else:
                # === РЕЖИМ ОНЛАЙН-ИГРЫ С ЧЕЛОВЕКОМ ===
                game_data = await asyncio.to_thread(get_game_board, token, game_id)
                
                if game_data and isinstance(game_data, dict):
                    inner_game = game_data.get("game", {})
                    server_fen = inner_game.get("board", {}).get("fen")
                    game_status = inner_game.get("status")
                    
                    # Сначала проверяем, не завершилась ли игра (сдача/мат), чтобы не мигать доской
                    if game_status in ["finished", "surrendered"]:
                        user_state[user_id] = None
                        await client.send_message(user_id, "🏁 Партия завершена! Соперник сдался или игра окончена.", buttons=main_menu)
                        break
                    
                    # Если игра идет и FEN на сервере изменился — обновляем доску
                    if server_fen and server_fen != current_fen:
                        user_state[user_id]["current_fen"] = server_fen
                        user_state[user_id]["selected_piece"] = None
                        await send_game_board(client, user_id)

            await asyncio.sleep(3)
            
        except Exception:
            await asyncio.sleep(3)

def is_my_turn(fen: str, my_color: str) -> bool:
    """ Helper to determine if it's user's turn based on FEN """
    try:
        parts = fen.split()
        if len(parts) > 1:
            active_color = parts[1] # 'w' or 'b'
            return (active_color == 'w' and my_color == 'white') or (active_color == 'b' and my_color == 'black')
    except Exception:
        pass
    return True

async def search_opponent(event: events.CallbackQuery.Event):
    user_id = event.sender_id
    token = get_token()
    
    me = get_user(token, user_id)
    # Защита: проверяем, что ответ от сервера вообще пришел и это словарь
    if not me or not isinstance(me, dict) or not me.get("searched"):
        await event.answer("❌ Ошибка профиля", alert=True)
        return

    user_uuid = me["searched"][0].get("id")

    # Безопасно получаем стейт игрока
    state = user_state.get(user_id)
    # Если стейт является словарем и там уже активен поиск — выходим, чтобы не спамить запросами
    if isinstance(state, dict) and state.get("searching"):
        return

    # Записываем чистый словарь для старта поиска
    user_state[user_id] = {"searching": True}

    await asyncio.to_thread(stop_search_opponent, token, user_uuid)
    await asyncio.sleep(0.5) 

    res_start = await asyncio.to_thread(start_search_opponent, token, user_uuid)
    if res_start.status_code != 200:
        user_state[user_id]["searching"] = False
        await event.edit("❌ Ошибка при старте поиска.", buttons=play_menu)
        return

    await event.edit("🔍 Ищем противника...", buttons=[cancel_search_btn])

    # Запускаем long-polling ожидания
    data = await asyncio.to_thread(await_opponent, token, user_uuid)
    
    if isinstance(data, dict) and data.get("opponent"):
        user_state[user_id]["searching"] = False
        opponent = data["opponent"]
        
        real_game_id = None
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        my_color = "white"
        
        if data.get("game"):
            game_info = data["game"]
            real_game_id = game_info.get("id")
            fen = game_info.get("board", {}).get("fen", fen)
            is_white = game_info.get("white") == user_uuid
            my_color = "white" if is_white else "black"
            
        if not real_game_id:
            # Возвращаем флаг поиска в False, если сорвалось на этапе создания игры
            user_state[user_id]["searching"] = False
            await event.edit("⚠️ Ошибка синхронизации ID матча.", buttons=play_menu)
            return

        # Пытаемся определить Telegram ID оппонента из данных бэка, если он там есть
        opponent_tg_id = opponent.get("tg_id")

        # Получаем актуальный ID сообщения нажатой инлайн-кнопки перед занесением в стейт
        current_msg_id = event.msg_id if hasattr(event, 'msg_id') else None
        if not current_msg_id and hasattr(event, 'message') and event.message:
            current_msg_id = event.message.id

        user_state[user_id] = {
            "searching": False,
            "game_id": real_game_id,
            "my_color": my_color,
            "opponent_name": opponent.get("unique") or opponent.get("first_name") or "Оппонент",
            "opponent_rating": opponent.get("rating", 0),
            "opponent_tg_id": opponent_tg_id,
            "current_fen": fen,
            "selected_piece": None,
            "board_msg_id": current_msg_id  # Сохраняем вычисленный ID сообщения
        }
        
        # Первичная отрисовка доски поверх текста поиска
        await send_game_board(event, user_id)
        
        # Запускаем фоновый трекер ходов соперника
        asyncio.create_task(listen_opponent_moves(event.client, user_id, real_game_id))

async def callback_force_api_stop(event):
    user_id = event.sender_id
    token = get_token()
    
    # 1. Принудительно и БЕЗОПАСНО сбрасываем флаги в памяти бота
    # Если стейт есть, зачищаем его полностью, чтобы остановить фоновые циклы и оживить меню
    if user_id in user_state:
        user_state[user_id] = {
            "searching": False,
            "game_id": None,
            "selected_piece": None,
            "board_msg_id": None
        }
    else:
        user_state[user_id] = {"searching": False}

    # 2. Получаем UUID игрока
    me = get_user(token, user_id)
    if not me or not me.get("searched"):
        await event.answer("❌ Ошибка профиля. Не удалось получить UUID.", alert=True)
        # Даже если профиль на сервере не нашелся, мы уже разбажили стейт в памяти бота (шаг 1),
        # поэтому всё равно возвращаем его в меню игры:
        await event.edit("⚙️ Локальный стейт сброшен, но сервер не ответил.", buttons=play_menu)
        return
        
    user_uuid = me["searched"][0].get("id")
    
    # 3. Пинаем сервер через готовую функцию (снимаем с поиска / закрываем сессию на бэке)
    try:
        await asyncio.to_thread(stop_search_opponent, token, user_uuid)
    except Exception as e:
        print(f"[Force Stop API Error]: {e}")
        
    # 4. Обновляем интерфейс юзеру
    await event.answer("⚙️ Сессия принудительно сброшена!", alert=True)
    await event.edit("❌ Старая сессия закрыта. Теперь можно искать снова.", buttons=play_menu)

async def cancel_search(event: events.CallbackQuery.Event):
    user_id = event.sender_id
    token = get_token()
    user_state[user_id] = {"searching": False}
    me = get_user(token, user_id)
    if me.get("searched"):
        user_uuid = me["searched"][0].get("id")
        await asyncio.to_thread(stop_search_opponent, token, user_uuid)
    await event.edit("Поиск отменен.", buttons=play_menu)

async def send_game_board(event_or_client, user_id):
    """
    Отрисовывает шахматную доску.
    Показывает информацию об оппоненте, цвет игрока и ЧЕЙ СЕЙЧАС ХОД.
    """
    state = user_state.get(user_id)
    if not state:
        return
        
    fen = state["current_fen"]
    selected = state["selected_piece"]
    opponent_name = state["opponent_name"]
    opponent_rating = state["opponent_rating"]
    
    # Красиво форматируем цвет самого игрока
    my_color_text = "Белые ⚪" if state["my_color"] == "white" else "Черные ⚫"
    
    # ВЫЧИСЛЯЕМ ЧЕЙ СЕЙЧАС ХОД ИЗ FEN
    current_turn_text = "Определяется..."
    try:
        parts = fen.split()
        if len(parts) > 1:
            active_color = parts[1]  # 'w' или 'b'
            if active_color == 'w':
                current_turn_text = "Белых ⚪"
            elif active_color == 'b':
                current_turn_text = "Черных ⚫"
    except Exception:
        pass

    # Генерируем кнопки шахматных клеток
    chess_buttons = generate_chess_keyboard(fen, selected_cell=selected)
    
    # Добавляем кнопку "Сдаться" под доску
    chess_buttons.append([Button.inline("🏳️ Сдаться", data="game_surrender")])

    # Формируем итоговое сообщение для игрока
    message_content = (
        f"⚔️ **Партия против:** @{opponent_name} (⭐ {opponent_rating})\n"
        f"🏳️ **Ваш цвет:** {my_color_text}\n"
        f"⏳ **Сейчас ход:** {current_turn_text}\n\n"
        f"ℹ️ *Нажимайте на кнопки-клетки, чтобы сделать ход.*"
    )
    
    # ОПРЕДЕЛЯЕМ КЛИЕНТА (для фоновых методов или отправки нового сообщения)
    client = event_or_client.client if hasattr(event_or_client, 'client') else event_or_client

    # 1. Если передано событие (клик по кнопке игроком) — редактируем сообщение на месте
    if hasattr(event_or_client, 'edit'):
        try:
            # ИСПРАВЛЕНИЕ: Сохраняем результат редактирования! В нём содержится железный ID
            edited_msg = await event_or_client.edit(message_content, buttons=chess_buttons)
            
            # Если Телетон вернул объект измененного сообщения, забираем ID из него
            if edited_msg and hasattr(edited_msg, 'id'):
                state["board_msg_id"] = edited_msg.id
            elif hasattr(event_or_client, 'msg_id') and event_or_client.msg_id:
                state["board_msg_id"] = event_or_client.msg_id
            elif hasattr(event_or_client, 'message') and event_or_client.message:
                state["board_msg_id"] = event_or_client.message.id
                
            return
        except MessageNotModifiedError:
            # Если содержимое не изменилось, просто гасим ошибку
            return
        except Exception as e:
            # Любая другая непредвиденная ошибка при клике (например, если инлайн-событие устарело)
            print(f"[Ошибка редактирования при клике]: {e}")
            # Не делаем тут return, чтобы в случае падения event-а код попробовал обновиться через Сценарий 2 или 3!

    # 2. Если вызов из фона (listen_opponent_moves) — редактируем по сохраненному board_msg_id
    board_msg_id = state.get("board_msg_id")
    if board_msg_id:
        try:
            await client.edit_message(user_id, board_msg_id, message_content, buttons=chess_buttons)
            return
        except MessageNotModifiedError:
            return
        except Exception as e:
            print(f"[Ошибка редактирования доски из фона]: {e}")

    # 3. Самый крайний случай (если сообщения еще нет в истории или оно было удалено) — отправляем новое
    try:
        msg = await client.send_message(user_id, message_content, buttons=chess_buttons)
        state["board_msg_id"] = msg.id
    except Exception as e:
        print(f"[Ошибка отправки новой доски]: {e}")

async def handle_cell_click(event: events.CallbackQuery.Event):
    """
    Обработчик кликов по кнопкам шахматной доски.
    """
    user_id = event.sender_id
    state = user_state.get(user_id)
    
    if not state or not state.get("game_id"):
        await event.answer("⚠️ Вы не находитесь в активной игре.", alert=True)
        return
        
    fen = state["current_fen"]
    my_color = state["my_color"]
    game_id = state["game_id"]
    
    if not is_my_turn(fen, my_color):
        await event.answer("⏳ Сейчас ход вашего оппонента! Ожидайте.", alert=True)
        return
        
    cell = event.data.decode('utf-8').split('_')[1]
    selected = state["selected_piece"]
    
    if not selected:
        user_state[user_id]["selected_piece"] = cell
        await send_game_board(event, user_id)
        await event.answer(f"Выбрана клетка {cell}")
    else:
        if selected == cell:
            user_state[user_id]["selected_piece"] = None
            await send_game_board(event, user_id)
            return
            
        move_str = f"{selected}{cell}"
        token = get_token()
        
        result = await asyncio.to_thread(make_chess_move, token, game_id, move_str)
        
        # --- ПЕРЕХВАТЫВАЕМ КОНЕЦ ИГРЫ И ОШИБКИ ---
        if isinstance(result, dict) and ("detail" in result or result.get("status") == "error"):
            msg = result.get("detail", "")
            
            # Если игра УЖЕ завершена (кто-то поставил мат ранее)
            if "Game already finished" in str(msg) or "Game already finished" in str(result):
                # Перепроверяем финальный статус игры на бэкенде, чтобы узнать КТО победил
                token = get_token()
                game_data = await asyncio.to_thread(get_game_board, token, game_id)
                
                user_state[user_id] = None # Локально закрываем игру в любом случае
                
                if game_data and isinstance(game_data, dict):
                    game_info = game_data.get("game", {})
                    # Пытаемся понять по FEN или победителю, но самый простой вариант:
                    # Раз игра уже была завершена до твоего клика — значит, мат поставили ТЕБЕ!
                    await event.edit("💔 Партия завершена. Вам поставили ШАХ и МАТ. Оппонент победил!", buttons=main_menu)
                else:
                    await event.edit("🏁 Партия завершена!", buttons=main_menu)
                return
                
            # Обычный нелегальный ход
            if isinstance(msg, list) and len(msg) > 0:
                msg = msg[0].get("msg", "Ошибка валидации параметров")
            elif not msg:
                msg = "Нелегальный ход по правилам шахмат!"
                
            await event.answer(f"⚠️ {msg}", alert=True)
            user_state[user_id]["selected_piece"] = None
            await send_game_board(event, user_id)
            return
            
        if not result:
            await event.answer("⚠️ Ошибка связи с сервером при отправке хода.", alert=True)
            user_state[user_id]["selected_piece"] = None
            await send_game_board(event, user_id)
            return
            
        # Если ход успешный
        game_info = result.get("game", {}) if "game" in result else result
        board_info = game_info.get("board", {}) if "board" in game_info else result.get("board", {})
        
        new_fen = board_info.get("fen")
        game_status = game_info.get("status")
        
        # Если ИМЕННО ЭТОТ твой ход привел к мату (бэк вернул 200 и статус finished)
        if game_status in ["finished", "surrendered"]:
            user_state[user_id] = None
            await event.edit("🎉 Поздравляем! Вы поставили ШАХ и МАТ! Победа! 🏆", buttons=main_menu)
            return
            
        if new_fen:
            user_state[user_id]["current_fen"] = new_fen
            user_state[user_id]["selected_piece"] = None
            await send_game_board(event, user_id)

async def handle_surrender_click(event: events.CallbackQuery.Event):
    """
    Обработчик кнопки сдаться. Получает UUID игрока, передает его в API,
    после чего выбрасывает в главное меню обоих оппонентов.
    """
    user_id = event.sender_id
    state = user_state.get(user_id)
    
    if not state or not state.get("game_id"):
        await event.answer("⚠️ Активная игра не найдена.", alert=True)
        return
        
    token = get_token()
    
    # 1. Получаем профиль юзера, чтобы вытащить его UUID (бэк требует UUID игрока для сдачи)
    me = get_user(token, user_id)
    if not me or not isinstance(me, dict) or not me.get("searched"):
        await event.answer("❌ Ошибка профиля. Не удалось получить UUID для отправки на сервер.", alert=True)
        return
        
    user_uuid = me["searched"][0].get("id")
    
    # 2. Шлем запрос на бэкенд и передаем именно USER_UUID, чтобы закрыть сессию в БД
    await asyncio.to_thread(surrender_game, token, user_uuid)
    
    opponent_tg_id = state.get("opponent_tg_id")
    game_id = state.get("game_id")
    
    # 3. Выбрасываем текущего (кто нажал кнопку) игрока в главное меню
    user_state[user_id] = None
    await event.edit("🏳️ Вы сдались! Игра завершена.", buttons=main_menu)
    
    # 4. Автоматически переводим противника в главное меню, если у нас сохранен его TG ID
    if opponent_tg_id:
        opp_state = user_state.get(opponent_tg_id)
        # Проверяем, что противник все еще находится в этой же игре
        if opp_state and opp_state.get("game_id") == game_id:
            user_state[opponent_tg_id] = None # Чистим стейт противника, чтобы заглушить его фоновый цикл
            
            try:
                opp_msg_id = opp_state.get("board_msg_id")
                if opp_msg_id:
                    # Редактируем сообщение доски соперника, сообщая о победе
                    await event.client.edit_message(
                        opponent_tg_id, opp_msg_id, 
                        "🎉 Противник сдался! Вы победили! Партия завершена.", 
                        buttons=main_menu
                    )
                else:
                    # Если ID сообщения доски соперника не найден, просто шлем ему новое сообщение
                    await event.client.send_message(
                        opponent_tg_id, 
                        "🎉 Противник сдался! Вы победили! Партия завершена.", 
                        buttons=main_menu
                    )
            except Exception as e:
                print(f"[Ошибка уведомления оппонента о сдаче]: {e}")

async def start_ai_game_handler(event: events.CallbackQuery.Event):
    """ Максимально защищенный обработчик старта игры с ИИ с обходом зависших сессий """
    user_id = event.sender_id
    level_chosen = event.data.decode('utf-8')
    token = get_token()
    
    difficulty_map = {"easy": 1, "medium": 3, "hard": 4}
    ai_diff = difficulty_map.get(level_chosen, 3)
    
    rating_map = {"easy": "400", "medium": "1000", "hard": "1500"}
    ai_rating = rating_map.get(level_chosen, "1000")
    
    # Сбрасываем стейты поиска в памяти бота сразу
    user_state[user_id] = {"searching": False}
    
    me = get_user(token, user_id)
    if not me or not isinstance(me, dict) or not me.get("searched"):
        await event.answer("❌ Ошибка профиля (Бэк недоступен)", alert=True)
        return
        
    user_uuid = me["searched"][0].get("id")
    my_color = "white" 
    
    await event.edit("🤖 Сбрасываем старую игру и подключаем ИИ...")
    
    # ПРИНУДИТЕЛЬНЫЙ СБРОС СЕССИИ
    # 1. Сначала отменяем поиск на бэке, если он завис
    try:
        await asyncio.to_thread(stop_search_opponent, token, user_uuid)
    except Exception as e:
        print(f"[Отладка] Ошибка stop_search_opponent: {e}")
        
    # 2. Принудительно сдаемся в старой игре по твоему UUID (на случай, если бот упал)
    try:
        await asyncio.to_thread(surrender_game, token, user_uuid)
    except Exception as e:
        print(f"[Отладка] Ошибка surrender_game: {e}")
        
    await asyncio.sleep(0.8) # Даем бэкенду Марка «продышаться» и обновить БД
    
    # 3. Пробуем создать игру с ИИ
    res = None
    try:
        res = await asyncio.to_thread(start_ai_game, token, user_uuid, my_color, ai_diff)
    except Exception as e:
        print(f"[КРИТИЧЕСКАЯ ОШИБКА АПИ] start_ai_game упал: {e}")
        await event.edit(f"❌ Бэкенд не отвечает на запрос ИИ.\nОшибка: {e}", buttons=main_menu)
        return

    # Проверяем ответ сервера
    if not res:
        await event.edit("❌ Бэкенд вернул пустой ответ (None). Проверь, запущен ли сервер", buttons=main_menu)
        return
        
    if res.status_code != 200:
        await event.edit(f"❌ Не удалось начать игру. Бэк вернул ошибку. (Код: {res.status_code})", buttons=main_menu)
        return
        
    # Если всё прошло успешно, парсим игру
    try:
        data = res.json()
        game_info = data.get("game", {})
        real_game_id = game_info.get("id")
        fen = game_info.get("board", {}).get("fen")
        
        user_state[user_id] = {
            "searching": False,
            "game_id": real_game_id,
            "my_color": my_color,
            "opponent_name": "ИИ",            
            "opponent_rating": ai_rating,     
            "opponent_tg_id": None,
            "current_fen": fen,
            "selected_piece": None,
            "board_msg_id": event.message_id,
            "is_ai": True
        }
        
        # Рисуем доску и запускаем прослушку ходов
        await send_game_board(event.client, user_id)
        asyncio.create_task(listen_opponent_moves(event.client, user_id, real_game_id))
        
    except Exception as e:
        print(f"[Ошибка парсинга ответа ИИ]: {e}")
        await event.edit("❌ Ошибка при инициализации шахматной доски.", buttons=main_menu)