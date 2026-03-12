# Comment Analytics MVP

Сервис аналитики комментариев под постами в Telegram и VK. Пользователь создает проект, добавляет ссылки на открытые источники, запускает индексацию, а затем строит отчет по теме, ключевым словам и периоду.

## Stack

- Frontend: Next.js 14, TypeScript, Tailwind CSS, React Query, Zustand, shadcn-style UI
- Backend: FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2
- Data: PostgreSQL, Redis, Celery
- NLP: sentence-transformers fallback, keyword extraction, topic grouping, heuristic sentiment, OpenAI-compatible summary
- Infra: Docker, docker-compose

## Architecture Overview

- `frontend/`: UI, typed API client, project/source/report pages.
- `backend/app/providers/`: единый provider interface, live adapters для Telegram/VK и demo fallback.
- `backend/app/services/`: orchestration слои для projects, sources, ingestion и analytics.
- `backend/app/analytics/`: sentiment, keywords, topics, relevance, aggregation, summary generation.
- `backend/app/tasks/`: фоновые Celery-задачи для ingestion и анализа.
- `backend/app/models/`: raw data (`posts`, `comments`) отдельно от processed data (`comment_analysis`, `report_snapshots`).

## Repository Tree

```text
comment-analytics-mvp/
  README.md
  docker-compose.yml
  .env.example
  frontend/
  backend/
  worker/
  infra/
```

## Live Credentials

Для реального использования нужны credentials.

### Telegram

- `TELEGRAM_API_ID`
- `TELEGRAM_API_HASH`
- `TELEGRAM_SESSION_STRING`

Session string можно получить так:

```bash
cd scripts
python generate-telegram-session.py
```

Требование: использовать Telegram user session. Публичный канал должен быть доступен аккаунту, а комментарии будут собираться только если у канала есть discussion thread.

### VK

- `VK_API_TOKEN`
- `VK_API_VERSION` (по умолчанию `5.199`)

Нужен рабочий VK API token, который может читать публичные wall posts и comments.

## Local Run

1. Скопируйте `.env.example` в `.env`, если нужен отдельный runtime env.
2. Запустите сервисы:

```bash
docker compose up --build
```

3. URLs:

- Frontend: `http://localhost:3000`
- Backend docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

## Migrations

В контейнере backend:

```bash
alembic upgrade head
```

Локально из `backend/`:

```bash
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

## Worker

Локально из `backend/`:

```bash
celery -A app.tasks.celery_app:celery_app worker --loglevel=info
```

## Quick Start Without Docker

По умолчанию `scripts/start-local.ps1` поднимает live-mode без фоновых очередей. Индексация и анализ в этом режиме исполняются синхронно.

```powershell
cd d:\ai-analysis\comment-analytics-mvp
powershell -ExecutionPolicy Bypass -File .\scripts\start-local.ps1
```

Для synthetic demo:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-local.ps1 -DemoMode
```

## Live Flow

1. Установите `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_SESSION_STRING`, `VK_API_TOKEN`.
2. Запустите `scripts/start-local.ps1`.
3. Создайте проект.
4. Добавьте реальные публичные `t.me/...` и `vk.com/...` ссылки.
5. Нажмите `Start indexing`.
6. После перехода источников в `ready` откройте `Analytics`.
7. Сформируйте отчет.

## Demo Flow

1. Откройте `/projects`.
2. Создайте проект.
3. Перейдите в `Sources`.
4. Добавьте demo-compatible ссылки, например:
   - `https://t.me/demo_channel`
   - `https://t.me/demo_channel/100`
   - `https://vk.com/democommunity`
   - `https://vk.com/wall-1_123`
5. Нажмите `Start indexing`.
6. После перехода источников в `ready` откройте `Analytics`.
7. Сформируйте отчет и откройте report page.

## Notes

- Live mode включен по умолчанию через `DEMO_MODE=false`.
- В local default `BACKGROUND_JOBS_ENABLED=false`, поэтому Redis/Celery не обязательны для одного узла.
- Demo mode доступен отдельно для synthetic end-to-end проверки.
- Реальные интеграции находятся в `backend/app/providers/telegram_provider.py` и `backend/app/providers/vk_provider.py`.
- Если `sentence-transformers` или LLM endpoint недоступны, система использует локальные эвристики и все равно возвращает отчет.
