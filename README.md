# GFP CoreX - Multi-Configuration FastAPI Backend

Production-ready мультиконфигурационный FastAPI-бэкенд с Docker поддержкой.

## 🚀 Особенности

- **Мультиконфигурационная архитектура**: Изолированные конфигурации с разными БД/Redis
- **URL-шаблон**: `http://gfp.com/api/c/{config_name}/api/v1/...`
- **Динамическая загрузка**: Конфигурации загружаются из YAML файлов
- **Docker-ready**: Полная поддержка Docker и Docker Compose
- **Production-ready**: Готов к развертыванию в продакшене

## 📁 Структура проекта

```
GFP CoreX/
├── configs/                 # Конфигурационные файлы
│   ├── prod.yaml           # Production конфигурация
│   ├── dev.yaml            # Development конфигурация
│   └── test.yaml           # Test конфигурация
├── src/gfpcorex/
│   ├── core/               # Основные модули
│   │   ├── config.py       # Система конфигураций
│   │   ├── database.py     # Управление БД
│   │   └── redis.py        # Управление Redis
│   ├── api/
│   │   └── dynamic/        # Динамические роутеры
│   │       └── router.py   # Основной роутер
│   └── main.py             # Главное приложение
├── docker/
├── scripts/                # Скрипты развертывания
├── Dockerfile              # Docker образ
├── docker-compose.yml      # Docker Compose
└── pyproject.toml         # Зависимости
```

## 🛠 Установка и запуск

### Локальная разработка

1. **Клонируйте репозиторий**:
```bash
git clone <repository-url>
cd gfp-corex
```

2. **Установите зависимости**:
```bash
poetry install
```

3. **Настройте базу данных**:
```bash
# Запустите PostgreSQL и Redis локально
# Или используйте Docker Compose
docker-compose up -d postgres redis
```

4. **Запустите приложение**:
```bash
poetry run python -m src.gfpcorex.main
```

### Docker развертывание

1. **Запустите все сервисы**:
```bash
docker-compose up -d
```

2. **Проверьте статус**:
```bash
docker-compose ps
```

3. **Просмотрите логи**:
```bash
docker-compose logs -f app
```

## 🔧 Конфигурация

### Структура конфигурационного файла

```yaml
# configs/prod.yaml
db:
  url: "postgresql+asyncpg://user:pass@postgres:5432/prod_db"
  pool_size: 20
  max_overflow: 30

redis:
  url: "redis://redis:6379/1"
  pool_size: 10

auth:
  secret_key: "ENCRYPTED_KEY"
  algorithm: "HS256"

app:
  title: "GFP CoreX Production"
  debug: false
```

### Добавление новой конфигурации

1. Создайте новый файл в `configs/`:
```bash
cp configs/dev.yaml configs/my-config.yaml
```

2. Отредактируйте настройки в `configs/my-config.yaml`

3. Перезапустите приложение

## 🌐 API Endpoints

### Основные endpoints

- `GET /` - Информация о приложении
- `GET /health` - Глобальная проверка здоровья
- `GET /docs` - Swagger документация
- `GET /redoc` - ReDoc документация

### Конфигурационные endpoints

Для каждой конфигурации доступны:

- `GET /api/c/{config_name}/api/v1/health` - Проверка здоровья конфигурации
- `GET /api/c/{config_name}/api/v1/example` - Пример endpoint

### Примеры запросов

```bash
# Получить информацию о приложении
curl http://localhost:8000/

# Проверить здоровье production конфигурации
curl http://localhost:8000/api/c/prod/api/v1/health

# Получить пример данных из development конфигурации
curl http://localhost:8000/api/c/dev/api/v1/example
```

## 🔐 Безопасность

### TODO: Настройки безопасности

1. **Секретные ключи**: Замените `ENCRYPTED_KEY` на реальные секреты
2. **CORS**: Настройте разрешенные домены в конфигурациях
3. **Rate Limiting**: Настройте лимиты запросов
4. **SSL/TLS**: Настройте HTTPS в продакшене

### Переменные окружения

```bash
# Production
export GFP_SECRET_KEY="your-super-secret-key"
export GFP_DB_URL="postgresql+asyncpg://user:pass@host:5432/db"
export GFP_REDIS_URL="redis://host:6379/1"
```

## 📊 Мониторинг

### Health Checks

- `GET /health` - Глобальная проверка
- `GET /api/c/{config}/api/v1/health` - Проверка конфигурации

### Логирование

Настройте логирование в конфигурациях:

```yaml
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  format: "json"  # text, json
  handlers: ["console", "file"]
```

## 🐳 Docker

### Сборка образа

```bash
docker build -t gfp-corex .
```

### Запуск с Docker Compose

```bash
# Разработка
docker-compose up

# Продакшен (с Nginx)
docker-compose --profile production up -d
```

### Переменные окружения в Docker

```yaml
# docker-compose.yml
environment:
  - GFP_SECRET_KEY=${GFP_SECRET_KEY}
  - GFP_DB_URL=${GFP_DB_URL}
  - GFP_REDIS_URL=${GFP_REDIS_URL}
```

## 🧪 Тестирование

### Запуск тестов

```bash
# Установите dev зависимости
poetry install --with dev

# Запустите тесты
poetry run pytest

# С покрытием
poetry run pytest --cov=src
```

### Тестовые конфигурации

Используйте `configs/test.yaml` для тестирования:

```bash
# Запустите тестовую конфигурацию
curl http://localhost:8000/api/c/test/api/v1/health
```

## 📈 Производительность

### Настройки пулов соединений

```yaml
db:
  pool_size: 20        # Размер пула БД
  max_overflow: 30     # Максимальное переполнение

redis:
  pool_size: 10        # Размер пула Redis
```

### Мониторинг производительности

- Используйте `echo: true` в development для логирования SQL
- Настройте метрики в продакшене
- Мониторьте использование памяти и CPU

## 🔄 Развертывание

### Production развертывание

1. **Подготовьте сервер**:
```bash
# Установите Docker и Docker Compose
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

2. **Настройте переменные окружения**:
```bash
export GFP_SECRET_KEY="your-production-secret"
export GFP_DB_URL="postgresql+asyncpg://prod_user:prod_pass@prod_host:5432/prod_db"
export GFP_REDIS_URL="redis://prod_redis:6379/1"
```

3. **Запустите приложение**:
```bash
docker-compose --profile production up -d
```

### CI/CD Pipeline

```yaml
# .github/workflows/deploy.yml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to production
        run: |
          docker-compose --profile production up -d
```

## 🐛 Troubleshooting

### Частые проблемы

1. **Ошибка подключения к БД**:
   - Проверьте настройки в конфигурации
   - Убедитесь, что PostgreSQL запущен
   - Проверьте права доступа пользователя

2. **Ошибка подключения к Redis**:
   - Проверьте настройки Redis
   - Убедитесь, что Redis запущен
   - Проверьте доступность порта

3. **Конфигурация не найдена**:
   - Проверьте наличие файла в `configs/`
   - Убедитесь в правильности YAML синтаксиса
   - Проверьте логи приложения

### Логи

```bash
# Просмотр логов приложения
docker-compose logs -f app

# Просмотр логов БД
docker-compose logs -f postgres

# Просмотр логов Redis
docker-compose logs -f redis
```

## 📝 TODO

### Кастомные настройки

- [ ] Настройте реальные секретные ключи
- [ ] Настройте CORS для ваших доменов
- [ ] Добавьте аутентификацию и авторизацию
- [ ] Настройте rate limiting
- [ ] Добавьте метрики и мониторинг
- [ ] Настройте SSL/TLS сертификаты
- [ ] Добавьте backup стратегию для БД
- [ ] Настройте логирование в файлы
- [ ] Добавьте алерты и уведомления

### Дополнительные функции

- [ ] Добавьте GraphQL поддержку
- [ ] Реализуйте WebSocket endpoints
- [ ] Добавьте поддержку Webhooks
- [ ] Реализуйте кэширование на уровне приложения
- [ ] Добавьте поддержку очередей задач
- [ ] Реализуйте API версионирование

## 📄 Лицензия

MIT License - см. файл LICENSE для деталей.

## 🤝 Вклад в проект

1. Fork репозиторий
2. Создайте feature branch (`git checkout -b feature/amazing-feature`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в branch (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## 📞 Поддержка

- Создайте Issue в GitHub
- Напишите на email: fealx15@gmail.com
- Документация: `/docs` endpoint в приложении

