from telethon import Button
reg = Button.inline('Реєстрація', data='userreg')
auth = Button.inline('Авторизація', data='userauth')
play = Button.inline('Грати♟', data='play')
profile = Button.inline('Профіль🧍', data='profile')
offline = Button.inline('Грати з ботом🤖', data='offline')
online = Button.inline('Грати з гравцями🎮', data='online')
friend_main = Button.inline('Друзі🗣', data='friend_main')
friend_add = Button.inline('Додати друга👀', data='friend_add')
friend_back = Button.inline('Назад◀️', data='friend_back')
friend_requests = Button.inline('Заявки📲', data='friend_requests')
profile_back = Button.inline('Назад◀️', data='profile_back')
remake_name = Button.inline("Змінити ім'я💬", data='remake_name')
remake_unique = Button.inline('Змінити нік✏️', data='remake_unique')
remake_password = Button.inline('Змінити пароль🔒', data='remake_password')
confirm_delete = Button.inline('Видалення акаунту🚨', data='confirm_delete')
play_back = Button.inline('Назад◀️', data='play_back')
remake_back = Button.inline('Назад◀️', data='remake_back')
white = Button.inline('⚪', data='white')
black = Button.inline('⚫', data='black')
easy = Button.inline('Легкий', data='easy')
medium = Button.inline('Середній', data='medium')
hard = Button.inline('Складний', data='hard')
cancel_search_btn = Button.inline('❌ Скасувати пошук', data='cancel_search')
authreg = [auth, reg]
main_menu = [[play], [profile], [friend_main]]
friend_menu = [[friend_add], [friend_requests], [friend_back]]
profile_menu = [[remake_name, remake_unique], [remake_password], [confirm_delete], [profile_back]]
play_menu = [[offline, online], [play_back]]
color = [white, black]
level = [[easy], [medium], [hard], [play_back]]
