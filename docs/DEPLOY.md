# Запуск и деплой

Документ описывает три способа запустить проект и локальную разработку. Выберите нужный.

| Способ | Что получаете | Цена | Сложность |
| --- | --- | --- | --- |
| A. GitHub Pages (уже работает) | Сайт со статическими данными | Бесплатно | Ничего делать не нужно |
| B. Свой сервер + Docker Compose | Сайт + живой API + PostgreSQL | VPS от ~5 $/мес | Средняя |
| C. Облачные сервисы без своего сервера | То же, что B | Бесплатные тарифы на старте | Средняя |
| D. Локальная разработка | Сайт на своём компьютере | Бесплатно | Средняя |

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
`ci`. Он проверяет код, собирает сайт, экспортирует данные и публикует сайт.

**Пояснение.** Набор данных для сайта задаёт файл `data/DATASET`:

- `release:data-2026.10.11-r25` — релиз GitHub с полным набором;
- `ci-results:data/latest` — последний тестовый срез (если файла нет).

Слой предсказанных материалов GNoME задаёт файл `data/GNOME`
(`release:gnome-<версия>`; `none` — без слоя).

**Ожидаемый результат.** Через 6–10 минут после push сайт показывает новую версию.

### Как включить публикацию через GitHub Actions (один раз)

**Цель.** Показать на сайте предсказанные материалы GNoME (ADR 0007).

**Команды.**

1. Откройте https://github.com/vik753/periodic-3d/settings/pages .
2. В блоке **Build and deployment** найдите поле **Source**.
3. Выберите **GitHub Actions** вместо **Deploy from a branch**.
4. Ничего больше не меняйте. Изменение сохраняется сразу.
5. Откройте **Actions** → workflow **ci** → **Run workflow** → **Run workflow**.

**Пояснение.** С GNoME сайт весит около 630 МБ и содержит около 95 000 файлов. Ветка
`gh-pages` для этого не подходит: каждый деплой добавлял бы сотни мегабайт в git.
Workflow `ci` сам проверяет настройку Pages. Пока стоит ветка, он публикует сайт без
GNoME. После переключения он загружает сайт артефактом, а задача `pages` публикует его.

**Ожидаемый результат.** В запуске `ci` задачи `pages` и `live demo` зелёные. На сайте
у элементов появляется переключатель «+ предсказанные».

> **Теория: два способа публикации GitHub Pages.** «Deploy from a branch»: GitHub берёт
> файлы из ветки (`gh-pages`) и сам собирает сайт. Каждая публикация — коммит, история
> растёт. «GitHub Actions»: workflow собирает папку сайта и загружает её как артефакт
> (`actions/upload-pages-artifact`), затем `actions/deploy-pages` публикует артефакт.
> Git не хранит собранные файлы, лимит сайта — 1 ГБ. Это рекомендуемый способ для
> больших сайтов и для сайтов, которые собираются в CI.

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

### Как перезаписать видео «Как пользоваться»

**Цель.** Записать новое видео после изменений интерфейса.

**Команды.**

1. Откройте **Actions** → workflow **guide** → **Run workflow**.
2. Оставьте `languages` = `uk,ru,en`, `fps` = `30`, `release` выключенным.
3. Нажмите **Run workflow** и дождитесь конца (около 40 минут).
4. Посмотрите видео: ветка `ci-results`, папка `guide/<язык>/` (файл `guide-<язык>.mp4`
   и кадры каждые 4 секунды).
5. Если видео в порядке: снова **Run workflow**, включите `release`, в `from_run`
   впишите номер (ID) проверенного запуска из адресной строки.

**Пояснение.** Сценарий записи — `apps/web/scripts/guide-video.mjs`. Он открывает живой
сайт, замораживает часы страницы и снимает кадр за кадром: в CI нет видеокарты, но видео
получается плавным. Подписи и курсор рисует `guide-overlay.js`. Не публикуйте сайт во
время записи: новые файлы сайта заменят старые, и запись может сломаться. С `release`
workflow публикует релиз `guide-<версия>`, записывает его в `data/GUIDE` и запускает `ci`;
сборка сайта кладёт видео в папку `guide/`.

**Ожидаемый результат.** В окне «Как пользоваться» появляется кнопка «Дивитися відео».
Видео открывается поверх главного экрана. Образ Docker видео не содержит: кнопка там
скрыта.

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
gh release download data-2026.10.11-r25 --repo vik753/periodic-3d --pattern 'dataset-*.tar.gz' --output data/dataset.tar.gz
docker compose -f infra/docker-compose.yml --env-file infra/.env run --rm -v "$PWD/data:/data" api \
  p3d-api load /data/dataset.tar.gz
```

**Пояснение.** Без `gh` скачайте архив со страницы **Releases** в браузере и положите
его в `data/dataset.tar.gz`. Загрузка заменяет старые данные одной транзакцией: сайт
работает и во время загрузки.

**Ожидаемый результат.** Строка `loaded <версия>: 118 elements, … compounds …`.

Предсказанные материалы GNoME (необязательно, около 1 ГБ в базе):

```bash
# Номер релиза — в файле data/GNOME (после "release:")
gh release download gnome-2026.10.11-r2 --repo vik753/periodic-3d --pattern 'gnome-*.tar.gz' --output data/gnome.tar.gz
docker compose -f infra/docker-compose.yml --env-file infra/.env run --rm -v "$PWD/data:/data" api \
  p3d-api load-gnome /data/gnome.tar.gz
```

**Ожидаемый результат.** Строка `loaded gnome-<версия>: 554054 materials, 3403 pairs, 83 elements`.
Загрузка идёт 3–6 минут. Лицензия данных GNoME — CC BY-NC 4.0: сайт с ними должен
оставаться некоммерческим.

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

## D. Локальная разработка

**Цель.** Менять код сайта и сразу видеть результат на своём компьютере.

**Требования.** Node.js 22, Docker с Docker Compose, Git.

**Команды.**

```bash
git clone https://github.com/vik753/periodic-3d.git
cd periodic-3d
cp infra/.env.example infra/.env
# 1. База и API (шаги 2–4 способа B): контейнеры db, api, web и данные в базе.
docker compose -f infra/docker-compose.yml --env-file infra/.env up -d --build
docker compose -f infra/docker-compose.yml --env-file infra/.env run --rm api p3d-api migrate
mkdir -p data
gh release download "$(sed 's/^release://' data/DATASET)" --repo vik753/periodic-3d \
  --pattern 'dataset-*.tar.gz' --output data/dataset.tar.gz
docker compose -f infra/docker-compose.yml --env-file infra/.env run --rm -v "$PWD/data:/data" api \
  p3d-api load /data/dataset.tar.gz
# 2. Сайт в режиме разработки, данные из локального API.
cd apps/web
npm ci
VITE_DATA_MODE=api VITE_API_URL=http://localhost:8080/api/v1 npm run dev
```

**Пояснение.** Vite открывает сайт на `http://localhost:5173/` и
перезагружает его при каждом сохранении файла. Без API можно работать со статикой:
выгрузите ответы API в папку `public/data` и запустите `npm run dev` без переменных.

```bash
docker compose -f infra/docker-compose.yml --env-file infra/.env run --rm \
  -v "$PWD/apps/web/public:/out" api p3d-api export-static /out/data
```

**Проверки перед push** (то же делает CI):

```bash
cd apps/web && npm run typecheck && npm run lint && npm test && npm run build
# Тестам API нужна отдельная PostgreSQL с pgvector (порт 5433, чтобы не мешать другим базам):
docker run -d --name p3d-test -e POSTGRES_PASSWORD=test -p 5433:5432 pgvector/pgvector:pg17
cd ../api && uv sync && uv run ruff check src tests && uv run ruff format --check src tests
uv run mypy && TEST_DATABASE_URL=postgresql://postgres:test@localhost:5433/postgres uv run pytest -q
cd ../../pipeline && uv sync && uv run ruff check src tests && uv run mypy && uv run pytest -q
```

**Ожидаемый результат.** Сайт работает локально; все проверки зелёные.

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
каждого соединения показывает источники со ссылками и лицензиями. Страница «О проекте»
(`/about`, кнопка «i» вверху справа) перечисляет все источники. Данные GNoME
(CC BY-NC) не используются. Подробности — [docs/data-sources.md](data-sources.md).
