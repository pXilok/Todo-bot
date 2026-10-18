# Todo-bot: Telegram-бот со списком дел и напоминаниями

Учебный проект: Telegram-бот для списка задач с напоминаниями. Бизнес-логика вынесена на сервер FastAPI, а бот играет роль тонкого адаптера между Telegram и сервером.
БЕРЕЗИН ДАНИИЛ МИХАЙЛОВИЧ 2 КУРС РПО
![Python](https://img.shields.io/badge/Python-3.13-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.1xx-009688)
![aiogram](https://img.shields.io/badge/aiogram-3.x-2CA5E0)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)

## Возможности

- Добавление задач с текстом до 200 символов.
- Список задач с кнопками: отметить выполненной, поставить напоминание, удалить.
- Напоминания в Telegram. Время можно задать абсолютно (`18:30`, `25.12 09:00`) или относительно (`+30m`, `+2h`, `+1d`).
- Настройки: часовой пояс и включение или выключение напоминаний.
- Команды `/start`, `/help`, `/settings`, `/stats`, `/cancel`.
- Диалоги через машину состояний (FSM): бот помнит, что вы делаете, например ждёт текст задачи или время напоминания.
- Защита от повторной обработки одного и того же сообщения Telegram по `update_id`.
- Очередь исходящих сообщений (outbox): напоминания не теряются, даже если бот временно недоступен.
- Swagger-документация API на `/docs`.

## Стек

| Часть | Технологии |
|---|---|
| Сервер | Python 3.13, FastAPI, Uvicorn, Pydantic, SQLAlchemy 2 (async), Alembic |
| Бот | aiogram 3, httpx |
| База данных | SQLite (для учебного варианта) |
| Инфраструктура | Docker, Docker Compose |
| Тесты | pytest |

## Архитектура
```text
Telegram ──► Бот (aiogram) ──HTTP/JSON──► Сервер (FastAPI) ──► SQLite
                  ▲                              │
                  └──── outbox: сообщения ◄──────┘
```

- **Бот** получает обновления от Telegram, приводит их к единому формату события и отправляет на сервер. Он не хранит задачи и не решает, что ответить: сервер возвращает список действий (отправить текст, показать кнопки, изменить состояние).
- **Сервер** хранит пользователей, задачи, состояние диалога, историю сообщений и очередь исходящих сообщений. Все команды и правила работают здесь.
- **Outbox**: сервер ставит напоминания в очередь, а бот периодически забирает их (`POST /api/v1/outbox/claim`) и отправляет в Telegram.

Подробное описание сценариев и состояний: [docs/report.md](docs/report.md) (если файл есть).

## Структура проекта
```text
todo-bot/
├── bot/

# Telegram-адаптер
│   ├── bot/

# код: main.py, api_client.py, outbox_poller.py, keyboards.py, ...
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── server/

# сервер бизнес-логики
│   ├── app/

# код FastAPI-приложения
│   ├── alembic/

# миграции базы данных
│   ├── tests/

# тесты pytest
│   ├── data/

# локальная база (не попадает в Git)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── docs/
│   └── openapi.json

# описание API в формате OpenAPI
├── docker-compose.yml
└── README.md
```

## Быстрый старт (Docker)

### Требования

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows, macOS или Linux)
- Telegram-бот, созданный через [@BotFather](https://t.me/BotFather)

### Шаги

1. Клонируйте репозиторий:
```bash
   git clone https://github.com/pXilok/Todo-bot.git
   cd Todo-bot
```

2. Создайте файлы настроек из примеров:
```bash
   cp bot/.env.example bot/.env
   cp server/.env.example server/.env
```

   В Windows PowerShell используйте `Copy-Item bot\.env.example bot\.env` и `Copy-Item server\.env.example server\.env`.

3. Откройте `bot/.env` и вставьте токен бота в `BOT_TOKEN`. Значение `SERVICE_TOKEN` должно быть одинаковым в `bot/.env` и `server/.env`.

4. Запустите оба сервиса:
```bash
   docker compose up -d --build
```

5. Проверьте состояние:
```bash
   docker compose ps
```

   Оба сервиса должны быть в статусе `Up`.

6. Откройте бота в Telegram и отправьте `/start`.

Сервер доступен на `http://127.0.0.1:8000`, Swagger на `http://127.0.0.1:8000/docs`.

### Полезные команды
```bash
docker compose logs -f bot

# лог бота в реальном времени
docker compose logs -f server

# лог сервера
docker compose stop

# остановить (данные сохраняются)
docker compose start

# снова запустить
docker compose down

# остановить и удалить контейнеры
docker compose up -d --build

# пересобрать после изменения кода
```

## Запуск без Docker (для разработки)

Нужен Python 3.13.

Сервер:
```bash
cd server
python -m venv .venv
source .venv/bin/activate

# Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:create_app --factory --reload
```

Бот, в отдельном терминале:
```bash
cd bot
python -m venv .venv
source .venv/bin/activate

# Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m bot.main
```

## Настройка

### bot/.env

| Переменная | Назначение | Пример |
|---|---|---|
| `BOT_TOKEN` | Токен от BotFather | `123456789:AA...` |
| `SERVICE_TOKEN` | Служебный токен для связи с сервером | `длинная-случайная-строка` |
| `SERVER_URL` | Адрес сервера | `http://127.0.0.1:8000` (в Docker задаётся автоматически) |
| `OUTBOX_POLL_INTERVAL` | Интервал опроса очереди, секунд | `5` |
| `LOG_LEVEL` | Уровень логов | `INFO` |

### server/.env

| Переменная | Назначение | Пример |
|---|---|---|
| `ENVIRONMENT` | Окружение | `dev` |
| `LOG_LEVEL` | Уровень логов | `INFO` |
| `DATABASE_URL` | Строка подключения к базе | `sqlite+aiosqlite:///./data/bot.db` |
| `SERVICE_TOKEN` | Токен бота (заголовок `X-Service-Token`) | совпадает с `bot/.env` |
| `ADMIN_TOKEN` | Токен администратора (заголовок `X-Admin-Token`) | `длинная-случайная-строка` |
| `MAX_ACTIVE_TASKS_PER_USER` | Лимит активных задач на пользователя | `50` |
| `TASKS_PAGE_SIZE` | Количество задач в списке | `10` |

Файлы `.env` содержат секреты и не попадают в Git (см. `.gitignore`). В репозитории лежат только `.env.example` с заглушками.

## Примеры использования

Диалог с ботом:
```text
Пользователь: /start
Бот:          Привет! Я помогу вести список дел и напоминать о важном.
              [➕ Добавить задачу] [📋 Мои задачи]

Пользователь: ➕ Добавить задачу
Бот:          Напишите текст задачи (до 200 символов).
Пользователь: Купить молоко
Бот:          Задача #1 добавлена: Купить молоко.

Пользователь: 📋 Мои задачи
Бот:          Ваши задачи (активных: 1, выполнено: 0):
              #1 Купить молоко   [✅] [⏰] [🗑]

Пользователь: ⏰ (у задачи #1), затем +30m
Бот:          Готово, напомню
```
