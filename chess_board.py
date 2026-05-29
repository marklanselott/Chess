from telethon import Button

def get_legal_moves_for_piece(fen: str, from_cell: str) -> set:
    """
    Обчислює легальні ходи для фігури на заданій клітинці.
    Повертає множину можливих ходів за правилами шахів.
    """
    if not from_cell or len(from_cell) != 2:
        return set()
    
    # Парсимо FEN
    parts = fen.split()
    if not parts:
        return set()
    
    position_part = parts[0]
    active_color = parts[1] if len(parts) > 1 else 'w'
    
    # Будуємо мапу дошки
    board = {}
    rows = position_part.split('/')
    for row_idx, row_str in enumerate(rows):
        rank = 8 - row_idx
        col_idx = 0
        for char in row_str:
            if char.isdigit():
                col_idx += int(char)
            else:
                col = chr(ord('a') + col_idx)
                cell = f"{col}{rank}"
                board[cell] = char
                col_idx += 1
    
    # Визначаємо чий хід
    our_color = 'white' if active_color == 'w' else 'black'
    is_white = our_color == 'white'
    
    from_col = ord(from_cell[0]) - ord('a')
    from_row = int(from_cell[1]) - 1
    
    piece = board.get(from_cell, '.')
    if piece == '.':
        return set()
    
    # Перевіряємо чи наша фігура
    is_our_piece = piece.isupper() if is_white else piece.islower()
    if not is_our_piece:
        return set()
    
    legal_moves = set()
    piece_type = piece.upper()
    
    # Пішак
    if piece_type == 'P':
        direction = 1 if is_white else -1
        
        # 1. Хід на 1 клітинку вперед
        target_rank_1 = from_row + direction
        cell_1_free = False
        if 0 <= target_rank_1 <= 7:
            target_cell_1 = chr(ord('a') + from_col) + str(target_rank_1 + 1)
            if target_cell_1 not in board or board[target_cell_1] == '.':
                legal_moves.add(target_cell_1)
                cell_1_free = True
        
        # 2. Хід на 2 клітинки вперед (якщо ще не ходив)
        is_initial_rank = (from_row == 1 if is_white else from_row == 6)
        if is_initial_rank and cell_1_free:
            target_rank_2 = from_row + (direction * 2)
            target_cell_2 = chr(ord('a') + from_col) + str(target_rank_2 + 1)
            if target_cell_2 not in board or board[target_cell_2] == '.':
                legal_moves.add(target_cell_2)
        
        # 3. Взяття фігур по діагоналі
        for dcol in [-1, 1]:
            target_col = from_col + dcol
            target_rank = from_row + direction
            if 0 <= target_col <= 7 and 0 <= target_rank <= 7:
                target_cell = chr(ord('a') + target_col) + str(target_rank + 1)
                if target_cell in board and board[target_cell] != '.':
                    target_piece = board[target_cell]
                    is_target_our = target_piece.isupper() if is_white else target_piece.islower()
                    if not is_target_our:
                        legal_moves.add(target_cell)
    
    # Кінь
    elif piece_type == 'N':
        knight_moves = [
            (2, 1), (2, -1), (-2, 1), (-2, -1),
            (1, 2), (1, -2), (-1, 2), (-1, -2)
        ]
        for dcol, drow in knight_moves:
            target_col = from_col + dcol
            target_row = from_row + drow
            if 0 <= target_col <= 7 and 0 <= target_row <= 7:
                target_cell = chr(ord('a') + target_col) + str(target_row + 1)
                if target_cell not in board or board[target_cell] == '.':
                    legal_moves.add(target_cell)
                else:
                    target_piece = board[target_cell]
                    is_target_our = target_piece.isupper() if is_white else target_piece.islower()
                    if not is_target_our:
                        legal_moves.add(target_cell)
    
    # Король
    elif piece_type == 'K':
        for drow in [-1, 0, 1]:
            for dcol in [-1, 0, 1]:
                if drow == 0 and dcol == 0:
                    continue
                target_col = from_col + dcol
                target_row = from_row + drow
                if 0 <= target_col <= 7 and 0 <= target_row <= 7:
                    target_cell = chr(ord('a') + target_col) + str(target_row + 1)
                    if target_cell not in board or board[target_cell] == '.':
                        legal_moves.add(target_cell)
                    else:
                        target_piece = board[target_cell]
                        is_target_our = target_piece.isupper() if is_white else target_piece.islower()
                        if not is_target_our:
                            legal_moves.add(target_cell)
    
    # Ладья
    elif piece_type == 'R':
        for direction in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            dcol, drow = direction
            for i in range(1, 8):
                target_col = from_col + dcol * i
                target_row = from_row + drow * i
                if not (0 <= target_col <= 7 and 0 <= target_row <= 7):
                    break
                target_cell = chr(ord('a') + target_col) + str(target_row + 1)
                if target_cell not in board or board[target_cell] == '.':
                    legal_moves.add(target_cell)
                else:
                    target_piece = board[target_cell]
                    is_target_our = target_piece.isupper() if is_white else target_piece.islower()
                    if not is_target_our:
                        legal_moves.add(target_cell)
                    break
    
    # Слон
    elif piece_type == 'B':
        for direction in [(1, 1), (1, -1), (-1, 1), (-1, -1)]:
            dcol, drow = direction
            for i in range(1, 8):
                target_col = from_col + dcol * i
                target_row = from_row + drow * i
                if not (0 <= target_col <= 7 and 0 <= target_row <= 7):
                    break
                target_cell = chr(ord('a') + target_col) + str(target_row + 1)
                if target_cell not in board or board[target_cell] == '.':
                    legal_moves.add(target_cell)
                else:
                    target_piece = board[target_cell]
                    is_target_our = target_piece.isupper() if is_white else target_piece.islower()
                    if not is_target_our:
                        legal_moves.add(target_cell)
                    break
    
    # Ферзь
    elif piece_type == 'Q':
        for direction in [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]:
            dcol, drow = direction
            for i in range(1, 8):
                target_col = from_col + dcol * i
                target_row = from_row + drow * i
                if not (0 <= target_col <= 7 and 0 <= target_row <= 7):
                    break
                target_cell = chr(ord('a') + target_col) + str(target_row + 1)
                if target_cell not in board or board[target_cell] == '.':
                    legal_moves.add(target_cell)
                else:
                    target_piece = board[target_cell]
                    is_target_our = target_piece.isupper() if is_white else target_piece.islower()
                    if not is_target_our:
                        legal_moves.add(target_cell)
                    break
    
    return legal_moves

def generate_chess_keyboard(fen: str, selected_cell: str = None, player_color: str = 'white') -> list:
    """
    Парсить FEN и собирает клавиатуру.
    При player_color='black' доска переворачивается визуально.
    """
    pieces_map = {
        'P': '▫️', 'R': '♜', 'N': '♞', 'B': '♝', 'Q': '♛', 'K': '♚',
        'p': '▪️', 'r': '♖', 'n': '♘', 'b': '♗', 'q': '♕', 'k': '♔'
    }
    
    cols = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
    position_part = fen.split(' ')[0]
    rows = position_part.split('/')
    
    legal_moves = set()
    if selected_cell:
        legal_moves = get_legal_moves_for_piece(fen, selected_cell.lower())
    
    keyboard = []

    # ЛОГИКА ПЕРЕВОРОТА:
    # Если мы за черных, меняем порядок строк (рядов) и столбцов на обратный
    row_range = range(8) if player_color == 'white' else range(7, -1, -1)
    col_range = range(8) if player_color == 'white' else range(7, -1, -1)

    for row_idx in row_range:
        # Для белых: 8-0=8 (8-й ряд), для черных: 8-7=1 (1-й ряд)
        current_rank = 8 - row_idx
        row_str = rows[row_idx]
        
        full_row = []
        for char in row_str:
            if char.isdigit():
                full_row.extend(['.'] * int(char))
            else:
                full_row.append(char)
        
        row_buttons = []
        for col_idx in col_range:
            cell_name = f"{cols[col_idx]}{current_rank}"
            cell_content = full_row[col_idx]
            
            if cell_content == '.':
                display_text = "  " 
            else:
                display_text = pieces_map.get(cell_content, cell_content)
            
            # Логика подсветки
            if selected_cell and cell_name == selected_cell.lower():
                display_text = f"{{{display_text.strip()}}}"
            elif cell_name in legal_moves:
                display_text = "●" if cell_content == '.' else f"[{display_text.strip()}]"
            
            btn = Button.inline(display_text, data=f"cell_{cell_name}")
            row_buttons.append(btn)
            
        keyboard.append(row_buttons)
    
    return keyboard