from telethon import TelegramClient, events, Button
from config import apiId, apiHash, botToken, base_url, maxname, minname
from menus import level, authreg, main_menu, play_menu, profile_menu, remake_back, remake_name, friend_menu, friend_back
import requests
import api

user_state = {}


bot = TelegramClient("session_file", apiId, apiHash)
bot.start(bot_token=botToken)

# Старт
@bot.on(events.NewMessage(pattern='/start'))
async def start(event:events.NewMessage.Event):
    token = api.get_token()
    result = api.get_user(token, event.chat_id)
    # print(result)

    if not result.get("searched"):
        await bot.send_message(event.chat_id, "Привет! Ты не зарегистрирован. Выбери действие:", buttons=authreg)
    else:
        # Если нашли пользователя по TG ID, сразу пускаем в меню
        user = result["searched"][0]
        await bot.send_message(event.chat_id, f"С возвращением, {user.get('first_name')}!", buttons=main_menu)

# --- Обработка нажатий на кнопки регистрации и входа ---

@bot.on(events.CallbackQuery(data="userreg"))
async def start_reg(event):
    user_state[event.sender_id] = {"step": "reg_name"}
    await event.edit("📝 Введите ваше Имя:")

@bot.on(events.CallbackQuery(data="userauth"))
async def start_auth(event):
    user_state[event.sender_id] = {"step": "auth_unique"}
    await event.edit("🔑 Введите ваш логин (unique):")

# --- Единый обработчик текстовых сообщений (FSM) ---

@bot.on(events.NewMessage)
async def handle_registration_and_auth(event):
    if event.text.startswith('/'):
        return

    state = user_state.get(event.sender_id)
    if not state:
        return

    step = state["step"]
    text = event.text.strip()

# >>> ЛОГИКА РЕГИСТРАЦИИ <<<
    
    # 1. Проверка Имени
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

    # 2. Проверка Логина (unique)
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

    # 3. Проверка Пароля
    elif step == "reg_password":
        if len(text) < 6 or len(text) > 12:
            await event.reply("❌ Пароль должен быть от 6 до 12 символов. Введите еще раз:")
            return

        data = user_state[event.sender_id]
        token = api.get_token()
        
        try:
            api.reg_user(
                token=token,
                unique=data["unique"],
                first_name=data["first_name"], 
                password=text, # здесь text — это проверенный пароль
                tg_id=event.sender_id
            )
            
            user_state[event.sender_id] = None
            await event.respond(f"✅ Регистрация завершена! Добро пожаловать, {data['first_name']}.", buttons=main_menu)
        except Exception as e:
            await event.respond("⚠️ Произошла ошибка при регистрации. Попробуйте позже.")
            print(f"Reg error: {e}")

# >>> ЛОГИКА АВТОРИЗАЦИИ (остается без изменений, так как там валидация не нужна) <<<
    elif step == "auth_unique":
        user_state[event.sender_id]["login_try"] = text
        user_state[event.sender_id]["step"] = "auth_password"
        await event.respond("🔒 Введите ваш пароль:")

    elif step == "auth_password":
        login = state["login_try"]
        password = text
        token = api.get_token()

        user_data = api.get_user_by_unique(token, login)

        if user_data and str(user_data.get("password")) == password:
            user_state[event.sender_id] = None
            await event.respond(f"✅ Вход выполнен! Привет, {user_data.get('first_name')}!", buttons=main_menu)
        else:
            await event.respond("❌ Ошибка: логин или пароль неверны. Попробуйте снова через /start")
            user_state[event.sender_id] = None
        
# >>> ИЗМЕНЕНИЕ ИМЕНИ <<<
    elif step == "wait_new_name":
        # 1. Валидация: длина и отсутствие спецсимволов/цифр
        if len(text) < 2 or len(text) > 20:
            await event.reply("❌ Имя должно быть от 2 до 20 символов!")
            return
        
        # Убираем пробелы для проверки, чтобы .isalpha() не ругался на них
        if not text.replace(" ", "").isalpha():
            await event.reply("❌ Имя должно состоять только из букв!")
            return

        token = api.get_token()
        current_user = api.get_user(token, event.sender_id)
        
        if current_user.get("searched") and len(current_user["searched"]) > 0:
            user_data = current_user["searched"][0]
            user_id = user_data.get("id") 
            
            payload = {
                "unique": user_data.get("unique"),
                "first_name": text, 
                "middle_name": user_data.get("middle_name", ""),
                "last_name": user_data.get("last_name", ""),
                "password": user_data.get("password", ""),
                "phone": user_data.get("phone", 0),
                "email": user_data.get("email", "")
            }
            
            host = base_url.rstrip('/')
            url = f"{host}/api/user/update/user_id/{user_id}"
            res = requests.post(url, params={"token": token}, json=payload)
            
            if res.status_code == 200:
                user_state[event.sender_id] = None
                await event.respond(f"✅ Имя успешно изменено на: **{text}**", buttons=main_menu)
            else:
                await event.respond(f"❌ Ошибка {res.status_code}: {res.text}")
        else:
            await event.respond("❌ Пользователь не найден.")

# >>> ИЗМЕНЕНИЕ ЛОГИНА (UNIQUE) <<<
    elif step == "wait_new_unique":
        # 1. Валидация: длина и только буквы/цифры (без пробелов и знаков)
        if len(text) < 3 or len(text) > 15:
            await event.reply("❌ Логин должен быть от 3 до 15 символов!")
            return
        
        if not text.isalnum():
            await event.reply("❌ Логин может содержать только буквы и цифры без спецсимволов!")
            return

        token = api.get_token()
        current_user = api.get_user(token, event.sender_id)
        
        if current_user.get("searched") and len(current_user["searched"]) > 0:
            user_data = current_user["searched"][0]
            user_id = user_data.get("id")
            
            payload = {
                "unique": text,
                "first_name": user_data.get("first_name", ""),
                "middle_name": user_data.get("middle_name", ""),
                "last_name": user_data.get("last_name", ""),
                "password": user_data.get("password", ""),
                "phone": user_data.get("phone", 0),
                "email": user_data.get("email", "")
            }
            
            host = base_url.rstrip('/')
            url = f"{host}/api/user/update/user_id/{user_id}"
            res = requests.post(url, params={"token": token}, json=payload)
            
            if res.status_code == 200:
                user_state[event.sender_id] = None
                await event.respond(f"✅ Логин успешно изменен на: **{text}**", buttons=main_menu)
            elif res.status_code == 400:
                await event.respond("⚠️ Этот логин уже занят или совпадает с текущим.")
            else:
                await event.respond(f"❌ Ошибка {res.status_code}")
        else:
            await event.respond("❌ Пользователь не найден.")
            
# >>> ИЗМЕНЕНИЕ ПАРОЛЯ <<<
    elif step == "wait_new_password":
        # 1. Валидация на стороне бота
        if len(text) < 6 or len(text) > 12:
            await event.reply("❌ **Ошибка:** Пароль должен быть от 6 до 12 символов!")
            return

        token = api.get_token()
        current_user = api.get_user(token, event.sender_id)
        
        if current_user.get("searched") and len(current_user["searched"]) > 0:
            user_data = current_user["searched"][0]
            user_id = user_data.get("id")
            
            payload = {
                "unique": user_data.get("unique"),
                "first_name": user_data.get("first_name"),
                "middle_name": user_data.get("middle_name", ""),
                "last_name": user_data.get("last_name", ""),
                "password": text, # Новый пароль
                "phone": user_data.get("phone", 0),
                "email": user_data.get("email", "")
            }
            
            host = base_url.rstrip('/')
            url = f"{host}/api/user/update/user_id/{user_id}"
            
            try:
                res = requests.post(url, params={"token": token}, json=payload)
                
                # --- БЛОК ОБРАБОТКИ ОТВЕТОВ СЕРВЕРА ---
                if res.status_code == 200:
                    # Успех
                    user_state[event.sender_id] = None
                    await event.respond("✅ **Успешно!** Ваш пароль был обновлен.", buttons=main_menu)
                
                elif res.status_code == 400:
                    # Проверяем, что именно не понравилось серверу
                    error_data = res.json()
                    detail = error_data.get("detail", "")
                    
                    if "No changes detected" in detail:
                        await event.respond("⚠️ **Вы ввели тот же самый пароль.**\nПридумайте новую комбинацию или нажмите «Назад».")
                    else:
                        await event.respond(f"❌ **Ошибка запроса:** {detail}")
                
                elif res.status_code == 422:
                    await event.respond("❌ **Ошибка валидации:** Сервер не принял формат данных. Проверьте пароль.")
                
                elif res.status_code == 404:
                    await event.respond("❌ **Ошибка:** Пользователь не найден на сервере.")
                
                else:
                    await event.respond(f"❓ **Неизвестная ошибка ({res.status_code}):**\n{res.text}")

            except Exception as e:
                await event.respond(f"⚠️ **Ошибка соединения:** Не удалось связаться с сервером.\n`{str(e)}`")
        else:
            await event.respond("❌ **Ошибка:** Не удалось получить данные вашего профиля.")


# >>> ШАГ 1: ПОЛУЧАЕМ ЛОГИН ДЛЯ УДАЛЕНИЯ <<<
    elif step == "wait_delete_login":
        # Сохраняем введенный логин во временное состояние и просим пароль
        user_state[event.sender_id] = {
            "step": "wait_delete_password_final", 
            "delete_unique": text.strip()
        }
        await event.respond("🔐 Теперь введите ваш **Пароль** для окончательного удаления:")

    # >>> ШАГ 2: ПОЛУЧАЕМ ПАРОЛЬ И УДАЛЯЕМ <<<
    elif step == "wait_delete_password_final":
        delete_login = user_state[event.sender_id].get("delete_unique")
        delete_password = text.strip()
        
        token = api.get_token()
        host = base_url.rstrip('/')
        url = f"{host}/api/user/remove"
        
        # Данные строго по твоей документации (Request body)
        payload = {
            "unique": delete_login,
            "password": delete_password
        }
        
        try:
            # Отправляем DELETE запрос
            res = requests.post(url, params={"token": token}, json=payload)
            
            if res.status_code == 200:
                user_state[event.sender_id] = None # Сброс состояния
                await event.respond("🗑 **Ваш аккаунт и все данные успешно удалены.**\nДо новых встреч!", buttons=authreg)
            
            elif res.status_code == 404:
                # Согласно доке, 404 возвращается, если логин или пароль неверны
                user_state[event.sender_id] = None
                await event.respond("❌ **Ошибка:** Неверный логин или пароль. Удаление отменено.", buttons=main_menu)
            
            else:
                await event.respond(f"❌ **Ошибка сервера ({res.status_code}):** {res.text}")
                
        except Exception as e:
            await event.respond(f"⚠️ **Ошибка соединения:** {e}")

# поиск друзей
    elif step == "wait_friend_nickname":
        target_nickname = text.strip()
        token = api.get_token()
        
        # 1. Получаем твой профиль (нужен твой ID и имя для уведомления)
        me = api.get_user(token, event.sender_id)
        
        # 2. Ищем того, кого хотим добавить (по уникальному нику)
        search_url = f"{base_url.rstrip('/')}/api/user/search/"
        search_res = requests.post(search_url, params={"token": token}, json={"unique": target_nickname})
        
        if search_res.status_code == 200:
            search_data = search_res.json()
            
            # Проверяем, что и ты, и цель найдены в базе
            if search_data.get("searched") and me.get("searched"):
                my_info = me["searched"][0]
                target_info = search_data["searched"][0]
                
                my_id = my_info.get("id")          # Твой UUID
                target_id = target_info.get("id")  # UUID друга
                friend_tg_id = target_info.get("tg_id") # Telegram ID друга для уведомления

                # Запрет на добавление самого себя
                # if my_id == target_id:
                #     user_state[event.sender_id] = None
                #     await event.respond("❌ Нельзя добавить самого себя!", buttons=main_menu)
                #     return

                # 3. Отправка запроса (НОВЫЙ URL: send_request)
                add_url = f"{base_url.rstrip('/')}/api/friends/send_request"
                payload = {"user_id": my_id, "friend_id": target_id}
                add_res = requests.post(add_url, params={"token": token}, json=payload)

                if add_res.status_code == 200:
                    # Сервер вернул ID новой заявки
                    req_id = add_res.json().get("id")
                    
                    user_state[event.sender_id] = None
                    await event.respond(f"✅ Запрос для **{target_nickname}** успешно отправлен!", buttons=main_menu)

                    # 4. Мгновенное уведомление другу (как ты и просил)
                    if friend_tg_id:
                        try:
                            msg = (
                                f"🔔 **Новая заявка в друзья!**\n\n"
                                f"Игрок **{my_info.get('first_name')}** (@{my_info.get('unique')}) хочет добавить вас.\n"
                                f"Вы можете ответить прямо здесь или в меню «Заявки»."
                            )
                            # Кнопки с ID заявки для мгновенного принятия
                            req_buttons = [
                                [
                                    Button.inline("✅ Принять", data=f"acc_{req_id}"),
                                    Button.inline("❌ Отклонить", data=f"rej_{req_id}")
                                ]
                            ]
                            await bot.send_message(friend_tg_id, msg, buttons=req_buttons)
                        except Exception as e:
                            print(f"Ошибка отправки уведомления: {e}")

                elif add_res.status_code in [400, 422]:
                    # Обработка ошибки "уже существует"
                    try:
                        reason = add_res.json().get("detail", "")
                    except:
                        reason = ""
                    
                    if "already exists" in str(reason).lower():
                        error_text = "⚠️ **Заявка уже была отправлена ранее.**\nОна ожидает подтверждения в разделе «Заявки» у вашего друга."
                    else:
                        error_text = f"❌ Ошибка сервера: {reason if reason else add_res.status_code}"
                    
                    user_state[event.sender_id] = None
                    await event.respond(error_text, buttons=main_menu)
                
                else:
                    user_state[event.sender_id] = None
                    await event.respond(f"❌ Не удалось отправить запрос (Код: {add_res.status_code})", buttons=main_menu)

            else:
                # Если поиск вернул пустой список
                await event.respond("❌ Пользователь с таким ником не найден. Проверьте правильность написания.", buttons=main_menu)
                user_state[event.sender_id] = None
        else:
            # Ошибка самого поиска
            await event.respond(f"⚠️ Ошибка при поиске: {search_res.status_code}", buttons=main_menu)
            user_state[event.sender_id] = None






# Кнопка играть
@bot.on(events.CallbackQuery(data="play"))
async def play(event:events.CallbackQuery.Event):
    await event.edit("Выберите режим:", buttons=play_menu)

# Кнопка назад из игр
@bot.on(events.CallbackQuery(data="play_back"))
async def playback(event:events.CallbackQuery.Event):
    await event.edit("Вернулись, выбирайте:", buttons=main_menu)

# Меню друзей и список
@bot.on(events.CallbackQuery(data="friend_main")) 
async def show_friends_list(event):
    token = api.get_token()
    current_user = api.get_user(token, event.sender_id)
    
    if current_user.get("searched"):
        user_id = current_user["searched"][0].get("id")
        host = base_url.rstrip('/')
        url = f"{host}/api/friends/get_list/user_id/{user_id}"
        
        try:
            res = requests.get(url, params={"token": token})
            
            if res.status_code == 200:
                friends = res.json()
                
                if not friends:
                    text = "👥 **Ваш список друзей пуст.**\n\nСамое время кого-нибудь добавить!"
                else:
                    text = "👥 **Ваши друзья:**\n\n"
                    for f in friends:
                        name = f.get('first_name', 'Игрок')
                        nick = f.get('unique', '???')
                        rating = f.get('rating', 0)
                        text += f"• **{name}** (@{nick}) — 🏆 {rating}\n"

                # --- НОВАЯ КНОПКА ТУТ ---
                # Создаем временную копию меню и добавляем кнопку удаления в начало
                current_buttons = [[Button.inline("🗑 Удалить кого-то", data="unfriend_list")]] + friend_menu
                
                await event.edit(text, buttons=current_buttons)
                
            elif res.status_code == 404:
                await event.edit("❌ Пользователь не найден.", buttons=friend_menu)
            else:
                await event.edit(f"❌ Ошибка API: {res.status_code}", buttons=friend_menu)
                
        except Exception as e:
            await event.edit(f"⚠️ Ошибка сети: {e}", buttons=friend_menu)
    else:
        await event.answer("❌ Сначала зарегистрируйтесь!", alert=True)

# Добавление друзей
@bot.on(events.CallbackQuery(data="friend_add"))
async def start_add_friend(event):
    user_state[event.sender_id] = {"step": "wait_friend_nickname"}
    # Здесь используем friend_back, так как это логично для отмены
    await event.edit("🔍 Введите **Ник (unique)** пользователя, которого хотите добавить:", 
                     buttons=[[friend_back]])

# заявка в друзья
@bot.on(events.CallbackQuery(data="friend_requests"))
async def handle_requests_menu(event):
    # Это та самая "первая кнопка"
    text = "🚀 **Управление заявками**\n\nВыберите раздел:"
    buttons = [
        [Button.inline("📥 Входящие (вам)", data="requests_in")],
        [Button.inline("📤 Исходящие (от вас)", data="requests_out")],
        [Button.inline("⬅️ Назад в меню", data="friend_main")]
    ]
    await event.edit(text, buttons=buttons)

# входящие заявки
@bot.on(events.CallbackQuery(data="requests_in"))
async def show_incoming(event):
    token = api.get_token()
    me = api.get_user(token, event.sender_id)
    my_uuid = me["searched"][0].get("id")
    
    url = f"{base_url.rstrip('/')}/api/friends/get_requests_for_me/user_id/{my_uuid}"
    
    try:
        res = requests.get(url, params={"token": token})
        if res.status_code == 200:
            reqs = res.json()
            if not reqs:
                await event.edit("📩 **Входящих заявок нет.**", 
                                 buttons=[[Button.inline("⬅️ Назад", data="friend_requests")]])
                return

            text = "📥 **Входящие заявки:**\n"
            buttons = []
            for r in reqs:
                r_id = r.get("id")
                
                # --- ВОТ ТУТ ИСПРАВЛЕНИЕ ---
                # Получаем данные отправителя из вложенного словаря 'user'
                user_data = r.get("user") or {}
                # Сначала пробуем уникальный ник, если его нет — имя
                name = user_data.get("unique") or user_data.get("first_name") or "Игрок"
                # ---------------------------

                text += f"\n👤 От: **@{name}**"
                buttons.append([
                    Button.inline(f"✅ Принять", data=f"acc_{r_id}"),
                    Button.inline(f"❌", data=f"rej_{r_id}")
                ])
            
            buttons.append([Button.inline("⬅️ Назад", data="friend_requests")])
            await event.edit(text, buttons=buttons)
    except Exception as e:
        print(f"Ошибка в show_incoming: {e}")
        await event.answer("⚠️ Ошибка загрузки", alert=True)

# исходящие заявки
@bot.on(events.CallbackQuery(data="requests_out"))
async def show_outgoing(event):
    token = api.get_token()
    me = api.get_user(token, event.sender_id)
    my_uuid = me["searched"][0].get("id")
    
    url = f"{base_url.rstrip('/')}/api/friends/get_requests_my/user_id/{my_uuid}"
    
    try:
        res = requests.get(url, params={"token": token})
        if res.status_code == 200:
            reqs = res.json()
            if not reqs:
                await event.edit("📤 **Вы не отправляли заявок.**", 
                                 buttons=[[Button.inline("⬅️ Назад", data="friend_requests")]])
                return

            text = "📤 **Ваши исходящие заявки:**\n"
            buttons = []
            for r in reqs:
                r_id = r.get("id")
                
                # --- ИСПРАВЛЕНИЕ ТУТ ---
                # В исходящих данных получатель лежит в ключе 'friend'
                friend_data = r.get("friend") or {}
                # Сначала пробуем уникальный ник, потом имя
                name = friend_data.get("unique") or friend_data.get("first_name") or "Игрок"
                # -----------------------

                text += f"\n👤 К: **@{name}**"
                buttons.append([Button.inline(f"🚫 Отозвать", data=f"can_{r_id}")])
            
            buttons.append([Button.inline("⬅️ Назад", data="friend_requests")])
            await event.edit(text, buttons=buttons)
    except Exception as e:
        print(f"Ошибка в show_outgoing: {e}")
        await event.answer("⚠️ Ошибка загрузки", alert=True)

@bot.on(events.CallbackQuery(data="unfriend_list"))
async def show_unfriend_menu(event):
    token = api.get_token()
    me = api.get_user(token, event.sender_id)
    user_id = me["searched"][0].get("id")
    
    url = f"{base_url.rstrip('/')}/api/friends/get_list/user_id/{user_id}"
    
    try:
        res = requests.get(url, params={"token": token})
        friends = res.json()
        
        if not friends:
            await event.edit("📭 Список пуст.", buttons=[[Button.inline("⬅️ Назад", data="friend_main")]])
            return

        buttons = []
        for f in friends:
            # Если в консоли появится ключ типа 'request_id' или 'friendship_id', 
            # заменим 'id' на него ниже.
            f_id = f.get('id') 
            nick = f.get('unique', 'Игрок')
            buttons.append([Button.inline(f"❌ Удалить {nick}", data=f"unf_id_{f_id}")])
        
        buttons.append([Button.inline("⬅️ Назад", data="friend_main")])
        await event.edit("🗑 Выберите друга для удаления:", buttons=buttons)
        
    except Exception as e:
        print(f"Ошибка в меню: {e}")
        await event.answer("⚠️ Ошибка загрузки списка", alert=True)

# список для удаления
@bot.on(events.CallbackQuery(pattern=r"unf_id_(.+)"))
async def handle_unfriend_action(event):
    target_user_id = event.pattern_match.group(1).decode('utf-8')
    token = api.get_token()
    
    me = api.get_user(token, event.sender_id)
    my_uuid = me["searched"][0].get("id")
    
    # Ссылки на твои заявки
    url_out = f"{base_url.rstrip('/')}/api/friends/get_requests_my/user_id/{my_uuid}"
    url_in = f"{base_url.rstrip('/')}/api/friends/get_requests_for_me/user_id/{my_uuid}"
    
    try:
        # 1. Проверяем ИСХОДЯЩИЕ
        res_out = requests.get(url_out, params={"token": token})
        found_req = None
        
        if res_out.status_code == 200:
            reqs_out = res_out.json()
            for r in reqs_out:
                # Проверяем ID друга в исходящей заявке
                if r.get("friend", {}).get("id") == target_user_id:
                    found_req = r
                    break
        
        # 2. Если не нашли, проверяем ВХОДЯЩИЕ
        if not found_req:
            res_in = requests.get(url_in, params={"token": token})
            if res_in.status_code == 200:
                reqs_in = res_in.json()
                for r in reqs_in:
                    # Входящая: отправитель — r['user'], ты — r['friend']
                    if r.get("user", {}).get("id") == target_user_id:
                        found_req = r
                        break

        if found_req:
            real_request_id = found_req.get("id")
            print(f"FOUND REAL ID: {real_request_id}")
            
            update_url = f"{base_url.rstrip('/')}/api/friends/update_request"
            final_res = requests.post(update_url, params={"token": token}, 
                                     json={"request_id": real_request_id, "status": False})
            
            if final_res.status_code == 200:
                await event.answer("✅ Друг удален!", alert=True)
                await show_unfriend_menu(event)
                return
            else:
                print(f"FAIL UPDATE: {final_res.text}")

        await event.answer("❌ Не удалось найти ID связи", alert=True)
        
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        await event.answer("⚠️ Ошибка поиска", alert=True)

# Назад из друзей
@bot.on(events.CallbackQuery(data="friend_back"))
async def go_back_from_friends(event):
    user_state[event.sender_id] = None # Сброс поиска, если он шел
    # Возвращаемся в главное меню (main_menu)
    await event.edit("🏠 Главное меню", buttons=main_menu)

# Профиль
@bot.on(events.CallbackQuery(data="profile"))
async def profile(event: events.CallbackQuery.Event):
    token = api.get_token()
    # Получаем данные пользователя из БД по его Telegram ID
    result = api.get_user(token, event.chat_id)
    
    if result.get("searched"):
        user = result["searched"][0]
        
        # Извлекаем данные (используем .get() на случай, если какого-то поля нет)
        first_name = user.get("first_name", "Не указано")
        unique = user.get("unique", "Не указано")
        
        # Статистика (если эти поля есть в твоем API, если нет — останутся пустыми)
        rating = user.get("rating", 0)
        games = user.get("games_count", 0)
        wins = user.get("wins", 0)
        losses = user.get("losses", 0)
        
        # Считаем Win/Loss Ratio (защита от деления на ноль)
        if losses > 0:
            wl = round(wins / losses, 2)
        else:
            wl = wins # Если поражений 0, W/L равен количеству побед

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
        await event.answer("❌ Ошибка: данные профиля не найдены.", alert=True)

# Кнопка изменения имени
@bot.on(events.CallbackQuery(data="remake_name"))
async def nameremake(event):
    user_state[event.sender_id] = {"step": "wait_new_name"}
    await event.edit("✏️ Введите новое **Имя** (2-16 символов):", buttons=remake_back)

# Кнопка изменения логина (unique)
@bot.on(events.CallbackQuery(data="remake_unique")) 
async def loginremake(event):
    user_state[event.sender_id] = {"step": "wait_new_unique"}
    await event.edit("✏️ Введите новый **Логин** (2-16 символов, только буквы и цифры):", buttons=remake_back)

# Изменение пароля
@bot.on(events.CallbackQuery(data="remake_password"))
async def passwordremake(event):
    # Сразу ставим шаг ожидания НОВОГО пароля
    user_state[event.sender_id] = {"step": "wait_new_password"}
    await event.edit("🔒 Введите **новый пароль** (от 6 до 12 символов):", buttons=remake_back)

# Подтверждение удаления
@bot.on(events.CallbackQuery(data="confirm_delete"))
async def confirmdelete(event):
    # Начинаем с запроса логина
    user_state[event.sender_id] = {"step": "wait_delete_login"}
    await event.edit(
        "⚠️ **УДАЛЕНИЕ АККАУНТА**\n\nДля подтверждения введите ваш **Логин (unique)**:", 
        buttons=remake_back
    )
            
@bot.on(events.CallbackQuery(data="remake_back"))
async def remakeback(event):
    # 1. Сбрасываем состояние, чтобы бот перестал ждать ввод текста
    user_state[event.sender_id] = None
    
    try:
        # 2. Получаем свежий токен и данные из БД
        token = api.get_token()
        # Используем event.sender_id для надежности
        result = api.get_user(token, event.sender_id)
        
        if result.get("searched") and len(result["searched"]) > 0:
            user = result["searched"][0]
            
            # 3. Извлекаем поля
            first_name = user.get("first_name", "Не указано")
            unique = user.get("unique", "Не указано")
            rating = user.get("rating", 0)
            games = user.get("games_count", 0)
            wins = user.get("wins", 0)
            losses = user.get("losses", 0)
            
            # 4. Считаем W/L
            wl = round(wins / losses, 2) if losses > 0 else wins

            # 5. Формируем текст профиля
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
            
            # 6. Редактируем сообщение ОДИН РАЗ
            await event.edit(profile_text, buttons=profile_menu)
        
        else:
            # Если юзер не найден
            await event.edit("❌ Ошибка: профиль не найден.", buttons=main_menu)

    except Exception as e:
        # Если текст сообщения не изменился или произошла ошибка в процессе (например, 400 или 429)
        # Просто гасим уведомление на кнопке (убираем "часики")
        print(f"Ошибка в remakeback: {e}")
        await event.answer()

# Ещё возврат в профиль
@bot.on(events.CallbackQuery(data="profile_back"))
async def profileback(event:events.CallbackQuery.Event):
    await event.edit("Вернулись, выбирайте:", buttons=main_menu)

# игра с ботом
@bot.on(events.CallbackQuery(data="offline"))
async def choosecolor(event:events.CallbackQuery.Event):
    await event.edit("Выберите уровень сложности", buttons=level)

# @bot.on(events.CallbackQuery(data="white"))
# async def white(event:events.CallbackQuery.Event):
#     await event.edit("В разработке...", buttons=main_menu)


# @bot.on(events.CallbackQuery(data="black"))
# async def black(event:events.CallbackQuery.Event):
#     await event.edit("В разработке...", buttons=main_menu)


bot.run_until_disconnected()

"""

User(id=1847174605, is_self=False, contact=False, mutual_contact=False, deleted=False, bot=False, bot_chat_history=False, bot_nochats=False, verified=False, restricted=False, min=False, bot_inline_geo=False, support=False, scam=False, apply_min_photo=True, fake=False, bot_attach_menu=False, premium=False, attach_menu_enabled=False, bot_can_edit=False, close_friend=False, stories_hidden=False, stories_unavailable=True, contact_require_premium=False, bot_business=False, bot_has_main_app=False, bot_forum_view=False, access_hash=-6388187944164433123, first_name='d1sk', last_name=None, username='ssdd1skxx', phone=None, photo=None, status=UserStatusRecently(by_me=False), bot_info_version=None, restriction_reason=[], bot_inline_placeholder=None, lang_code='ru', emoji_status=None, usernames=[], stories_max_id=None, color=None, profile_color=None, bot_active_users=None, bot_verification_icon=None, send_paid_messages_stars=None)"""