from telethon import events
import asyncio

from chess_handler import ChessTest
from menus import main_menu, play_menu, level
from state import user_state

current_test = ChessTest()
last_msg_event = None
waiting_for_coords = False
current_legal_moves = []
console_active = asyncio.Event()


def register_game_handlers(bot):
    bot.add_event_handler(play, events.CallbackQuery(data="play"))
    bot.add_event_handler(playback, events.CallbackQuery(data="play_back"))
    bot.add_event_handler(choosecolor, events.CallbackQuery(data="offline"))
    bot.add_event_handler(start_test, events.CallbackQuery(data="easy"))
    bot.add_event_handler(handle_click, events.CallbackQuery(pattern=r"c:(\d+):(\d+)"))
    bot.loop.create_task(console_listener())


async def play(event: events.CallbackQuery.Event):
    await event.edit("Выберите режим:", buttons=play_menu)


async def playback(event: events.CallbackQuery.Event):
    console_active.clear()
    await event.edit("Вернулись, выбирайте:", buttons=main_menu)


async def choosecolor(event: events.CallbackQuery.Event):
    await event.edit("Выберите уровень сложности", buttons=level)


async def start_test(event: events.CallbackQuery.Event):
    global last_msg_event, waiting_for_coords, current_legal_moves
    last_msg_event = event
    current_test.selected = None
    waiting_for_coords = False
    current_legal_moves = []
    console_active.set()

    await event.edit(
        f"Игра началась.\n`{current_test.fen}`\n\nВыбери фигуру (или введи новый FEN в консоль):",
        buttons=current_test.get_buttons(),
    )


async def handle_click(event):
    global last_msg_event, waiting_for_coords, current_legal_moves
    last_msg_event = event
    r, c = map(int, event.pattern_match.groups())

    if waiting_for_coords:
        if current_test.selected == (r, c):
            current_test.selected = None
            waiting_for_coords = False
            current_legal_moves = []
            await event.edit(buttons=current_test.get_buttons())
            await event.answer("Отмена")
            return

        new_fen = current_test.move(current_test.selected, (r, c))
        current_test.selected = None
        waiting_for_coords = False
        current_legal_moves = []

        await event.edit(f"Ход сделан!\n`{new_fen}`", buttons=current_test.get_buttons())
        await event.answer("ОК")
    else:
        if current_test.board[r][c] != '.':
            current_test.selected = (r, c)
            waiting_for_coords = True
            await event.edit(
                f"Фигура выбрана. Жду ходы в консоли (напр. e4, d5):",
                buttons=current_test.get_buttons(selected=(r, c)),
            )
            await event.answer("Жду консоль")
        else:
            await event.answer("Там пусто")


async def console_listener():
    while True:
        await console_active.wait()

        prompt = "КОНСОЛЬ (Введи FEN): " if not waiting_for_coords else "КОНСОЛЬ (Введи ходы e2,e4): "
        user_input = await asyncio.get_event_loop().run_in_executor(None, input, prompt)

        if not console_active.is_set() or not last_msg_event:
            continue

        try:
            if "/" in user_input:
                current_test.set_fen(user_input)
                current_test.selected = None
                waiting_for_coords = False
                current_legal_moves = []
                await last_msg_event.edit(
                    f"FEN обновлен через консоль!\n`{current_test.fen}`",
                    buttons=current_test.get_buttons(),
                )
                print("Доска обновлена.")
            elif waiting_for_coords:
                raw_moves = user_input.replace(" ", "").split(",")
                legal_coords = []
                for m in raw_moves:
                    coord = current_test.notation_to_coords(m)
                    if coord:
                        legal_coords.append(coord)

                if legal_coords:
                    current_legal_moves = legal_coords
                    await last_msg_event.edit(
                        f"Получены ходы: **{user_input}**",
                        buttons=current_test.get_buttons(selected=current_test.selected, legal_moves=legal_coords),
                    )
                else:
                    print("Ошибка формата координат.")
        except Exception as e:
            print(f"Ошибка консоли: {e}")
