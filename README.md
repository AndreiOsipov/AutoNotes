# AutoNotes
AutoNotes — нейросервис для конспектирования видео. 

## Содержание
- [О проекте](#о-проекте)
- [Основные возможности](#основные-возможности)
- [Быстрый старт](#быстрый-старт)
- [Структура проекта](#структура-проекта)

## О проекте
AutoNotes превращает видеоролики (лекции) в структурированные конспекты.

Сервис использует современные алгоритмы распознавания речи, текста на изображении и обработки естественного языка, чтобы выделить главное и сократить время на просмотр.

AutoNotes идеально заточен под студентов, исследователей, преподавателей и всех, кто учится или работает с видеоуроками, лекциями и интервью.

## Основные возможности
 - Автоматическое распознавание речи и составление текста.
 - Генерация краткого конспекта и тезисов по видео.
 - Таймкоды с переходом к нужному фрагменту.
 - Возможность экспорта в PDF или Markdown.

## Быстрый старт
1. Клонирование репозитория
```bash   
git clone [https://github.com/AndreiOsipov/AutoNotes.git](https://github.com/AndreiOsipov/AutoNotes.git)
cd AutoNotes
```
2. Настройка окружения
Создайте файл .env на основе примера:
```bash
cp .env.example .env
```
3. Установка зависимостей
```bash
python3 -m venv venv
source venv/bin/activate  # Для Windows: venv\Scripts\activate
pip install -r requirements.txt
```
4. Запуск тестов
Чтобы убедиться, что всё настроено верно:
```bash
PYTHONPATH=. pytest
```

## Структура проекта
```
AutoNotes/
│ 
├── .github/workflows/                # CI/CD конфигурации GitHub Actions
│   └── ci.yml
│ 
├── certs/                            # SSL/TLS сертификаты и ключи
│
├── src/                              # Основной исходный код приложения
│   │
│   ├── api/                          # Слой API (маршруты, зависимости, конфигурация FastAPI)
│   │   │
│   │   ├── routers/                  # API роутеры/эндпоинты
│   │   │   ├── __init__.py
│   │   │   ├── auth.py/
│   │   │   └── rest.py
│   │   │
│   │   ├── __init__.py
│   │   ├── constants.py
│   │   ├── dependencies.py
│   │   ├── router.py
│   │   └── tags.py
│   │
│   ├── core/                         # Ядро приложения и базовая логика
│   │   ├── __init__.py
│   │   ├── exceptions.py
│   │   ├── security.py
│   │   ├── settings.py
│   │   └── tokens.py
│   │
│   ├── db/                           # Работа с базой данных
│   │   ├── __init__.py
│   │   ├── database.py
│   │   └── db_manager.py
│   │
│   ├── models/                       # ORM модели базы данных
│   │   ├── __init__.py
│   │   ├── reviews.py
│   │   ├── users.py
│   │   └── videos.py
│   │  
│   ├── NotesSynchronizer/            # Модуль синхронизации конспекта
│   │   └── notes_synchronizer.py
│   │
│   ├── repositories/                 # Слой доступа к данным (Repository pattern)
│   │   ├── __init__.py
│   │   └── repositories.py
│   │
│   ├── schemas/                      # Pydantic-схемы для валидации данных
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── user.py
│   │ 
│   ├── services/                     # Бизнес-логика приложения
│   │   ├── __init__.py
│   │   ├── services.py
│   │   └── video_service.py
│   │ 
│   ├── subtitles/                    # Работа с субтитрами, аудио и текстом
│   │   ├── dir_audio/
│   │   ├── dir_text/
│   │   ├── dir_txt/
│   │   ├── dit_video/
│   │   ├── parsed_images/
│   │   ├── __init__.py
│   │   └── subtitles.py
│   │ 
│   ├── utils/                        # Вспомогательные утилиты и хелперы
│   │   ├── __init__.py
│   │   └── utils.py
│   │ 
│   ├── __init__.py
│   └── main.py
│
├── tests/                            # Тесты проекта
│   │ 
│   ├── unit/                         # Unit-тесты
│   │   ├── test_users_router.py
│   │   └── test_video_transcription.py
│   │ 
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_db.py
│   └── test_notes_synchronizer.py
│ 
├── .env.example
├── .gitignore
├── .python-version
├── LICENSE
├── pyproject.toml
├── README.md
├── requirements.txt
└── uv.lock
```
 - 📁 .github/ 📁 workflows/ — конфигурации GitHub Actions;
 - ci.yml — конфигурация continuous integration;
 - 📁 NotesSynchronizer/ — директория по синхронизации транскрипций;
 - notes_synchronizer.py — модуль по синхронизации транскрипций;
 - 📁 config/ — директория для глобальной настройки проекта и валидация .env;
 - config.py — модуль для глобальныой настройки проекта и валидация .env;
 - 📁 subtitles/ — модуль глубокого анализа медиаконтента;
 - 📁 dir_audio/ — временное хранилище извлеченных звуковых дорожек;
 - 📁 dir_txt/ — промежуточные текстовые результаты транскрипции;
 - 📁 dit_video/ — кэш загруженных видеофайлов;
 - 📁 parsed_images/ — кадры, извлеченные из видео для анализа контента;
 - subtitles.py — реализует интеллектуальную обработку видео через три типа нейросетей;
 - 📁 tests/ — инфраструктура тестирования;
 - 📁 unit/ — изолированные тесты отдельных модулей (API, логика);
 - test_users_router.py — модуль юнит тестов ручек авторизации;
 - test_video_transcription.py — модуль юнит тестов транскрипций;
 - conftest.py — модуль создания глобальных фикстур для тестов;
 - test_db.py — модуль создания тестовой базы данных;
 - test_notes_synchronizer.py — модуль тестов синхронизации транскрипции;
 - 📁 users/ — управление пользователями, JWT-авторизация и роутинг;
 - users_router.py — модуль роутеров для users;
 - users.py — модуль логики работы с пользователем;
 - 📁 utils/ — директория вспомогательных утилит (логирования, форматтеров);
 - utils.py — модуль где вспомогательные утилиты (логирование, форматтеры);
 - .env — файл с секретами - обязательно добавить в .gitignore;
 - .env.example — файл с примерами секретов для удалённого репозитория;
 - .gitignore — для исключения временных/лишних файлов (рекомендуется);
 - db.py — инициализация SQLModel, описание таблиц и связей;
 - main.py — основной скрипт (исполняемый файл);
 - requirements.txt — зависимости (опционально).
