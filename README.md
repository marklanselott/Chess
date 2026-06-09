# Chess

Backend API для шахового застосунку на FastAPI. Проєкт відповідає за користувачів, друзів, пошук суперника, партії проти інших гравців або AI, збереження ходів і статистику.

## Можливості

- реєстрація, пошук, оновлення та видалення користувачів;
- JWT-авторизація для захищених API-ендпоінтів;
- рейтинг користувачів і статистика партій;
- заявки в друзі та список друзів;
- пошук суперника за рейтингом;
- гра проти AI з рівнем складності від 1 до 5;
- збереження стану дошки у FEN та JSON-представленні;
- обробка здачі, мату, нічиєї та зміни рейтингу тільки у партіях між гравцями.

## Технології

- Python 3
- FastAPI
- SQLAlchemy Async
- PostgreSQL
- PyJWT
- pytest
- зовнішній Chess Core API для перевірки ходів і AI-ходів

## Налаштування `.env`

Створіть файл `.env` у корені проєкту та заповніть змінні:

```env
# Основний API
MAIN_API_PORT=9538

# База даних
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/chess

# Авторизація
SECURE_TOKEN=your_secure_admin_token
SECRET_WORD=your_secret_key_for_jwt
ALGORITHM=HS256
EXPIRE_TOKEN_TIME=3600

# Користувачі та матчмейкінг
BASE_USER_RATING=1000
RATING_SEARCH_RANGE=100

# Chess Core API
CHESS_CORE_API_PORT=4956
CHESS_CORE_API_PATH=path/to/ChessAPI.dll
CHESS_CORE_TIMEOUT=120
```

> `start.sh` запускає зовнішній Chess Core через `dotnet`, тому шлях у `CHESS_CORE_API_PATH` має вказувати на зібраний `.dll` файл цього сервісу.
> На Linux `start.sh` безпечно читає `.env` навіть із Windows-переносами рядків. Якщо експортуєте `.env` вручну через `source .env`, спочатку приберіть CRLF.

## Встановлення та запуск

Найпростіший спосіб запустити проєкт:

```bash
bash start.sh
```

Скрипт:

1. створює `.venv`, якщо його ще немає;
2. активує віртуальне середовище;
3. оновлює `pip` і встановлює залежності з `requirements.txt`;
4. завантажує змінні з `.env`;
5. запускає Chess Core API;
6. запускає FastAPI через `uvicorn` на порту `MAIN_API_PORT`.

Після запуску перевірити API можна так:

```bash
curl http://127.0.0.1:9538/health
```

Очікувана відповідь:

```json
{"status":"ok"}
```

## Тести

Запуск усіх тестів:

```bash
bash tests.sh
```

Або напряму через pytest:

```bash
python -m pytest -s tests
```

Тести автоматично запускають Chess Core з `CHESS_CORE_API_PATH` і основний FastAPI через
`uvicorn app:app`, якщо ці сервіси ще не доступні. Файли `ChessAPI.dll`, `ChessLib.dll`,
`ChessAI.dll` і `ChessAPI.deps.json` мають бути з одного publish-білду.

## Документація API

Після старту сервера інтерактивна документація доступна за адресами:

- `http://127.0.0.1:9538/docs`
- `http://127.0.0.1:9538/redoc`

## Авторизація

Спочатку отримайте JWT:

```bash
curl -X POST "http://127.0.0.1:9538/api/auth/create-token" \
  -H "token: your_secure_admin_token"
```

У відповідь API поверне:

```json
{
  "jwt": "YOUR_JWT_TOKEN",
  "exp": 1710000000
}
```

Усі захищені ендпоінти приймають JWT у параметрі `token`:

```text
?token=YOUR_JWT_TOKEN
```

## Приклади запитів

### Реєстрація користувача

```bash
curl -X POST "http://127.0.0.1:9538/api/user/register?token=YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "unique": "max",
    "email": "max@example.com",
    "password": "secure_password",
    "first_name": "Max"
  }'
```

### Пошук користувача

```bash
curl -X POST "http://127.0.0.1:9538/api/user/search/?token=YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "unique": "max"
  }'
```

### Оновлення користувача

```bash
curl -X POST "http://127.0.0.1:9538/api/user/update/user_id/USER_ID?token=YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Maksym"
  }'
```

### Рейтинг гравців

```bash
curl -X POST "http://127.0.0.1:9538/api/user/rating?token=YOUR_JWT_TOKEN&start=0"
```

### Статистика користувача

```bash
curl "http://127.0.0.1:9538/api/user/stats/user_id/USER_ID?token=YOUR_JWT_TOKEN"
```

### Запуск гри проти AI

```bash
curl -X POST "http://127.0.0.1:9538/api/game/ai/start?token=YOUR_JWT_TOKEN&user_id=USER_ID&user_color=white&ai_difficulty=3"
```

Партії проти AI не змінюють рейтинг користувача або AI. Рейтинг змінюється тільки
після завершення партії між двома гравцями.

### Хід у партії

```bash
curl "http://127.0.0.1:9538/api/game/move?token=YOUR_JWT_TOKEN&game_id=GAME_ID&from_to=e2e4&promoteTo=q"
```

`promoteTo` передається в Chess Core для перетворення пішака. Якщо параметр не вказаний,
API використовує `q` за замовчуванням. Також підтримується короткий запис у `from_to`,
наприклад `e7e8q`.

### Хід AI

```bash
curl -X POST "http://127.0.0.1:9538/api/game/ai/move?token=YOUR_JWT_TOKEN&game_id=GAME_ID"
```

### Здача партії

```bash
curl -X POST "http://127.0.0.1:9538/api/game/surrender?token=YOUR_JWT_TOKEN&user_id=USER_ID"
```

### Друзі

```bash
curl -X POST "http://127.0.0.1:9538/api/friends/requests?token=YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "USER_ID",
    "friend_id": "FRIEND_ID"
  }'
```

```bash
curl "http://127.0.0.1:9538/api/friends/requests/sent/user_id/USER_ID?token=YOUR_JWT_TOKEN"
```

```bash
curl "http://127.0.0.1:9538/api/friends/requests/incoming/user_id/USER_ID?token=YOUR_JWT_TOKEN"
```

```bash
curl -X POST "http://127.0.0.1:9538/api/friends/requests/REQUEST_ID/accept?token=YOUR_JWT_TOKEN&user_id=USER_ID"
```

```bash
curl -X DELETE "http://127.0.0.1:9538/api/friends/requests/REQUEST_ID/cancel?token=YOUR_JWT_TOKEN&user_id=USER_ID"
```

```bash
curl -X DELETE "http://127.0.0.1:9538/api/friends/requests/REQUEST_ID/decline?token=YOUR_JWT_TOKEN&user_id=USER_ID"
```

```bash
curl -X DELETE "http://127.0.0.1:9538/api/friends/friend?token=YOUR_JWT_TOKEN&user_id=USER_ID&friend_id=FRIEND_ID"
```

`cancel` скасовує власну відправлену заявку, `decline` відхиляє вхідну заявку,
`friend` видаляє користувача з друзів.

### Пошук суперника

```bash
curl -X POST "http://127.0.0.1:9538/api/opponents/search/start?token=YOUR_JWT_TOKEN&user_id=USER_ID"
```

Очікування знайденого суперника:

```bash
curl "http://127.0.0.1:9538/api/opponents/await?token=YOUR_JWT_TOKEN&user_id=USER_ID"
```

Зупинка пошуку:

```bash
curl -X POST "http://127.0.0.1:9538/api/opponents/search/stop?token=YOUR_JWT_TOKEN&user_id=USER_ID"
```

## Структура проєкту

```text
.
├── app.py              # FastAPI-застосунок і підключення роутерів
├── auth.py             # створення та перевірка JWT
├── requests.py         # Pydantic-моделі вхідних даних
├── responses.py        # Pydantic-моделі відповідей
├── utils.py            # допоміжні функції
├── db/                 # підключення до БД, моделі та ініціалізація
├── moduls/             # API-модулі: user, friends, opponents, game
├── scripts/            # допоміжні скрипти
└── tests/              # pytest-тести
```

## Примітки

- База даних ініціалізується під час старту застосунку.
- Таблиці створюються автоматично через SQLAlchemy.
- Chess Core має бути доступним до виконання шахових ходів, AI-ходів і перевірки правил.
- У прикладах замініть `YOUR_JWT_TOKEN`, `USER_ID`, `FRIEND_ID`, `REQUEST_ID` і `GAME_ID` на реальні значення.
