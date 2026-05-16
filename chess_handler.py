from telethon import Button

def generate_chess_keyboard(fen: str, selected_cell: str = None) -> list:
    """
    Парсит FEN и собирает двумерный массив инлайн-кнопок 8х8 для Телеграма.
    Пешки: ▪️ и ▫️. Выбранная клетка берется в { }.
    """
    pieces_map = {
    'P': '▫️', 'R': '♜', 'N': '♞', 'B': '♝', 'Q': '♛', 'K': '♚',
    'p': '▪️', 'r': '♖', 'n': '♘', 'b': '♗', 'q': '♕', 'k': '♔'
    }
    
    cols = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
    position_part = fen.split(' ')[0]
    rows = position_part.split('/')
    
    keyboard = []

    # Идем по строкам сверху вниз (от 8 до 1)
    for row_idx, row_str in enumerate(rows):
        current_rank = 8 - row_idx
        
        # Разворачиваем строку FEN в строку из 8 элементов
        full_row = []
        for char in row_str:
            if char.isdigit():
                full_row.extend(['.'] * int(char))
            else:
                full_row.append(char)
        
        # Собираем один ряд кнопок (8 штук)
        row_buttons = []
        for col_idx, cell_content in enumerate(full_row):
            cell_name = f"{cols[col_idx]}{current_rank}" # Например, "e2"
            
            # Определяем текст на кнопке
            if cell_content == '.':
                # Для пустой клетки можно использовать невидимый символ, пробел или точку
                # Попробуем пробел, чтобы выглядело чисто, как на твоем скрине
                display_text = "  " 
            else:
                display_text = pieces_map.get(cell_content, cell_content)
            
            # Если эта клетка сейчас выбрана — берем текст в фигурные скобки
            if selected_cell and cell_name == selected_cell.lower():
                display_text = f"{{{display_text.strip()}}}"
                
            # Создаем инлайн-кнопку. В data зашиваем её имя, например "cell_e2"
            btn = Button.inline(display_text, data=f"cell_{cell_name}")
            row_buttons.append(btn)
            
        keyboard.append(row_buttons)
        
    # В самый низ под доску добавляем кнопку сдачи на всю ширину
    #keyboard.append([Button.inline("🏳️ Сдаться в этой партии", data="game_surrender")])
    
    return keyboard