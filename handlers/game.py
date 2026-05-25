from telethon import events, Button
import asyncio
import json
import re
from telethon.errors import MessageNotModifiedError
from menus import main_menu, play_menu, level, play_back, cancel_search_btn
from state import user_state
from api import await_opponent, get_token, get_user, start_game_analysis, get_analysis_status, start_search_opponent, stop_search_opponent, get_game_board, make_chess_move, surrender_game, start_ai_game
from chess_board import generate_chess_keyboard


console_active = asyncio.Event()


def normalize_color(color):
    if color is None:
        return None
    c = str(color).strip().lower()
    if c in ("w", "white", "белый", "белые", "white", "белые ", "white ", "w "):
        return "white"
    if c in ("b", "black", "черный", "черные", "black", "черные ", "black ", "b "):
        return "black"
    if c in ("1", "0", "first", "1st", "whiteplayer", "whiteplayer "):
        return "white"
    if c in ("2", "second", "2nd", "blackplayer", "blackplayer "):
        return "black"
    return c


def get_end_reason_text(reason_code: str):
    if reason_code is None:
        return "Рішення серверу"
    normalized = str(reason_code).strip().lower()
    reason_map = {
        "mate": "Мат",
        "checkmate": "Мат",
        "stalemate": "Пат (у гравця немає доступних ходів)",
        "draw": "Нічия за домовленістю або за правилами",
        "patch": "Нічия",
        "resign": "Здача суперника",
        "surrendered": "Здача суперника",
        "timeout": "Час закінчився",
        "finished": "Гру завершено",
        "game over": "Гру завершено",
    }
    return reason_map.get(normalized, f"Рішення серверу ({reason_code})")


def build_endgame_texts(my_color, winner_color, reason_text, winner_data=None, is_ai=False):
    my_color = normalize_color(my_color)
    winner_color = normalize_color(winner_color)

    if winner_color == my_color and winner_color in ("white", "black"):
        if is_ai:
            # For AI games, don't show rating
            text_me = (
                f"🏁 **Гру завершено!**\n🎉 **Результат:** Ви перемогли! 🏆\n💬 **Причина:** {reason_text}"
            )
        else:
            new_rating = winner_data.get("after", "---") if isinstance(winner_data, dict) else "---"
            text_me = (
                f"🏁 **Гру завершено!**\n🎉 **Результат:** Ви перемогли! 🏆\n💬 **Причина:** {reason_text}\n📈 Ваш новий рейтинг: {new_rating}"
            )
        text_opp = f"🏁 **Гру завершено!**\n💔 **Результат:** Ви програли.\n💬 **Причина:** {reason_text}"
    elif winner_color in ("white", "black") and winner_color != my_color:
        text_me = f"🏁 **Гру завершено!**\n💔 **Результат:** Ви програли.\n💬 **Причина:** {reason_text}"
        text_opp = f"🏁 **Гру завершено!**\n🎉 **Результат:** Ви перемогли! 🏆\n💬 **Причина:** {reason_text}"
    else:
        text_me = f"🏁 **Гру завершено!**\n🤝 **Результат:** Нічия.\n💬 **Причина:** {reason_text}"
        text_opp = text_me

    return text_me, text_opp


def format_result_data(result_block, game_status=None, game_obj=None):
    result_data = result_block or {}
    if not isinstance(result_data, dict):
        return {
            "winner_color": None,
            "reason_text": get_end_reason_text(str(game_status or "finished")),
            "winner_data": {},
        }

    winner_info = result_data.get("winner")
    if winner_info is None:
        # Some backends may expose the winner directly or via a separate field.
        winner_info = result_data.get("winner_color") or result_data.get("winner_data")

    winner_data = winner_info if isinstance(winner_info, dict) else {}
    if isinstance(winner_info, dict):
        winner_color = normalize_color(
            winner_info.get("color")
            or winner_info.get("winner_color")
            or winner_info.get("side")
            or winner_info.get("team")
            or winner_info.get("color_name")
            or winner_info.get("player_color")
        )

        if not winner_color:
            winner_uid = winner_info.get("user_id") or winner_info.get("id")
            if winner_uid and isinstance(game_obj, dict):
                white_id = game_obj.get("white")
                black_id = game_obj.get("black")
                if white_id and str(winner_uid) == str(white_id):
                    winner_color = "white"
                elif black_id and str(winner_uid) == str(black_id):
                    winner_color = "black"
    else:
        winner_color = normalize_color(winner_info)

    if not winner_color and isinstance(result_data.get("winner"), dict):
        winner_color = normalize_color(result_data.get("winner").get("color"))

    reason_code = result_data.get("reason") or game_status or result_data.get("status")
    reason_text = get_end_reason_text(str(reason_code))

    return {
        "winner_color": winner_color,
        "reason_text": reason_text,
        "winner_data": winner_data,
    }


async def notify_end_game(event_or_client, user_id, opponent_tg_id, text_me, buttons_me, text_opp, buttons_opp):
    client = event_or_client.client if hasattr(event_or_client, "client") else event_or_client
    opp_state = user_state.get(opponent_tg_id) if opponent_tg_id else None

    user_state[user_id] = None
    if opponent_tg_id and opponent_tg_id in user_state:
        user_state[opponent_tg_id] = None

    if hasattr(event_or_client, "edit"):
        try:
            await event_or_client.edit(text_me, buttons=buttons_me)
        except Exception:
            await client.send_message(user_id, text_me, buttons=buttons_me)
    else:
        await client.send_message(user_id, text_me, buttons=buttons_me)

    if opponent_tg_id:
        try:
            if opp_state and opp_state.get("board_msg_id"):
                await client.edit_message(opponent_tg_id, opp_state["board_msg_id"], text_opp, buttons=buttons_opp)
            else:
                await client.send_message(opponent_tg_id, text_opp, buttons=buttons_opp)
        except Exception as e:
            print(f"Ошибка уведомления оппонента о завершении партии {opponent_tg_id}: {e}")


def parse_game_finish_data(game_obj, my_color, is_ai=False):
    if not isinstance(game_obj, dict):
        return None

    result_block = game_obj.get("result")
    inner_game = game_obj.get("game", game_obj)
    if not result_block:
        result_block = inner_game.get("result")

    game_status = inner_game.get("status") or game_obj.get("status")

    if not result_block and game_status not in ("finished", "surrendered"):
        return None

    parsed = format_result_data(result_block or inner_game, game_status, inner_game)
    text_me, text_opp = build_endgame_texts(my_color, parsed["winner_color"], parsed["reason_text"], parsed["winner_data"], is_ai=is_ai)
    return {
        "text_me": text_me,
        "text_opp": text_opp,
        "buttons_me": [[Button.inline("📊 Аналіз гри", data=f"start_analysis_{inner_game.get('id', '')}_{my_color}")], [Button.inline("◀️ Назад в меню", data="play_back")]],
        "buttons_opp": [[Button.inline("📊 Аналіз гри", data=f"start_analysis_{inner_game.get('id', '')}_{'black' if normalize_color(my_color) == 'white' else 'white'}")], [Button.inline("◀️ Назад в меню", data="play_back")]],
    }


def is_my_turn(fen: str, my_color: str) -> bool:
    """ Helper to determine if it's user's turn based on FEN """
    try:
        parts = fen.split()
        if len(parts) > 1:
            active_color = parts[1]  # 'w' or 'b'
            my_color = normalize_color(my_color)
            if active_color == 'w':
                return my_color == 'white'
            if active_color == 'b':
                return my_color == 'black'
    except Exception:
        pass
    return True


def is_promotion_move(from_cell: str, to_cell: str, my_color: str) -> bool:
    """
    Определяет, является ли ход пешки превращением
    """
    try:
        to_rank = int(to_cell[1])
        is_white = normalize_color(my_color) == "white"
        
        if is_white and to_rank == 8:
            return True
        elif not is_white and to_rank == 1:
            return True
    except Exception:
        pass
    
    return False

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
    bot.add_event_handler(trigger_analysis_handler, events.CallbackQuery(pattern=r'^start_analysis_(.+)'))
    bot.add_event_handler(handle_analysis_navigation, events.CallbackQuery(pattern=r'^analysis_(prev|next)_\d+$'))
    bot.add_event_handler(handle_promotion_choice, events.CallbackQuery(pattern=r'^promotion_(q|r|b|n)$'))

async def play(event: events.CallbackQuery.Event):
    await event.edit("Виберіть режим:", buttons=play_menu)


async def playback(event: events.CallbackQuery.Event):
    console_active.clear()
    await event.edit("Повернулись, виберіть:", buttons=main_menu)


async def offline(event: events.CallbackQuery.Event):
    await event.edit("Виберіть рівень складності", buttons=level)

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
            if active_color == 'w' and normalize_color(my_color) == "white":
                is_my_turn = True
            elif active_color == 'b' and normalize_color(my_color) == "black":
                is_my_turn = True

            is_ai = state.get("is_ai", False)
            
            # Если сейчас НАШ ХОД в онлайн-игре, просто ждем клика игрока по кнопкам-клеткам
            if is_my_turn and not is_ai:
                await asyncio.sleep(3)
                continue

            if not is_my_turn and is_ai:
                # === РЕЖИМ ИГРЫ С ИИ ===
                ai_res = await asyncio.to_thread(make_ai_move, token, game_id)
                
                if ai_res and ai_res.status_code == 200:
                    ai_data = ai_res.json()
                    # DEBUG: выводим JSON ответа для анализа промоции
                    print(f"\n[ХОД ИИ] AI MOVE RESPONSE:")
                    print(f"[API RESPONSE] {json.dumps(ai_data, indent=2, ensure_ascii=False)}\n")
                    parsed = parse_game_finish_data(ai_data, my_color, is_ai=True)
                    new_fen = None
                    if isinstance(ai_data, dict):
                        ai_game = ai_data.get("game", ai_data)
                        new_fen = ai_game.get("board", {}).get("fen")
                        game_status = ai_game.get("status")
                    else:
                        game_status = None

                    if parsed:
                        await notify_end_game(client, user_id, None, parsed["text_me"], parsed["buttons_me"], parsed["text_opp"], parsed["buttons_opp"])
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
                    
                    if game_status in ["finished", "surrendered"]:
                        parsed = parse_game_finish_data(game_data, my_color, is_ai=False)
                        if parsed:
                            await notify_end_game(client, user_id, state.get("opponent_tg_id"), parsed["text_me"], parsed["buttons_me"], parsed["text_opp"], parsed["buttons_opp"])
                        else:
                            user_state[user_id] = None
                            await client.send_message(user_id, "🏁 Партія завершена! Суперник сдався або гра закінчена.", buttons=main_menu)
                        break
                    
                    # Если игра идет и FEN на сервере изменился — обновляем доску
                    if server_fen and server_fen != current_fen:
                        user_state[user_id]["current_fen"] = server_fen
                        user_state[user_id]["selected_piece"] = None
                        await send_game_board(client, user_id)

            await asyncio.sleep(3)
            
        except Exception:
            await asyncio.sleep(3)

async def search_opponent(event: events.CallbackQuery.Event):
    user_id = event.sender_id
    token = get_token()
    
    me = get_user(token, user_id)
    # Защита: проверяем, что ответ от сервера вообще пришел и это словарь
    if not me or not isinstance(me, dict) or not me.get("searched"):
        await event.answer("❌ Помилка профілю", alert=True)
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
    if not res_start or res_start.status_code != 200:
        user_state[user_id]["searching"] = False
        error_msg = "Помилка при старті пошуку." if res_start else "Не вдалося підключитися до сервера пошуку."
        print(f"[ПОИСК] {error_msg}")
        await event.edit(f"❌ {error_msg}", buttons=play_menu)
        return

    await event.edit("🔍 Шукаємо суперника...", buttons=[cancel_search_btn])

    print(f"[ПОИСК] Начинаем ожидание оппонента для user_uuid={user_uuid}")
    
    # Запускаем long-polling ожидания с более долгим сроком
    data = await asyncio.to_thread(await_opponent, token, user_uuid)
    
    # DEBUG логирование
    print(f"[ПОИСК ОППОНЕНТА] Получен ответ: {type(data).__name__}")
    if isinstance(data, dict):
        print(f"[ПОИСК ОППОНЕНТА] Ответ: {data}")
    else:
        print(f"[ПОИСК ОППОНЕНТА] Ответ (строка/None): {data}")
    
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
            await event.edit("⚠️ Помилка синхронізації ID матчу.", buttons=play_menu)
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
            "is_ai": False,
            "current_fen": fen,
            "selected_piece": None,
            "board_msg_id": current_msg_id  # Сохраняем вычисленный ID сообщения
        }
        
        # Первичная отрисовка доски поверх текста поиска
        await send_game_board(event, user_id)
        
        # Запускаем фоновый трекер ходов соперника
        asyncio.create_task(listen_opponent_moves(event.client, user_id, real_game_id))
    else:
        # Ошибка: не найден оппонент или произошла ошибка сети
        user_state[user_id]["searching"] = False
        if data == "404" or data is None:
            print(f"[ПОШУК] Таймаут або помилка мережі при пошуку суперника")
            await event.edit(
                "⏱️ **Istinu закінчився або втрачено з'єднання.**\n"
                "Спробуйте пошук заново.",
                buttons=play_menu
            )
        else:
            print(f"[ПОШУК] Несподіваний ответ сервера: {data}")
            await event.edit(
                "⚠️ **Помилка пошуку суперника.**\n"
                "Спробуйте спочатку.",
                buttons=play_menu
            )

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
        await event.answer("❌ Ошибка профілю. Не вдалося отримати UUID.", alert=True)
        # Даже если профиль на сервере не нашелся, мы уже разбажили стейт в памяти бота (шаг 1),
        # поэтому всё равно возвращаем его в меню игры:
        await event.edit("⚙️ Локальний стейт скинутий, але сервер не відповів.", buttons=play_menu)
        return
        
    user_uuid = me["searched"][0].get("id")
    
    # 3. Пинаем сервер через готовую функцию (снимаем с поиска / закрываем сессию на бэке)
    try:
        await asyncio.to_thread(stop_search_opponent, token, user_uuid)
    except Exception as e:
        print(f"[Force Stop API Error]: {e}")
        
    # 4. Обновляем интерфейс юзеру
    await event.answer("⚙️ Сесія примусово скинута!", alert=True)
    await event.edit("❌ Стару сесію закрито. Тепер можна шукати знову.", buttons=play_menu)

async def cancel_search(event: events.CallbackQuery.Event):
    user_id = event.sender_id
    token = get_token()
    user_state[user_id] = {"searching": False}
    me = get_user(token, user_id)
    if me.get("searched"):
        user_uuid = me["searched"][0].get("id")
        await asyncio.to_thread(stop_search_opponent, token, user_uuid)
    await event.edit("Пошук відмінено.", buttons=play_menu)

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
    my_color_text = "Білі ⚪" if state["my_color"] == "white" else "Чорні ⚫"
    
    # ВЫЧИСЛЯЕМ ЧЕЙ СЕЙЧАС ХОД ИЗ FEN
    current_turn_text = "Визначається..."
    try:
        parts = fen.split()
        if len(parts) > 1:
            active_color = parts[1]  # 'w' або 'b'
            if active_color == 'w':
                current_turn_text = "Білих ⚪"
            elif active_color == 'b':
                current_turn_text = "Чорних ⚫"
    except Exception:
        pass

    # Генерируем кнопки шахматных клеток
    chess_buttons = generate_chess_keyboard(fen, selected_cell=selected)
    
    # Проверяем, ожидаем ли выбора промоции
    waiting_for_promotion = state.get("waiting_for_promotion", False)
    
    if waiting_for_promotion:
        # Если ожидаем выбора фигуры - показываем кнопки для промоции
        chess_buttons.append([
            Button.inline("♕ Ферзь", data="promotion_q"),
            Button.inline("♖ Ладья", data="promotion_r")
        ])
        chess_buttons.append([
            Button.inline("♗ Слон", data="promotion_b"),
            Button.inline("♘ Кінь", data="promotion_n")
        ])
    else:
        # Иначе показываем кнопку сдаться
        chess_buttons.append([Button.inline("🏳️ Здатися", data="game_surrender")])

    # Формируем итоговое сообщение для игрока
    if waiting_for_promotion:
        message_content = (
            f"⚔️ **Гра проти:** @{opponent_name} (⭐ {opponent_rating})\n"
            f"🏳️ **Ваш колір:** {my_color_text}\n"
            f"⏳ **Зараз хід:** {current_turn_text}\n\n"
            f"👑 **ПІШАК ДІЙШОВ ДО КІНЦЯ!**\n"
            f"Виберіть, на яку фігуру його перетворити:"
        )
    else:
        message_content = (
            f"⚔️ **Гра проти:** @{opponent_name} (⭐ {opponent_rating})\n"
            f"🏳️ **Ваш колір:** {my_color_text}\n"
            f"⏳ **Зараз хід:** {current_turn_text}\n\n"
            f"ℹ️ *Натискайте на кнопки-клітинки, щоб зробити хід.*"
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
    Синхронно завершает игру для обоих участников с красивым выводом причины.
    """
    user_id = event.sender_id
    state = user_state.get(user_id)
    
    if not state or not state.get("game_id"):
        await event.answer("⚠️ Ви не знаходитесь в активній грі.", alert=True)
        return
        
    fen = state["current_fen"]
    my_color = state["my_color"]
    game_id = state["game_id"]
    opponent_tg_id = state.get("opponent_tg_id")  # TG ID оппонента из стейта
    
    if not is_my_turn(fen, my_color):
        await event.answer("⏳ Зараз хід вашого суперника! Чекайте.", alert=True)
        return
        
    cell = event.data.decode('utf-8').split('_')[1]
    selected = state["selected_piece"]
    
    if not selected:
        user_state[user_id]["selected_piece"] = cell
        await send_game_board(event, user_id)
        await event.answer(f"Вибрана клітинка {cell}")
        return
    else:
        if selected == cell:
            user_state[user_id]["selected_piece"] = None
            await send_game_board(event, user_id)
            return
            
        move_str = f"{selected}{cell}"
        token = get_token()
        
        # Проверяем, это ли ход с промоцией
        if is_promotion_move(selected, cell, my_color):
            # Сохраняем информацию о ходе и просим выбрать фигуру
            user_state[user_id]["waiting_for_promotion"] = True
            user_state[user_id]["pending_promotion_move"] = move_str
            await send_game_board(event, user_id)
            await event.answer("♕ Виберіть фігуру для перетворення пішака!")
            return
        
        result = await asyncio.to_thread(make_chess_move, token, game_id, move_str)
        
        # DEBUG: выводим JSON ответа для анализа промоции
        print(f"\n[ХОД ИГРОКА] move_str={move_str}")
        print(f"[API RESPONSE] {json.dumps(result, indent=2, ensure_ascii=False)}\n")
        
        # --- 1. ПЕРЕХВАТЫВАЕМ КОНЕЦ ИГРЫ, ЕСЛИ ОНА УЖЕ БЫЛА ЗАВЕРШЕНА РАНЕЕ ---
        if isinstance(result, dict) and ("detail" in result or result.get("status") == "error"):
            msg = result.get("detail", "")
            
            if any(token in str(msg).lower() for token in ["game already finished", "already finished", "finished"]):
                parsed = await asyncio.to_thread(get_game_board, token, game_id)
                state = user_state.get(user_id)
                is_ai_game = state.get("is_ai", False) if state else False
                final_state = parse_game_finish_data(parsed, my_color, is_ai=is_ai_game)
                if final_state:
                    await notify_end_game(event, user_id, opponent_tg_id, final_state["text_me"], final_state["buttons_me"], final_state["text_opp"], final_state["buttons_opp"])
                    return

                await event.edit("🏁 **Гру завершено.**\n⚠️ Гра вже завершена. Оновіть екран.", buttons=[[Button.inline("◀️ Назад в меню", data="play_back")]])
                return
                
            # Обычный нелегальный ход
            if isinstance(msg, list) and len(msg) > 0:
                msg = msg[0].get("msg", "Ошибка валидации параметров")
            elif not msg:
                msg = "Нелегальний хід за правилами шахмат!"
                
            await event.answer(f"⚠️ {msg}", alert=True)
            user_state[user_id]["selected_piece"] = None
            await send_game_board(event, user_id)
            return
            
        if not result:
            await event.answer("⚠️ Помилка зв'язку з сервером при відправці ходу.", alert=True)
            user_state[user_id]["selected_piece"] = None
            await send_game_board(event, user_id)
            return
            
        # --- 2. ОБРАБОТКА УСПЕШНОГО ФИНАЛЬНОГО ХОДА ---
        state = user_state.get(user_id)
        is_ai_game = state.get("is_ai", False) if state else False
        parsed_finish = parse_game_finish_data(result, my_color, is_ai=is_ai_game)
        if parsed_finish:
            await notify_end_game(event, user_id, opponent_tg_id, parsed_finish["text_me"], parsed_finish["buttons_me"], parsed_finish["text_opp"], parsed_finish["buttons_opp"])
            return

        game_info = result.get("game", result) if isinstance(result, dict) else result
        board_info = game_info.get("board", {}) if isinstance(game_info, dict) else {}
        new_fen = board_info.get("fen")

        if new_fen:
            user_state[user_id]["current_fen"] = new_fen
            user_state[user_id]["selected_piece"] = None
            await send_game_board(event, user_id)

async def handle_promotion_choice(event: events.CallbackQuery.Event):
    """
    Обработчик выбора фигуры при превращении пешки
    """
    user_id = event.sender_id
    state = user_state.get(user_id)
    
    if not state or not state.get("waiting_for_promotion"):
        await event.answer("⚠️ Промоция не требуется.", alert=True)
        return
    
    promotion_char = event.data.decode('utf-8').split('_')[1]  # q, r, b или n
    move_str = state.get("pending_promotion_move")
    game_id = state.get("game_id")
    my_color = state.get("my_color")
    opponent_tg_id = state.get("opponent_tg_id")
    
    # DEBUG логирование выбора промоции
    promotion_map = {'q': 'Ферзь ♕', 'r': 'Ладья ♖', 'b': 'Слон ♗', 'n': 'Конь ♘'}
    print(f"[ПРОМОЦІЯ] Гравець вибрав: {promotion_map.get(promotion_char, 'НЕВІДОМО')} (код: '{promotion_char}')")
    
    if not move_str or not game_id:
        await event.answer("⚠️ Помилка: дані про хід втрачені.", alert=True)
        return
    
    token = get_token()
    
    # Отправляем ход с указанием фигуры для превращения
    result = await asyncio.to_thread(make_chess_move, token, game_id, move_str, promotion_char)
    
    # Очищаем флаг промоции
    user_state[user_id]["waiting_for_promotion"] = False
    user_state[user_id]["pending_promotion_move"] = None
    
    # DEBUG логирование ответа сервера с промоцией
    print(f"[ПРОМОЦИЯ] Ответ сервера:")
    print(f"{json.dumps(result, indent=2, ensure_ascii=False)}")
    
    # Проверяем что произошло с пешкой/фигурой
    if isinstance(result, dict):
        game_info = result.get("game", result)
        if isinstance(game_info, dict):
            board_info = game_info.get("board", {})
            board_json = board_info.get("json", {})
            if isinstance(board_json, dict):
                pieces = board_json.get("board", {})
                print(f"[ПРОМОЦИЯ] Фигуры на доске после хода: {pieces}")
    
    # --- ОБРАБОТКА ОТВЕТА СЕРВЕРА ---
    if isinstance(result, dict) and ("detail" in result or result.get("status") == "error"):
        msg = result.get("detail", "")
        if isinstance(msg, list) and len(msg) > 0:
            msg = msg[0].get("msg", "Помилка валідації параметрів")
        elif not msg:
            msg = "Нелегальний хід за правилами шахмат!"
        
        await event.answer(f"⚠️ {msg}", alert=True)
        await send_game_board(event, user_id)
        return
    
    if not result:
        await event.answer("⚠️ Помилка зв'язку з сервером при відправці ходу.", alert=True)
        await send_game_board(event, user_id)
        return
    
    # Проверяем, не закончилась ли игра
    state = user_state.get(user_id)
    is_ai_game = state.get("is_ai", False) if state else False
    parsed_finish = parse_game_finish_data(result, my_color, is_ai=is_ai_game)
    if parsed_finish:
        await notify_end_game(event, user_id, opponent_tg_id, parsed_finish["text_me"], parsed_finish["buttons_me"], parsed_finish["text_opp"], parsed_finish["buttons_opp"])
        return
    
    # Обновляем доску
    game_info = result.get("game", result) if isinstance(result, dict) else result
    board_info = game_info.get("board", {}) if isinstance(game_info, dict) else {}
    new_fen = board_info.get("fen")
    
    if new_fen:
        user_state[user_id]["current_fen"] = new_fen
        user_state[user_id]["selected_piece"] = None
        await send_game_board(event, user_id)
    
    await event.answer("✅ Пішак перетворено!")


async def handle_surrender_click(event: events.CallbackQuery.Event):
    """
    Обработчик кнопки сдаться. Получает UUID игрока, передает его в API,
    после чего выбрасывает в главное меню обоих оппонентов.
    """
    user_id = event.sender_id
    state = user_state.get(user_id)
    
    if not state or not state.get("game_id"):
        await event.answer("⚠️ Активна гра не знайдена.", alert=True)
        return
        
    token = get_token()
    
    # 1. Получаем профиль юзера, чтобы вытащить его UUID (бэк требует UUID игрока для сдачи)
    me = get_user(token, user_id)
    if not me or not isinstance(me, dict) or not me.get("searched"):
        await event.answer("❌ Помилка профілю. Не вдалося отримати UUID для відправки на сервер.", alert=True)
        return
        
    user_uuid = me["searched"][0].get("id")
    
    # 2. Шлем запрос на бэкенд и передаем именно USER_UUID, чтобы закрыть сессию в БД
    await asyncio.to_thread(surrender_game, token, user_uuid)
    
    opponent_tg_id = state.get("opponent_tg_id")
    game_id = state.get("game_id")
    
    # 3. Выбрасываем текущего (кто нажал кнопку) игрока в главное меню
    user_state[user_id] = None
    await event.edit("🏳️ Ви здалися! Гру завершено.", buttons=main_menu)
    
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
                        "🎉 Супернік здався! Ви перемогли! Гру завершено.", 
                        buttons=main_menu
                    )
                else:
                    # Если ID сообщения доски соперника не найден, просто шлем ему новое сообщение
                    await event.client.send_message(
                        opponent_tg_id, 
                        "🎉 Суперник здався! Ви перемогли! Гру завершено.", 
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
        await event.answer("❌ Помилка профілю (Сервер недоступний)", alert=True)
        return
        
    user_uuid = me["searched"][0].get("id")
    my_color = "white" 
    
    await event.edit("🤖 Скидаємо стару гру й підключаємо ШІ...")
    
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
        print(f"[КРИТИЧНА ПОМИЛКА API] start_ai_game впав: {e}")
        await event.edit(f"❌ Сервер не відповідає на запит ШІ.\nПомилка: {e}", buttons=main_menu)
        return

    # Проверяем ответ сервера
    if not res:
        await event.edit("❌ Сервер повернув пусту відповідь (None). Перевір, запущений ли сервер", buttons=main_menu)
        return
        
    if res.status_code != 200:
        await event.edit(f"❌ Не вдалося почати гру. Сервер повернув помилку. (Код: {res.status_code})", buttons=main_menu)
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
            "opponent_name": "ШІ",            
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
        print(f"[Помилка парсингу відповіді ШІ]: {e}")
        await event.edit("❌ Помилка при ініціалізації шахової дошки.", buttons=main_menu)


def parse_analysis_report(analysis_list, player_color):
    """
    Парсит JSON-массив отчета.
    Генерирует полный список ходов ТОЛЬКО для конкретного игрока без упоминания движка.
    """
    if not isinstance(analysis_list, list):
        return [str(analysis_list)]
        
    total_moves = len(analysis_list)
    blunders = 0
    mistakes = 0
    inaccuracies = 0
    good_moves = 0
    
    player_moves_details = []
    
    # Определяем, какие индексы полуходов нам нужны
    # Если играл за белых (white) — четные индексы (0, 2, 4...)
    # Если за черных (black) — нечетные индексы (1, 3, 5...)
    target_remainder = 0 if player_color == "white" else 1

    for index, move in enumerate(analysis_list):
        # Пропускаем ходы соперника
        if index % 2 != target_remainder:
            continue
            
        annotation = move.get("annotation", "Normal")
        
        # Номер хода для шахматиста
        display_move_num = (index // 2) + 1
        color_tag = "⚪️" if player_color == "white" else "⚫️"
        
        # Форматируем лучший ход из "f6e4" в "f6-e4"
        raw_best_move = move.get("bestMove", "")
        if len(raw_best_move) == 4:
            formatted_best = f"{raw_best_move[:2]}-{raw_best_move[2:]}"
        else:
            formatted_best = raw_best_move

        # Считаем только твои категории ходов
        if annotation == "Blunder":
            blunders += 1
            status_text = f"❌ {color_tag} Хід {display_move_num}: Груба помилка! Краще було: `{formatted_best}`"
        elif annotation == "Mistake":
            mistakes += 1
            status_text = f"🔶 {color_tag} Хід {display_move_num}: Помилка! Краще було: `{formatted_best}`"
        elif annotation == "Inaccuracy":
            inaccuracies += 1
            status_text = f"🟡 {color_tag} Хід {display_move_num}: Неточність. Краще було: `{formatted_best}`"
        else:
            good_moves += 1
            status_text = f"🟢 {color_tag} Хід {display_move_num}: Чудовий хід"
            
        player_moves_details.append(status_text)

    # Собираем текстовый каркас отчета
    report_lines = []
    report_lines.append(f"📊 **Фінальний звіт (Аналіз твоїх ходів за {'Білих ⚪️' if player_color == 'white' else 'Чорних ⚫️'}):**\n")
    report_lines.append(f"⏱ Всього твоїх ходів проаналізовано: **{len(player_moves_details)}**")
    
    report_lines.append("\n📈 **Твоя статистика:**")
    report_lines.append(f"🟢 Чудові ходи: **{good_moves}**")
    report_lines.append(f"🟡 Неточності: **{inaccuracies}**")
    report_lines.append(f"🔶 Помилки: **{mistakes}**")
    report_lines.append(f"❌ Грубі помилки: **{blunders}**\n")
    
    report_lines.append("📝 **Список твоїх ходів у партії:**")
    report_lines.extend(player_moves_details)
        
    return report_lines


def fen_to_board_map(fen: str):
    board = {}
    if not isinstance(fen, str):
        return board
    parts = fen.split()
    if not parts:
        return board
    ranks = parts[0].split('/')
    files = 'abcdefgh'
    for rank_index, rank_data in enumerate(ranks):
        file_index = 0
        rank = 8 - rank_index
        for ch in rank_data:
            if ch.isdigit():
                file_index += int(ch)
            else:
                if file_index < 8:
                    square = f"{files[file_index]}{rank}"
                    board[square] = ch
                file_index += 1
    return board


def compute_move_from_fens(prev_fen: str, next_fen: str):
    if not prev_fen or not next_fen:
        return None
    prev_map = fen_to_board_map(prev_fen)
    next_map = fen_to_board_map(next_fen)

    removed = [sq for sq in prev_map if prev_map.get(sq) != next_map.get(sq)]
    added = [sq for sq in next_map if prev_map.get(sq) != next_map.get(sq)]

    if len(removed) == 1 and len(added) == 1:
        return f"{removed[0]}{added[0]}"

    # Castling detection
    for king_start, king_end in (("e1", "g1"), ("e1", "c1"), ("e8", "g8"), ("e8", "c8")):
        if prev_map.get(king_start) in ("K", "k") and next_map.get(king_end) == prev_map.get(king_start):
            return f"{king_start}{king_end}"

    # If more than one square changed, fallback with first removed/added
    if removed and added:
        return f"{removed[0]}{added[0]}"

    return None


def format_analysis_move(move_str: str):
    if not move_str:
        return "(...)"
    if len(move_str) == 4:
        return f"{move_str[:2]}-{move_str[2:]}"
    return move_str


async def build_analysis_view(event_or_client, user_id, analysis_state):
    results = analysis_state.get("results", [])
    current_index = analysis_state.get("current_index", 0)
    player_color = analysis_state.get("player_color", "white")

    if current_index < 0:
        current_index = 0
    if current_index >= len(results):
        current_index = len(results) - 1

    if not results:
        message_content = "📊 Аналіз недоступний."
        client = event_or_client.client if hasattr(event_or_client, "client") else event_or_client
        try:
            if hasattr(event_or_client, "edit"):
                await event_or_client.edit(message_content, buttons=[[Button.inline("◀️ Меню", data="play_back")]])
            else:
                await client.send_message(user_id, message_content, buttons=[[Button.inline("◀️ Меню", data="play_back")]])
        except MessageNotModifiedError:
            pass
        return

    result = results[current_index]
    fen = result.get("fen", "")
    annotation = result.get("annotation", "Normal")
    best_move = result.get("bestMove", "?")
    evaluation = result.get("evaluation")

    prev_fen = results[current_index - 1].get("fen") if current_index > 0 else None
    raw_move = None
    if prev_fen:
        raw_move = compute_move_from_fens(prev_fen, fen)
    elif result.get("move"):
        raw_move = result.get("move")
    elif result.get("playedMove"):
        raw_move = result.get("playedMove")
    elif result.get("from") and result.get("to"):
        raw_move = f"{result.get('from')}{result.get('to')}"

    move_text = format_analysis_move(raw_move)
    color = "Білі" if current_index % 2 == 0 else "Чорні"
    move_number = (current_index // 2) + 1
    move_descr = f"Ход {move_number} {color}"

    evaluation_text = f"{evaluation}" if evaluation is not None else "—"
    annotation_emoji = {
        "Normal": "🟢 Чудовий хід",
        "Great": "🟢 Відмінний хід!",
        "Good": "🟢 Добрий хід",
        "Inaccuracy": "🟡 Неточність",
        "Mistake": "🔶 Помилка",
        "Blunder": "❌ Груба помилка"
    }.get(annotation, annotation)

    board_buttons = generate_chess_keyboard(fen)
    nav_buttons = []
    has_prev = current_index > 0
    has_next = current_index < len(results) - 1
    if has_prev:
        nav_buttons.append(Button.inline("◀️ Назад", data=f"analysis_prev_{user_id}"))
    if has_next:
        nav_buttons.append(Button.inline("Вперед ▶️", data=f"analysis_next_{user_id}"))
    if nav_buttons:
        board_buttons.append(nav_buttons)

    board_buttons.append([Button.inline("◀️ Меню", data="play_back")])

    footer_note = ""
    if not has_next:
        footer_note = "\n\n✅ Ви досягли кінця аналізу."
    message_content = (
        f"📊 **Аналіз партії**\n"
        f"{move_descr}\n"
        f"♟️ Зігранний хід: **{move_text}**\n"
        f"✅ Кращий хід: **{format_analysis_move(best_move)}**\n"
        f"🔍 Оцінка: **{annotation_emoji}**\n"
        f"📈 Оцінка суммарна: **{evaluation_text}**\n"
        f"📌 Позиція {current_index + 1}/{len(results)}{footer_note}"
    )

    client = event_or_client.client if hasattr(event_or_client, "client") else event_or_client
    try:
        if hasattr(event_or_client, "edit"):
            await event_or_client.edit(message_content, buttons=board_buttons)
        else:
            await client.send_message(user_id, message_content, buttons=board_buttons)
    except MessageNotModifiedError:
        pass
    except Exception:
        await client.send_message(user_id, message_content, buttons=board_buttons)


async def send_analysis_summary(client, user_id, analysis_state):
    results = analysis_state.get("results", [])
    player_color = analysis_state.get("player_color", "white")
    report_lines = parse_analysis_report(results, player_color)

    chat_id = user_id
    message_chunks = []
    current_chunk = ""
    for line in report_lines:
        if len(current_chunk) + len(line) + 1 > 3500:
            message_chunks.append(current_chunk)
            current_chunk = line
        else:
            current_chunk = f"{current_chunk}\n{line}" if current_chunk else line
    if current_chunk:
        message_chunks.append(current_chunk)

    for chunk in message_chunks:
        await client.send_message(chat_id, chunk)


async def handle_analysis_navigation(event: events.CallbackQuery.Event):
    data = event.data.decode("utf-8") if isinstance(event.data, bytes) else str(event.data)
    match = re.match(r"^analysis_(prev|next)_(\d+)$", data)
    if not match:
        await event.answer("Неправильна команда аналізу.", alert=True)
        return

    action, owner_id = match.group(1), int(match.group(2))
    if event.sender_id != owner_id:
        await event.answer("Цей аналіз доступний тільки його автору.", alert=True)
        return

    state = user_state.get(owner_id, {}) or {}
    analysis_state = state.get("analysis_state")
    if not analysis_state:
        await event.answer("Аналіз не знайден. Запустіть його знову.", alert=True)
        return

    results = analysis_state.get("results", [])
    if not results:
        await event.answer("Немає доступного аналізу для навігації.", alert=True)
        return

    current_index = analysis_state.get("current_index", 0)
    if action == "prev":
        if current_index == 0:
            await event.answer("Це перший хід.", alert=True)
            return
        analysis_state["current_index"] = current_index - 1
    elif action == "next":
        if current_index >= len(results) - 1:
            await event.answer("Це останній хід.", alert=True)
            return
        analysis_state["current_index"] = current_index + 1

    await build_analysis_view(event, owner_id, analysis_state)


async def trigger_analysis_handler(event: events.CallbackQuery.Event):
    """
    Хэндлер кнопки 'Анализ партії'. Запускает анализ и отправляет результат.
    Цвет игрока железно берется из data кнопки.
    """
    # Разбиваем data кнопки: "start_analysis", "{game_id}", "{color}"
    params = event.pattern_match.group(1).decode('utf-8').split('_')
    
    game_id = params[0]
    
    # Если цвет передан в кнопке, берем его, иначе страхуемся белыми
    if len(params) > 1:
        player_color = params[1]
    else:
        player_color = "white"
        
    user_id = event.sender_id
    token = get_token()
    
    await event.edit("⏳ **Ініціалізація аналізу...**\nВідправка запиту до шахматного двигуна.")
    
    start_res = await asyncio.to_thread(start_game_analysis, token, game_id, depth=3)
    
    if isinstance(start_res, dict) and "detail" in start_res:
        err_msg = start_res.get("detail", "Помилка параметрів")
        await event.edit(f"❌ **Не вдалося запустити аналіз.**\n{err_msg}", buttons=[[play_back]])
        return
        
    job_id = start_res  
    
    dots = ["⏳", "⏳.", "⏳..", "⏳..."]
    counter = 0
    
    while True:
        status_res = await asyncio.to_thread(get_analysis_status, token, job_id)
        
        if isinstance(status_res, dict) and "detail" in status_res:
            err_msg = status_res.get("detail", "Задача не знайдена")
            await event.edit(f"❌ **Помилка статуса аналізу:**\n{err_msg}", buttons=[[play_back]])
            return
            
        status_str = "PENDING"
        results_data = None
        
        if isinstance(status_res, dict):
            status_str = str(status_res.get("status", "PENDING")).upper()
            results_data = status_res.get("results")
        else:
            status_str = str(status_res).upper()

        if status_str in ["PENDING", "PROCESSING", "RUNNING"]:
            animation = dots[counter % len(dots)]
            counter += 1
            try:
                await event.edit(f"{animation} **Шаховий двигун аналізує ваші ходи...**\nБудь ласка, зачекайте.")
            except MessageNotModifiedError:
                pass  
            await asyncio.sleep(2)
            continue
            
        elif status_str in ["SUCCESS", "COMPLETED"]:
            if isinstance(results_data, list):
                # Сохраняем состояние анализа для навигации по результатам
                state = user_state.get(user_id) or {}
                state["analysis_state"] = {
                    "results": results_data,
                    "current_index": 0,
                    "player_color": player_color,
                }
                user_state[user_id] = state

                await build_analysis_view(event, user_id, state["analysis_state"])
                return
            
            report_lines = [f"📊 **Аналіз партії завершено!**\n\n{results_data if results_data else status_res}"]
            await event.edit("\n".join(report_lines), buttons=[[play_back]])
            break
            
        else:
            await event.edit(f"❌ **Аналіз завершився з помилкою бекенда.**\nСтатус: {status_str}", buttons=[[play_back]])
            break