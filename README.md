# GFP CoreX - Мультитенантная система с плагинами

GFP CoreX - это мультитенантная FastAPI система с изолированными базами данных, Redis и системой плагинов для каждой конфигурации.

## 🚀 Основные возможности

### Мультитенантная архитектура
- **Изолированные конфигурации**: Каждая конфигурация (`dev`, `prod`) имеет свою базу данных и Redis
- **Универсальные API пути**: Все API доступны через `/api/c/{config_name}/api/v1/`
- **Изолированные плагины**: Плагины загружаются и работают независимо для каждой конфигурации

### Система плагинов
- **Горячая перезагрузка**: Плагины перезагружаются автоматически при изменении кода
- **Изоляция по конфигурациям**: Плагины доступны только в своей конфигурации
- **Безопасное выполнение**: Плагины выполняются в изолированной среде
- **API интеграция**: Плагины можно вызывать из других API эндпоинтов

## 📋 Структура проекта

```
GFP CoreX/
├── src/gfpcorex/
│   ├── api/
│   │   ├── plugins.py              # API управления плагинами
│   │   └── plugin_integration.py   # API интеграции плагинов
│   ├── plugins/
│   │   ├── manager.py              # Менеджер плагинов
│   │   └── api.py                  # API для плагинов
│   ├── models/
│   │   ├── plugin.py               # Модель плагина
│   │   ├── user.py                 # Модель пользователя
│   │   └── user_role.py            # Модель роли пользователя
│   └── core/
│       ├── database.py             # Управление БД
│       └── config.py               # Конфигурации
├── configs/
│   ├── dev.yaml                   # Конфигурация dev
│   └── prod.yaml                  # Конфигурация prod
└── scripts/
    ├── create_calculator_plugin.py # Создание плагина-калькулятора
    ├── call_plugin_with_params.py  # Тест вызова плагина
    └── test_multi_config_plugins.py # Тест мультиконфигурации
```

## 🔧 Установка и запуск

### Требования
- Python 3.10+
- MySQL/PostgreSQL
- Redis (опционально)

### Установка
```bash
# Клонирование репозитория
git clone <repository-url>
cd "GFP CoreX"

# Установка зависимостей
poetry install

# Активация виртуального окружения
poetry shell
```

### Запуск
```bash
# Запуск сервера
python -m src.gfpcorex.main
```

Сервер будет доступен по адресу: http://localhost:8000

## 📚 API документация

### Основные эндпоинты

#### Глобальные (без конфигурации)
- `GET /` - Информация о API
- `GET /health` - Проверка здоровья системы
- `GET /docs` - Swagger документация

#### Конфигурационные (с конфигурацией)
- `GET /api/c/{config_name}/api/v1/health` - Проверка конфигурации
- `GET /api/c/{config_name}/api/v1/example` - Пример эндпоинта

### API плагинов

#### Управление плагинами
```bash
# Список плагинов
GET /api/c/{config_name}/api/v1/plugins

# Информация о плагине
GET /api/c/{config_name}/api/v1/plugins/{plugin_name}

# Создание плагина
POST /api/c/{config_name}/api/v1/plugins
{
    "name": "my_plugin",
    "code": "def hello(): return 'Hello, World!'"
}

# Обновление плагина
PUT /api/c/{config_name}/api/v1/plugins/{plugin_name}
{
    "code": "def hello(): return 'Updated Hello!'",
    "is_active": true
}

# Выполнение функции плагина
POST /api/c/{config_name}/api/v1/plugins/{plugin_name}/execute
{
    "function_name": "hello",
    "args": [],
    "kwargs": {}
}

# Перезагрузка плагина
POST /api/c/{config_name}/api/v1/plugins/{plugin_name}/reload

# Удаление плагина
DELETE /api/c/{config_name}/api/v1/plugins/{plugin_name}
```

#### Интеграционные API
```bash
# Калькулятор
POST /api/c/{config_name}/api/v1/plugin-integration/calculate
{
    "plugin_name": "calculator",
    "function_name": "calculate",
    "params": {"operation": "add", "a": 10, "b": 5}
}

# Приветствие
POST /api/c/{config_name}/api/v1/plugin-integration/greet
{
    "plugin_name": "calculator",
    "function_name": "greet",
    "params": {"name": "Иван", "age": 25}
}

# Универсальный API
POST /api/c/{config_name}/api/v1/plugin-integration/custom
{
    "plugin_name": "my_plugin",
    "function_name": "my_function",
    "params": {"param1": "value1"}
}
```

## 🔌 Система плагинов

### Создание плагина

Плагины - это Python код, который выполняется в изолированной среде. Каждый плагин может содержать несколько функций.

#### Пример плагина-калькулятора:
```python
def calculate(operation, a, b):
    """Калькулятор с параметрами"""
    try:
        if operation == 'add':
            result = a + b
        elif operation == 'subtract':
            result = a - b
        elif operation == 'multiply':
            result = a * b
        elif operation == 'divide':
            if b == 0:
                return {"error": "Деление на ноль невозможно"}
            result = a / b
        else:
            return {"error": f"Неизвестная операция: {operation}"}
        
        return {
            "operation": operation,
            "a": a,
            "b": b,
            "result": result,
            "success": True
        }
    except Exception as e:
        return {"error": str(e), "success": False}

def greet(name, age=None):
    """Приветствие с параметрами"""
    if age:
        return {
            "message": f"Привет, {name}! Тебе {age} лет.",
            "name": name,
            "age": age
        }
    else:
        return {
            "message": f"Привет, {name}!",
            "name": name
        }
```

### Изоляция плагинов

Плагины полностью изолированы по конфигурациям:

- **DEV конфигурация**: Плагины доступны только в `/api/c/dev/api/v1/plugins/`
- **PROD конфигурация**: Плагины доступны только в `/api/c/prod/api/v1/plugins/`

Плагины из одной конфигурации недоступны в другой.

### Безопасность

- Плагины выполняются в изолированной среде
- Ограниченный доступ к системным ресурсам
- Валидация входных данных
- Обработка ошибок выполнения

## 🗄️ База данных

### Модели

#### User (Пользователи)
```sql
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    role_id INT DEFAULT 2,
    bio TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES user_roles(id)
);
```

#### UserRole (Роли пользователей)
```sql
CREATE TABLE user_roles (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

#### Plugin (Плагины)
```sql
CREATE TABLE plugins (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL,
    code TEXT NOT NULL,
    hashsum VARCHAR(64) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

#### AuthSession (Сессии аутентификации)
```sql
CREATE TABLE auth_sessions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### Автоматическое создание таблиц

Система автоматически создает таблицы при первом запуске:

1. Проверяет существование таблиц
2. Создает недостающие таблицы из моделей SQLAlchemy
3. Вставляет данные по умолчанию (роли пользователей)

## 🔧 Конфигурации

### Структура конфигурации
```yaml
# configs/dev.yaml
app:
  title: "GFP CoreX Dev"
  version: "1.0.0"

db:
  url: "mysql+aiomysql://user:password@localhost/gfpcorex_dev"
  echo: true

redis:
  url: "redis://localhost:6379/0"
```

### Доступные конфигурации
- `dev` - Конфигурация для разработки
- `prod` - Конфигурация для продакшена

## 🧪 Тестирование

### Тестовые скрипты

```bash
# Создание плагина-калькулятора
python scripts/create_calculator_plugin.py

# Тест вызова плагина с параметрами
python scripts/call_plugin_with_params.py

# Тест интеграционного API
python scripts/test_plugin_integration.py

# Тест мультиконфигурационных плагинов
python scripts/test_multi_config_plugins.py
```

### Примеры curl

```bash
# Создание плагина
curl -X POST "http://localhost:8000/api/c/dev/api/v1/plugins" \
  -H "Content-Type: application/json" \
  -d '{"name": "test", "code": "def hello(): return \"Hello\""}'

# Выполнение функции плагина
curl -X POST "http://localhost:8000/api/c/dev/api/v1/plugins/test/execute" \
  -H "Content-Type: application/json" \
  -d '{"function_name": "hello", "args": [], "kwargs": {}}'

# Интеграционный API
curl -X POST "http://localhost:8000/api/c/dev/api/v1/plugin-integration/custom" \
  -H "Content-Type: application/json" \
  -d '{"plugin_name": "calculator", "function_name": "calculate", "params": {"operation": "add", "a": 10, "b": 5}}'
```

## 📖 Примеры использования

### 1. Создание плагина через API

```python
import requests

# Создание плагина
plugin_code = '''
def calculate(operation, a, b):
    if operation == 'add':
        return a + b
    elif operation == 'multiply':
        return a * b
    else:
        return None
'''

response = requests.post(
    "http://localhost:8000/api/c/dev/api/v1/plugins",
    json={
        "name": "calculator",
        "code": plugin_code
    }
)

print(response.json())
```

### 2. Вызов плагина

```python
import requests

# Вызов функции плагина
response = requests.post(
    "http://localhost:8000/api/c/dev/api/v1/plugins/calculator/execute",
    json={
        "function_name": "calculate",
        "args": [],
        "kwargs": {
            "operation": "add",
            "a": 10,
            "b": 5
        }
    }
)

result = response.json()
print(f"Результат: {result['result']}")
```

### 3. Интеграция в другие API

```python
import requests

# Вызов через интеграционный API
response = requests.post(
    "http://localhost:8000/api/c/dev/api/v1/plugin-integration/custom",
    json={
        "plugin_name": "calculator",
        "function_name": "calculate",
        "params": {
            "operation": "multiply",
            "a": 7,
            "b": 8
        }
    }
)

result = response.json()
print(f"Результат: {result['result']}")
```

## 🔒 Безопасность

### Аутентификация и авторизация
- JWT токены для аутентификации
- Роли пользователей (admin, user)
- Сессии с автоматическим истечением

### Изоляция данных
- Каждая конфигурация имеет свою базу данных
- Плагины изолированы по конфигурациям
- Безопасное выполнение кода плагинов

## 🚀 Развертывание

### Docker Compose
```bash
# Запуск всех сервисов
docker-compose up -d

# Просмотр логов
docker-compose logs -f
```

### Продакшен
```bash
# Использование продакшен конфигурации
export CONFIG_NAME=prod
python -m src.gfpcorex.main
```

## 📝 Лицензия

MIT License

## 🤝 Вклад в проект

1. Fork репозитория
2. Создайте feature branch
3. Внесите изменения
4. Добавьте тесты
5. Создайте Pull Request

## 📞 Поддержка

Для вопросов и поддержки создавайте Issues в репозитории.

