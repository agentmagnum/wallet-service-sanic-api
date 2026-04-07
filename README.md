# Async Wallet Service

Тестовое backend-приложение на `Python + Sanic + SQLAlchemy + PostgreSQL` в формате REST API.

## Что реализовано

- Авторизация по `email/password` для пользователя и администратора.
- Получение данных о текущем пользователе.
- Получение пользователем списка своих счетов и платежей.
- CRUD для пользователей со стороны администратора.
- Получение администратором списка пользователей вместе с их счетами и балансами.
- Обработка webhook платежной системы с проверкой `signature`, автосозданием счета и защитой от повторного зачисления по одному `transaction_id`.
- Docker Compose для быстрого запуска проекта.
- Alembic-миграция с тестовыми данными.

## Стек

- `Sanic`
- `SQLAlchemy` async
- `PostgreSQL`
- `Alembic`
- `Docker Compose`

## Данные по умолчанию

- Пользователь:
  `user@example.com` / `UserPass123!`
- Администратор:
  `admin@example.com` / `AdminPass123!`

Тестовый счет пользователя создается в миграции с `id=1` и балансом `0.00`.

## Переменные окружения

Скопируйте файл:

```bash
cp .env.example .env
```

Для Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Ключевые настройки:

- `APP_WORKERS`:
  количество worker-процессов Sanic. Для локального запуска по умолчанию `1`, в Docker Compose выставляется `2`.
- `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`, `DB_POOL_RECYCLE`:
  настройки пула соединений SQLAlchemy.
- `DB_USE_NULL_POOL`:
  позволяет переключить SQLAlchemy на `NullPool`, если приложение будет работать за внешним PgBouncer.
- `DB_STATEMENT_CACHE_SIZE`:
  размер statement cache для `asyncpg`; при работе за PgBouncer в transaction pooling режиме часто имеет смысл выставлять `0`.
- `LOGIN_RATE_LIMIT_REQUESTS`, `LOGIN_RATE_LIMIT_WINDOW_SECONDS`:
  мягкий rate limit для `POST /api/v1/auth/login`.
- `WEBHOOK_RATE_LIMIT_REQUESTS`, `WEBHOOK_RATE_LIMIT_WINDOW_SECONDS`:
  мягкий rate limit для `POST /api/v1/webhooks/payments`.

## Запуск через Docker Compose

1. Создать `.env` из `.env.example`.
2. Выполнить:

```bash
docker compose up --build
```

3. Приложение будет доступно по адресу:
   [http://localhost:8000](http://localhost:8000)

При старте контейнера автоматически выполняется `alembic upgrade head`.

## Запуск без Docker Compose

1. Убедиться, что локально доступен PostgreSQL.
2. Создать базу данных `wallet_service`.
3. Создать и активировать виртуальное окружение.
4. Установить зависимости:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Для Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

5. Создать `.env` из `.env.example` и при необходимости скорректировать `DATABASE_URL`.
6. Применить миграции:

```bash
alembic upgrade head
```

7. Запустить приложение:

```bash
python -m app.main
```

## Основные роуты

### Аутентификация

- `POST /api/v1/auth/login`

Пример тела запроса:

```json
{
  "email": "user@example.com",
  "password": "UserPass123!"
}
```

### Пользователь

- `GET /api/v1/me`
- `GET /api/v1/accounts`
- `GET /api/v1/payments`

Для `GET /api/v1/payments` поддерживаются опциональные query-параметры:

- `limit`
- `offset`

### Администратор

- `GET /api/v1/admin/users`
- `GET /api/v1/admin/users/<user_id>`
- `POST /api/v1/admin/users`
- `PATCH /api/v1/admin/users/<user_id>`
- `DELETE /api/v1/admin/users/<user_id>`

Для `GET /api/v1/admin/users` также поддерживаются опциональные query-параметры:

- `limit`
- `offset`

### Webhook платежей

- `POST /api/v1/webhooks/payments`

Пример тела запроса:

```json
{
  "transaction_id": "5eae174f-7cd0-472c-bd36-35660f00132b",
  "user_id": 1,
  "account_id": 1,
  "amount": 100,
  "signature": "7b47e41efe564a062029da3367bde8844bea0fb049f894687cee5d57f2858bc8"
}
```

Подпись рассчитывается как SHA256 от строки:

```text
{account_id}{amount}{transaction_id}{user_id}{secret_key}
```

При `PAYMENT_SECRET_KEY=gfdmhghif38yrf9ew0jkf32` пример выше проходит валидацию.

## Проверка работоспособности

- `GET /healthz` возвращает статус приложения.
- Повторный webhook с тем же `transaction_id` не увеличивает баланс повторно и возвращает статус `duplicate`.
- `POST /api/v1/auth/login` и `POST /api/v1/webhooks/payments` защищены мягким in-memory rate limit.
