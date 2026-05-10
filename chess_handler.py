from telethon import Button

PIECES = {
    # БЕЛЫЕ ФИГУРЫ (будут отображаться темными эмодзи, так как темные на темном фоне бота)
    'K': '♚', 'Q': '♛', 'R': '♜', 'B': '♝', 'N': '♞', 'P': '▫️', # (Король, Ферзь, Ладья, Слон, Конь, Пешка)

    # ЧЕРНЫЕ ФИГУРЫ (будут отображаться светлыми эмодзи)
    'k': '♔', 'q': '♕', 'r': '♖', 'b': '♗', 'n': '♘', 'p': '▪️', # (Король, Ферзь, Ладья, Слон, Конь, Пешка)

    '.': ' ' # Пустая клетка
}

class ChessTest:
    def __init__(self, fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"):
        self.board = []
        self.fen = fen
        self.selected = None
        self.set_fen(fen)

    def set_fen(self, fen):
        """Парсит FEN строку в двумерный массив 8x8"""
        self.fen = fen
        self.board = []
        rows = fen.split(' ')[0].split('/')
        for row in rows:
            line = []
            for char in row:
                if char.isdigit():
                    line.extend(['.'] * int(char))
                else:
                    line.append(char)
            self.board.append(line)

    def matrix_to_fen(self):
        """Конвертирует текущее состояние массива обратно в FEN"""
        fen_rows = []
        for row in self.board:
            empty = 0
            res = ""
            for char in row:
                if char == '.':
                    empty += 1
                else:
                    if empty > 0:
                        res += str(empty)
                        empty = 0
                    res += char
            if empty > 0:
                res += str(empty)
            fen_rows.append(res)
        self.fen = "/".join(fen_rows)
        return self.fen

    def notation_to_coords(self, notation):
        """Переводит 'e4' в (row, col) -> (4, 4)"""
        try:
            notation = notation.strip().lower()
            if len(notation) < 2: return None
            col = ord(notation[0]) - ord('a')
            row = 8 - int(notation[1])
            if 0 <= row < 8 and 0 <= col < 8:
                return row, col
        except (ValueError, IndexError):
            pass
        return None

    def get_buttons(self, selected=None, legal_moves=None):
        """Генерирует кнопки: [] для выбора, {} для взятия, 🟢 для пустых ходов"""
        if legal_moves is None: legal_moves = []
        kb = []
        for r in range(8):
            row_btns = []
            for c in range(8):
                char = self.board[r][c]
                text = PIECES.get(char, ' ')
                
                # Если клетка в списке легальных ходов
                if (r, c) in legal_moves:
                    if char == '.':
                        text = "🟢" # Пустое поле — рисуем кружок
                    else:
                        text = f"{{{text}}}" # Фигура под боем — берем в фигурные скобки
                
                # Если это сама выбранная фигура
                elif selected == (r, c):
                    text = f"[{text}]"
                
                row_btns.append(Button.inline(text, data=f"c:{r}:{c}"))
            kb.append(row_btns)
        return kb

    def move(self, start, end):
        """Передвигает фигуру и возвращает обновленный FEN"""
        r1, c1 = start
        r2, c2 = end
        # Совершаем ход в матрице
        self.board[r2][c2] = self.board[r1][c1]
        self.board[r1][c1] = '.'
        return self.matrix_to_fen()