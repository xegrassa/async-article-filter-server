# Фильтр желтушных новостей

[Установите проект и зависимости](#как-установить).
Для работы требуется версия Python 3.8 +
Для установки пакетов рекомендуется создать виртуальное окружение.
После [запустите сервер](#как-запустить) который будет принимать список URL статей которые нужно проверить на желтушность.

```Пример запроса к серверу: http://0.0.0.0:8001?urls=https://ya.ru,https://google.com```

**Сервер в ответ на запросы присылает JSON с отчетом анализа статей:**
```json
[
 {"status": "PARSING_ERROR", "url": "http://example.com", "score": null, "words_count": null},
 {"status": "OK", "url": "https://inosmi.ru/politic/20190629/245376799.html", "score": 0.39, "words_count": 5452},
 {"status": "OK", "url": "https://inosmi.ru/politic/20190629/245379332.html", "score": 0.54, "words_count": 9727}
]
```
Пока поддерживается только один новостной сайт - [ИНОСМИ.РУ](https://inosmi.ru/). Для него разработан специальный адаптер, умеющий выделять текст статьи на фоне остальной HTML разметки. Для других новостных сайтов потребуются новые адаптеры, все они будут находиться в каталоге `adapters`. Туда же помещен код для сайта ИНОСМИ.РУ: `adapters/inosmi_ru.py`.

В перспективе можно создать универсальный адаптер, подходящий для всех сайтов, но его разработка будет сложной и потребует дополнительных времени и сил.
***
# Как установить
```
git clone https://github.com/xegrassa/async-article-filter-server.git
cd async-article-filter-server
pip install -r requirements.txt
```
***
# Как запустить

```python3
python script\server.py
```
***
# Как запустить тесты

Для тестирования используется [pytest](https://docs.pytest.org/en/latest/), тестами покрыты фрагменты кода сложные
в отладке. Тесты лежат в каталоге `tests` Команды для запуска тестов

#### Для запуска всех тестов
```
python -m pytest tests
```

#### Для отдельных запусков теста
```
python -m pytest tests/ИМЯ_МОДУЛЯ_ДЛЯ_ТЕСТОВ
```
***
# Цели проекта

Код написан в учебных целях. Это урок из курса по веб-разработке — [Девман](https://dvmn.org).
