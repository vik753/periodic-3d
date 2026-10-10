# Запуск и деплой

Документ описывает три способа запустить проект. Выберите один.

| Способ | Что получаете | Цена | Сложность |
| --- | --- | --- | --- |
| A. GitHub Pages (уже работает) | Сайт со статическими данными | Бесплатно | Ничего делать не нужно |
| B. Свой сервер + Docker Compose | Сайт + живой API + PostgreSQL | VPS от ~5 $/мес | Средняя |
| C. Облачные сервисы без своего сервера | То же, что B | Бесплатные тарифы на старте | Средняя |

Части проекта:

- `apps/web` — сайт (React + Three.js). Собирается в статические файлы.
- `apps/api` — API только для чтения (FastAPI + PostgreSQL).
- `pipeline` — сборка набора данных (Wikidata, PubChem, Materials Project, Википедия).

> **Теория: статический режим и живой API.** Химические данные меняются только при
> новой сборке набора. Поэтому API умеет «сфотографировать» все свои ответы в JSON-файлы
> (`p3d-api export-static`). Сайт читает эти файлы с того же хостинга, сервер не нужен.
> Это способ A. Живой API (способы B и C) нужен для гибких запросов в будущем:
> похожесть соединений, серверный поиск. Формат ответов в обоих режимах один — его
> строит один и тот же код. Режим сайта задаёт переменная `VITE_DATA_MODE=static|api`.

---

## A. GitHub Pages — демо (уже работает)

**Цель.** Держать сайт https://vik753.github.io/periodic-3d/ в актуальном состоянии.

**Команды.** Ничего запускать не нужно. Каждый push в ветку `main` запускает workflow
`ci`. Он проверяет код, собирает сайт, экспортирует данные и публикует сайт в ветку
`gh-pages`.

**Пояснение.** Набор данных для сайта задаёт файл `data/DATASET`:

- `release:data-2026.10.11-r7` — релиз GitHub с полным набором;
- `ci-results:data/latest` — последний тестовый срез (если файла нет).

**Ожидаемый результат.** Через 5–7 минут после push сайт показывает новую версию.

### Как пересобрать набор данных

**Цель.** Обновить соединения, названия и 3D-структуры.

**Команды.**

1. Откройте репозиторий → вкладка **Actions** → workflow **data** → **Run workflow**.
2. Оставьте `only_elements` пустым, `limit` = `0`, `descriptions` = включено.
3. Включите `release`.
4. Нажмите **Run workflow**.

**Пояснение.** Сборка идёт 40–90 минут: источники ограничивают частоту запросов.
Сырые ответы кэшируются, поэтому повторная сборка быстрее. С `release` workflow
публикует релиз `data-<версия>`, записывает его в `data/DATASET` и запускает `ci`.

**Ожидаемый результат.** В разделе **Releases** появляется `Dataset <версия>` с
архивом и отчётом. Через несколько минут сайт работает на новом наборе.

---

## B. Свой сервер с Docker Compose

**Цель.** Сайт, API и база на одной машине.

**Требования.** Linux-сервер: 1 vCPU, 2 ГБ RAM, 10 ГБ диска. Установлены Docker и
Docker Compose (команда `docker compose version` работает). Открыт порт 80 или 443.

### Шаг 1. Код и пароль базы

```bash
git clone https://github.com/vik753/periodic-3d.git
cd periodic-3d
cp infra/.env.example infra/.env
nano infra/.env          # задайте длинный случайный POSTGRES_PASSWORD
```

**Пояснение.** `infra/.env` хранит пароль. Этот файл не попадает в git (`.gitignore`).

### Шаг 2. Сборка и запуск

```bash
docker compose -f infra/docker-compose.yml --env-file infra/.env up -d --build
docker compose -f infra/docker-compose.yml --env-file infra/.env ps
```

**Ожидаемый результат.** Три контейнера: `db`, `api`, `web`. Статус `running`
(у `db` — `healthy`).

### Шаг 3. Схема базы

```bash
docker compose -f infra/docker-compose.yml --env-file infra/.env run --rm api p3d-api migrate
```

**Ожидаемый результат.** Строка `schema is up to date`.

> **Теория: миграции.** Миграция — пронумерованный скрипт, который меняет схему базы
> (таблицы, индексы). Alembic помнит, какие миграции уже применены, и применяет только
> новые. Поэтому команду `migrate` можно запускать после каждого обновления кода.

### Шаг 4. Загрузка набора данных

```bash
mkdir -p data
# Номер релиза — в файле data/DATASET (после "release:")
gh release download data-2026.10.11-r7 --repo vik753/periodic-3d --pattern 'dataset-*.tar.gz' --output data/dataset.tar.gz
docker compose -f infra/docker-compose.yml --env-file infra/.env run --rm -v "$PWD/data:/data" api \
  p3d-api load /data/dataset.tar.gz
```

**Пояснение.** Без `gh` скачайте архив со страницы **Releases** в браузере и положите
его в `data/dataset.tar.gz`. Загрузка заменяет старые данные одной транзакцией: сайт
работает и во время загрузки.

**Ожидаемый результат.** Строка `loaded <версия>: 118 elements, … compounds …`.

### Шаг 5. Проверка

```bash
curl http://localhost:8080/health
curl http://localhost:8080/api/v1/meta
```

**Ожидаемый результат.** `{"status":"ok","version":"…"}` и данные о наборе. Сайт
открывается на `http://<IP сервера>:8080`.

### Шаг 6. Домен и HTTPS

**Цель.** Сайт на своём домене с сертификатом.

**Команды.** Самый простой путь — Caddy перед контейнером `web`:

```bash
sudo apt install -y caddy
sudo tee /etc/caddy/Caddyfile > /dev/null <<'EOF'
periodic.example.com {
  reverse_proxy localhost:8080
}
EOF
sudo systemctl reload caddy
```

**Пояснение.** Замените `periodic.example.com` на свой домен. A-запись домена должна
указывать на IP сервера. Caddy сам получает и продлевает сертификат Let's Encrypt.

**Ожидаемый результат.** `https://periodic.example.com` открывает сайт.

> **Теория: кэш и CDN.** API отдаёт заголовки `Cache-Control` и `ETag`. ETag — это
> версия набора данных. Браузер или CDN (например, Cloudflare) хранит ответ и при
> следующем запросе спрашивает «изменилось ли?». Если набор тот же, API отвечает
> `304 Not Modified` без тела. Так даже маленький сервер выдерживает много посетителей.

### Обновление

```bash
git pull
docker compose -f infra/docker-compose.yml --env-file infra/.env up -d --build
docker compose -f infra/docker-compose.yml --env-file infra/.env run --rm api p3d-api migrate
```

---

## C. Облачные сервисы без своего сервера

**Цель.** Тот же стек на управляемых сервисах.

1. **База — Neon** (neon.tech, есть бесплатный тариф). Создайте проект. Скопируйте
   строку подключения (`postgresql://…?sslmode=require`). API понимает этот формат.
2. **API — Render или Fly.io.** Создайте Web Service из репозитория:
   - Dockerfile: `apps/api/Dockerfile`, корень сборки: `apps/api`;
   - переменные: `DATABASE_URL` = строка Neon, `P3D_CORS_ORIGINS` = адрес сайта,
     `P3D_BUILD_ID` = любой номер версии;
   - проверка здоровья: путь `/health`.
3. **Схема и данные.** На своём компьютере (нужны Python 3.12 и uv):

   ```bash
   cd apps/api
   uv sync
   export DATABASE_URL='postgresql://…?sslmode=require'   # строка Neon
   uv run p3d-api migrate
   uv run p3d-api load ../../data/dataset.tar.gz
   ```

4. **Сайт — Cloudflare Pages, Netlify или Vercel.** Корень: `apps/web`.
   Команда сборки: `npm ci && npm run build`. Папка: `dist`. Переменные:
   `VITE_DATA_MODE=api`, `VITE_API_URL=https://<адрес API>/api/v1`.
   Для адресов сцен (`/e/Fe`) включите SPA-режим: все пути → `index.html`.

**Ожидаемый результат.** Сайт на адресе хостинга читает данные из вашего API.

---

## Мониторинг

- `GET /health` — `{"status":"ok","version":"…"}`. Подключите бесплатный монитор
  (например, UptimeRobot) к этому адресу.
- Логи: `docker compose -f infra/docker-compose.yml --env-file infra/.env logs -f api`.
- Проверка стека в CI: workflow `docker` собирает образы и запускает весь стек на
  тестовом наборе.

## Лицензии данных

Код — MIT. Данные сохраняют лицензии источников: Wikidata (CC0), Википедия
(CC BY-SA 4.0), PubChem (открытые данные NIH), Materials Project (CC BY 4.0). Карточка
каждого соединения показывает источники со ссылками и лицензиями. Подробности —
[docs/data-sources.md](data-sources.md).
