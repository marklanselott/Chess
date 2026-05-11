from telethon import Button
reg = Button.inline("Регистрация", data="userreg")
auth = Button.inline("Авторизация", data="userauth")
play = Button.inline("Играть♟", data="play")
profile = Button.inline("Профиль🧍", data="profile")
offline = Button.inline("Играть с ботом🤖", data="offline")
online = Button.inline("Играть с игроками🎮", data="online")
friend = Button.inline("Играть с другом👥", data="friend")
friend_main = Button.inline("Друзья🗣", data="friend_main")
friend_add = Button.inline("Добавить друга👀", data="friend_add")
friend_back = Button.inline("Назад◀️", data="friend_back")
friend_requests = Button.inline("Заявки📲", data="friend_requests")
profile_back = Button.inline("Назад◀️", data="profile_back")
remake_name = Button.inline("Поменять имя💬", data="remake_name")
remake_unique = Button.inline("Поменять ник✏️", data="remake_unique")
remake_password = Button.inline("Поменять пароль🔒", data="remake_password")
confirm_delete = Button.inline("Удаление аккаунта🚨", data="confirm_delete")
play_back = Button.inline("Назад◀️", data="play_back")
remake_back = Button.inline("Назад◀️", data="remake_back")
white = Button.inline("⚪", data="white")
black = Button.inline("⚫", data="black")
easy = Button.inline("Лёгкий", data="easy")
medium = Button.inline("Средний", data="medium")
hard = Button.inline("Сложный", data="hard")
cancel_search_btn = Button.inline("❌ Отменить поиск", data="cancel_search")


authreg = [auth, reg]

main_menu = [
[play], [profile],
[friend_main]
]

friend_menu = [
[friend_add], [friend_requests],
[friend_back]
]

profile_menu = [
[remake_name, remake_unique],
[remake_password],
[confirm_delete],
[profile_back]
]

play_menu = [
[offline, online],
[friend],
[play_back]
]

color = [white, black]

level = [
    [easy],
    [medium],
    [hard],
    [play_back]
]