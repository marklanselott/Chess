# Chess

## Окружение (.env)

Для работы приложения необходимо создать файл `.env` в корневой директории и указать следующие параметры:

```env
# Токен доступа для генерации JWT (передается в Header: token)
SECURE_TOKEN=your_secure_admin_token

# Настройки JWT
SECRET_WORD=your_secret_key_for_jwt
ALGORITHM=HS256
EXPIRE_TOKEN_TIME=3600
```

## Запуск приложения (start.sh)

Для запуска сервера используйте скрипт `start.sh`:
```bash
bash start.sh
```

**Что делает скрипт:**
1.  **Управление окружением**: Автоматически проверяет наличие папки `.venv`. Если её нет — создает виртуальное окружение.
2.  **Обновление зависимостей**: Активирует окружение, обновляет `pip` и устанавливает все пакеты из `requirements.txt`.
3.  **Запуск сервера**: Запускает FastAPI приложение через `uvicorn` на порту `9538` в режиме автоперезагрузки (`--reload`).

> **Примечание**: Порт и другие параметры запуска (например, хост) указываются напрямую внутри файла `start.sh`. Если вам нужно изменить порт, сделайте это в строке запуска `uvicorn`.

## Примеры запросов (cURL)

Ниже приведены основные запросы для работы с API.

### 1. Получение JWT токена
Для выполнения всех последующих запросов вам понадобится JWT токен. Он передается в параметре `token`.
```bash
curl -X POST "http://127.0.0.1:9538/api/auth/create-token" \
     -H "token: your_secure_admin_token"
```

### 2. Регистрация пользователя
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

### 3. Поиск пользователя
```bash
curl -X POST "http://127.0.0.1:9538/api/user/search/?token=YOUR_JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
           "unique": "max"
         }'
```

### 4. Обновление данных
```bash
curl -X POST "http://127.0.0.1:9538/api/user/search/update/max?token=YOUR_JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
           "first_name": "Maximilian"
         }'
```
