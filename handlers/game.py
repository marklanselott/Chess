from telethon import events, Button
import asyncio

from menus import main_menu, play_menu, level, play_back, cancel_search_btn
from state import user_state
from api import await_opponent, get_token, get_user, start_search_opponent, stop_search_opponent, await_opponent, get_game_board, make_chess_move, surrender_game
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


async def play(event: events.CallbackQuery.Event):
    await event.edit("Выберите режим:", buttons=play_menu)


async def playback(event: events.CallbackQuery.Event):
    console_active.clear()
    await event.edit("Вернулись, выбирайте:", buttons=main_menu)


async def offline(event: events.CallbackQuery.Event):
    await event.edit("Выберите уровень сложности", buttons=level)

async def listen_opponent_moves(client, user_id, game_id):
    """
    Фоновый цикл: раз в 2 секунды проверяет, не изменился ли FEN на сервере.
    Если соперник сделал ход — обновляет доску на экране.
    """
    token = get_token()
    print(f"[Фон] Запущено отслеживание ходов соперника для игрока {user_id}")
    
    while True:
        try:
            # 1. Проверяем, активна ли еще игра в памяти нашего бота
            state = user_state.get(user_id)
            if not state or state.get("game_id") != game_id or not state.get("searching") is False:
                # Если игрок сдался, игра закрылась или началась новая — тушим этот цикл
                break
                
            # 2. Запрашиваем состояние доски с сервера
            game_data = await asyncio.to_thread(get_game_board, token, game_id)
            if not game_data:
                await asyncio.sleep(2)
                continue
                
            game_info = game_data.get("game", {})
            server_fen = game_info.get("board", {}).get("fen")
            
            # 3. Если FEN на сервере отличается от того, что сохранен у нас
            if server_fen and server_fen != state.get("current_fen"):
                print(f"[Фон] Обнаружен ход соперника в игре {game_id}!")
                
                # Обновляем FEN в памяти бота
                user_state[user_id]["current_fen"] = server_fen
                user_state[user_id]["selected_piece"] = None # Сбрасываем выделение, если оно стояло
                
                # Нам нужно отправить обновленную доску. 
                # Так как у нас в фоновом цикле нет объекта 'event', мы создаем фейковый контекст 
                # или передаем client напрямую, чтобы отредактировать последнее сообщение.
                # Для простоты — отправляем доску новым сообщением через client:
                await send_game_board(client, user_id)
                
            # Делаем паузу в 2 секунды перед следующей проверкой, чтобы не спамить API
            await asyncio.sleep(2)
            
        except Exception as e:
            print(f"[Фон Ошибка]: {e}")
            await asyncio.sleep(2)
            
    print(f"[Фон] Отслеживание ходов соперника для {user_id} успешно остановлено.")

async def search_opponent(event: events.CallbackQuery.Event):
    user_id = event.sender_id
    token = get_token()
    
    # 1. Получаем профиль, чтобы узнать свой UUID ($uuid)
    me = get_user(token, user_id)
    if not me.get("searched"):
        await event.answer("❌ Ошибка профиля", alert=True)
        return

    user_uuid = me["searched"][0].get("id")

    if user_state.get(user_id, {}).get("searching"):
        return

    user_state[user_id] = {"searching": True}

    # Сбрасываем старую сессию поиска
    await asyncio.to_thread(stop_search_opponent, token, user_uuid)
    await asyncio.sleep(0.5) 

    # Стартуем поиск
    res_start = await asyncio.to_thread(start_search_opponent, token, user_uuid)
    
    if res_start.status_code != 200:
        user_state[user_id]["searching"] = False
        if res_start.status_code == 400:
            btn_fix = [[Button.inline("⚙️ Глубокий сброс сессии", data="force_api_stop")]]
            await event.edit(
                "⚠️ **Сервер все еще не отпустил сессию.**\n"
                "Нажмите 'Глубокий сброс' и подождите пару секунд перед новым поиском.", 
                buttons=btn_fix
            )
        else:
            await event.edit(f"❌ Ошибка старта поиска: {res_start.status_code}\n{res_start.text}")
        return

    await event.edit("🔎 **Поиск оппонента...**", buttons=cancel_search_btn)

    try:
        while user_state.get(user_id, {}).get("searching") is True:
            print(f"[Поиск] Игрок {user_id} отправляет запрос в await_opponent...")
            
            try:
                # Опрашиваем бэк Марка внутри потока
                data = await asyncio.to_thread(await_opponent, token, user_uuid)
            except Exception as e:
                print(f"[Поиск] Запрос await_opponent вылетел по ошибке: {e}")
                data = None
            
            if not user_state.get(user_id, {}).get("searching"): 
                break

            print(f"[Поиск] Игрок {user_id} получил из await_opponent данные: {data}")

            # --- 🛡️ ЖЕЛЕЗОБЕТОННАЯ СТРАХОВКА ДЛЯ ПЕРВОГО ИГРОКА ---
            # Если бэк разорвал коннект (вернул None, ошибку или пустую строку),
            # мы принудительно проверяем базу данных Марка через get_game_board
            if data is None or data == "None":
                print(f"⚠️ [Защита] У игрока {user_id} пустой ответ. Проверяем get_game_board принудительно...")
                board_data = await asyncio.to_thread(get_game_board, token, user_uuid)
                print(f"[Защита] Ответ от get_game_board для {user_id}: {board_data}")
                
                if board_data and board_data.get("game"):
                    print(f"🎯 [Защита] КРАСАВЧИК! Игра реально найдена в БД для первого игрока ({user_id})!")
                    game_info = board_data["game"]
                    
                    # Вычисляем UUID соперника
                    opp_uuid = game_info.get("black") if game_info.get("white") == user_uuid else game_info.get("white")
                    
                    # Подменяем data так, чтобы сработал стандартный блок успеха ниже
                    data = {
                        "game": game_info,
                        "opponent": {"id": opp_uuid, "unique": "Оппонент", "rating": 400}
                    }
                else:
                    print(f"[Защита] Активной игры в БД для {user_id} пока нет. Продолжаем поиск.")
                    await asyncio.sleep(1)
                    continue
            # ----------------------------------------------------

            # Обработка обычного таймаута пула (404)
            if data == "404":
                await asyncio.sleep(0.2)
                continue

            # ОБРАБОТКА УСПЕХА (Сюда зайдут ОБА игрока — и второй напрямую, и первый через страховку)
            if isinstance(data, dict) and data.get("opponent"):
                user_state[user_id]["searching"] = False
                opponent = data["opponent"]
                
                print(f"🎉 ПАРА НАШЛАСЬ в коде для {user_id}! Инициализируем матч...")
                
                real_game_id = None
                fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
                my_color = "white"
                
                if data.get("game"):
                    game_info = data["game"]
                    real_game_id = game_info.get("id")
                    fen = game_info.get("board", {}).get("fen", fen)
                    is_white = game_info.get("white") == user_uuid
                    my_color = "white" if is_white else "black"
                else:
                    board_data = await asyncio.to_thread(get_game_board, token, user_uuid)
                    if board_data and board_data.get("game"):
                        game_info = board_data["game"]
                        real_game_id = game_info.get("id")
                        fen = game_info.get("board", {}).get("fen", fen)
                        is_white = game_info.get("white") == user_uuid
                        my_color = "white" if is_white else "black"

                if not real_game_id:
                    print(f"❌ КРИТИКА: Игрок {user_id} не смог вытащить game_id матча.")
                    await event.edit("⚠️ Ошибка синхронизации ID матча.", buttons=play_menu)
                    return

                print(f"✅ Игрок {user_id} зафиксировал game_id: {real_game_id}. Включаем доску!")

                # Записываем всё в стейт юзера
                user_state[user_id] = {
                    "searching": False,
                    "game_id": real_game_id, 
                    "my_color": my_color,
                    "opponent_name": opponent.get("unique") or opponent.get("first_name") or "Оппонент",
                    "opponent_rating": opponent.get("rating", 0),
                    "current_fen": fen,
                    "selected_piece": None
                }
                
                color_emoji = "⚪ Белыми фигурами" if my_color == "white" else "⚫ Черными фигурами"
                match_msg = (
                    f"✅ **Игра найдена!**\n\n"
                    f"👤 **Противник:** {user_state[user_id]['opponent_name']} (⭐ {user_state[user_id]['opponent_rating']})\n"
                    f"🏳️ **Вы играете:** {color_emoji}\n"
                )
                await event.edit(match_msg)
                
                # Рисуем доску (теперь она железно откроется у обоих!)
                await send_game_board(event, user_id)
                
                # Запускаем прослушку ходов соперника
                asyncio.create_task(listen_opponent_moves(event.client, user_id, real_game_id))
                return 
                
            await asyncio.sleep(0.5)
            
    except Exception as e:
        print(f"❌ ОШИБКА В ПОИСКЕ: {e}")
        await event.edit(f"⚠️ Ошибка создания матча: {e}")
        
    finally:
        if user_id in user_state and user_state[user_id].get("searching"):
            user_state[user_id]["searching"] = False

async def callback_force_api_stop(event):
    user_id = event.sender_id
    token = get_token()
    
    # 1. Принудительно сбрасываем флаги в памяти бота, чтобы оживить меню
    if user_id in user_state:
        user_state[user_id]["searching"] = False
        user_state[user_id]["selected_piece"] = None

    # 2. Получаем UUID игрока
    me = get_user(token, user_id)
    if not me.get("searched"):
        await event.answer("❌ Ошибка профиля. Не удалось получить UUID.", alert=True)
        return
        
    user_uuid = me["searched"][0].get("id")
    
    # 3. Пинаем сервер через твою готовую функцию, обернутую в поток
    await asyncio.to_thread(stop_search_opponent, token, user_uuid)
        
    # 4. Обновляем интерфейс юзеру
    await event.answer("⚙️ Сессия сброшена!", alert=True)
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

async def send_game_board(event, user_id):
    state = user_state.get(user_id)
    if not state:
        return
        
    fen = state["current_fen"]
    selected = state["selected_piece"] 
    opponent_name = state["opponent_name"]
    opponent_rating = state["opponent_rating"]
    my_color = "Белые ⚪" if state["my_color"] == "white" else "Черные ⚫"
    
    # Генерируем сетку кнопок 8х8 + кнопку сдачи внизу
    chess_buttons = generate_chess_keyboard(fen, selected_cell=selected)
    
    # Текст сообщения
    message_content = (
        f"⚔️ **Партия против:** @{opponent_name} (⭐ {opponent_rating})\n"
        f"🏳️ **Ваш цвет:** {my_color}\n"
        f"ℹ️ *Нажимайте на кнопки-клетки, чтобы сделать ход.*"
    )
    
    # 1. Проверяем, если это CallbackQuery (нажатие инлайн-кнопки) — редактируем старое сообщение
    if hasattr(event, 'edit'):
        try:
            await event.edit(message_content, buttons=chess_buttons)
            return
        except Exception:
            pass  # Если отредактировать не получилось, код пойдет дальше и отправит новое

    # 2. Проверяем, если это вызов из фона (передан client) — отправляем новое сообщение напрямую юзеру
    if hasattr(event, 'send_message'):
        await event.send_message(user_id, message_content, buttons=chess_buttons)
    else:
        # 3. Запасной вариант для обычных текстовых эвентов (NewMessage)
        await event.respond(message_content, buttons=chess_buttons)

async def handle_cell_click(event: events.CallbackQuery.Event):
    user_id = event.sender_id
    state = user_state.get(user_id)
    
    # 1. Проверяем, идет ли игра
    if not state or not state.get("game_id"):
        await event.answer("⚠️ Вы не в игре.", alert=True)
        return
        
    game_id = state["game_id"]
    # Вытаскиваем имя клетки из data кнопки (например, из "cell_e2" получаем "e2")
    clicked_cell = event.data.decode('utf-8').split('_')[1]
    
    selected_before = state.get("selected_piece")
    token = get_token()

    # Сценарий А: Игрок нажимает на клетку первый раз (выбирает фигуру)
    if not selected_before:
        # Записываем выбранную клетку в память
        user_state[user_id]["selected_piece"] = clicked_cell
        await event.answer(f"Выбрано поле {clicked_cell.upper()}")
        
        # Перерисовываем доску, чтобы фигура взялась в фигурные скобки { }
        await send_game_board(event, user_id)
        return

    # Сценарий Б: Игрок нажал на ту же самую фигуру второй раз — сбрасываем выделение
    if selected_before == clicked_cell:
        user_state[user_id]["selected_piece"] = None
        await event.answer("Выделение снято")
        await send_game_board(event, user_id)
        return

    # Сценарий В: У игрока уже выбрана фигура, и он жмет на ДРУГУЮ клетку (делает ход)
    # Формируем строку хода, например "e2" + "e4" = "e2e4"
    full_move = f"{selected_before}{clicked_cell}"
    
    await event.answer("⚡ Обработка хода сервером...")
    
    # Отправляем ход в API админа (это GET запрос согласно тестам)
    result = await asyncio.to_thread(make_chess_move, token, game_id, full_move)
    
    if not result:
        await event.answer("❌ Ошибка отправки хода. Возможно, сейчас не ваш ход.", alert=True)
        user_state[user_id]["selected_piece"] = None
        await send_game_board(event, user_id)
        return
        
    # Если бэк вернул ошибку валидации FastAPI (FastAPI Validation Error) или кастомную ошибку
    if "detail" in result or result.get("status") == "error":
        msg = result.get("detail", "Нелегальный ход по правилам шахмат!")
        # Если detail прилетел списком (ошибка валидации), достаем красивый текст
        if isinstance(msg, list) and len(msg) > 0:
            msg = msg[0].get("msg", "Ошибка валидации параметров")
            
        await event.answer(f"⚠️ {msg}", alert=True)
        user_state[user_id]["selected_piece"] = None
        await send_game_board(event, user_id)
        return

    # --- ИСПРАВЛЕННЫЙ ПАРСИНГ СТРОГО ПО ТЕСТАМ АДМИНА ---
    # В ответе move_piece объект board лежит в корне: result["board"]["fen"]
    board_info = result.get("board", {})
    new_fen = board_info.get("fen")
    
    if new_fen:
        # Обновляем состояние игры новой расстановкой
        user_state[user_id]["current_fen"] = new_fen
        user_state[user_id]["selected_piece"] = None # Сбрасываем выделение
        
        # Обновляем кнопочную доску на экране у себя
        await send_game_board(event, user_id)
    else:
        # Запасной вариант на случай, если структура вернулась старая
        game_info = result.get("game", {})
        fallback_fen = game_info.get("board", {}).get("fen")
        
        if fallback_fen:
            user_state[user_id]["current_fen"] = fallback_fen
            user_state[user_id]["selected_piece"] = None
            await send_game_board(event, user_id)
        else:
            await event.answer("⚠️ Ход сделан, но сервер не вернул FEN доски.", alert=True)

async def handle_surrender_click(event: events.CallbackQuery.Event):
    user_id = event.sender_id
    state = user_state.get(user_id)
    
    # Проверяем, идет ли вообще игра у этого пользователя
    if not state or not state.get("game_id"):
        await event.answer("⚠️ Вы не находитесь в активной игре.", alert=True)
        return
        
    token = get_token()
    
    # Чтобы вызвать surrender_game, нам нужен UUID пользователя на бэкенде.
    # Достанем его через get_user, как ты делал в поиске оппонента.
    me = get_user(token, user_id)
    if not me.get("searched"):
        await event.answer("❌ Ошибка профиля на API", alert=True)
        return
        
    user_uuid = me["searched"][0].get("id")
    
    # Показываем всплывающее уведомление, что запрос обрабатывается
    await event.answer("Отправка запроса на сервер...")
    
    # Вызываем асинхронно эндпоинт POST /api/game/surrender
    res = await asyncio.to_thread(surrender_game, token, user_uuid)
    
    # Очищаем состояние игры в оперативной памяти бота, возвращая его в обычный режим
    user_state[user_id] = {
        "searching": False,
        "game_id": None,
        "my_color": None,
        "current_fen": None,
        "selected_piece": None
    }
    
    # Изменяем сообщение с доской, сообщая, что игра завершена сдачей
    from menus import main_menu # Импортируем твое главное меню для возврата
    
    await event.edit(
        "🏳️ **Вы сдались.** Партия завершена досрочно.\n\n"
        "Вы вернулись в главное меню. Можете начать новый поиск!",
        buttons=main_menu
    )