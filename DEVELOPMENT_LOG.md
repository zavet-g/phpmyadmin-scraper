# Журнал разработки phpMyAdmin Scraper

## Введение

Этот документ описывает мой процесс разработки скрипта для авторизации в phpMyAdmin и извлечения данных из таблицы users.

## Анализ требований

### Что требовалось сделать:
1. Написать Python-скрипт для авторизации в phpMyAdmin
2. Извлечь данные из таблицы `users` в базе данных `testDB`
3. Вывести данные в консоль в читаемом виде

### Ограничения:
- Запрещено использовать Selenium, Playwright
- Нельзя подключаться напрямую к MySQL
- Все действия через HTTP-запросы

### Параметры подключения:
- URL: http://185.244.219.162/phpmyadmin
- Логин: test
- Пароль: JHFBdsyf2eg8*

## Этап 1: Планирование архитектуры

Я решил создать объектно-ориентированный подход с классом `PhpMyAdminScraper`. Это позволило бы:
- Инкапсулировать логику работы с сессией
- Разделить функциональность на методы
- Легко тестировать и поддерживать код

### Структура класса:
```python
class PhpMyAdminScraper:
    - __init__() - инициализация параметров
    - get_login_page() - получение токена авторизации
    - login() - выполнение авторизации
    - navigate_to_database() - переход в базу данных
    - get_table_data() - извлечение данных таблицы
    - display_data() - вывод результатов
    - run() - основной метод
```

## Этап 2: Реализация базовой функциональности

### Шаг 1: Настройка окружения
Сначала я создал `requirements.txt` с необходимыми зависимостями:
```
requests==2.31.0
beautifulsoup4==4.12.2
```

Изначально добавил `lxml==4.9.3`, но при тестировании столкнулся с проблемами компиляции на Windows. Убрал эту зависимость, так как `html.parser` из стандартной библиотеки работает достаточно хорошо.

### Шаг 2: Создание класса скрапера
Я начал с базовой структуры:

```python
class PhpMyAdminScraper:
    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        # Настройка User-Agent для имитации браузера
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...'
        })
        self.token = None
```

### Шаг 3: Реализация авторизации
Самый важный этап - получение токена безопасности и авторизация:

```python
def get_login_page(self):
    response = self.session.get(f"{self.base_url}/index.php")
    soup = BeautifulSoup(response.text, 'html.parser')
    token_input = soup.find('input', {'name': 'token'})
    self.token = token_input.get('value')
```

```python
def login(self):
    login_data = {
        'pma_username': self.username,
        'pma_password': self.password,
        'server': '1',
        'token': self.token
    }
    response = self.session.post(f"{self.base_url}/index.php", data=login_data)
```

## Этап 3: Первые проблемы и их решение

### Проблема 1: Неправильный поиск таблицы
Изначально я искал таблицу так:
```python
data_table = soup.find('table', {'id': 'table_results'})
```

Но при тестировании обнаружил, что таблица имеет класс `table_results`, а не ID.

### Проблема 2: Неправильное извлечение данных
Первая версия извлекала все ячейки, включая кнопки действий:
```
DeleteDELETE FROM `users` WHERE `users`.`id` = 2 | 2 | Пётр
```

### Решение: Улучшение логики поиска таблицы

Я создал отладочный скрипт `debug_scraper.py` для анализа структуры HTML:

```python
def debug_phpmyadmin():
    # ... код для анализа всех таблиц на странице
    tables = soup.find_all('table')
    for i, table in enumerate(tables):
        print(f"Таблица {i+1}:")
        print(f"ID: {table.get('id', 'Нет ID')}")
        print(f"Class: {table.get('class', 'Нет класса')}")
```

Результат анализа показал:
- Таблица с данными имеет класс `table_results`
- Данные находятся в строках после заголовков
- Кнопки действий нужно фильтровать

### Улучшенная логика извлечения данных:

```python
# Ищем таблицу с данными (используем правильный селектор)
data_table = soup.find('table', {'class': 'table_results'})
if not data_table:
    # Альтернативный поиск
    tables = soup.find_all('table')
    for table in tables:
        if 'table_results' in table.get('class', []):
            data_table = table
            break

# Извлекаем заголовки
header_row = data_table.find('tr')
if header_row:
    header_cells = header_row.find_all(['th', 'td'])
    headers = []
    for cell in header_cells:
        text = cell.get_text(strip=True)
        if text and text not in ['Edit', 'Copy', 'Delete']:
            headers.append(text)

# Извлекаем данные (пропускаем первую строку с заголовками)
rows = []
data_rows = data_table.find_all('tr')[1:]  # Пропускаем заголовки

for row in data_rows:
    cells = row.find_all(['td', 'th'])
    row_data = []
    for cell in cells:
        text = cell.get_text(strip=True)
        # Пропускаем кнопки действий и SQL-запросы
        if text and text not in ['Edit', 'Copy', 'Delete'] and not text.startswith('DELETE FROM'):
            # Очищаем текст от лишних символов
            clean_text = text.replace('DeleteDELETE FROM `users` WHERE `users`.`id` = ', '')
            if clean_text and clean_text != text:  # Если был очищен
                continue  # Пропускаем эту ячейку
            row_data.append(text)
    
    if row_data:  # Добавляем только строки с данными
        rows.append(row_data)
```

## Этап 4: Тестирование и финальная отладка

### Первый запуск:
```
❌ Данные не найдены
```

### После отладки:
```
================================================================================
ДАННЫЕ ИЗ ТАБЛИЦЫ USERS
================================================================================
id | name1
----------
1 | Иван
2 | Пётр  
3 | Василий
4 | Алексей

Всего записей: 4
================================================================================
```

## Этап 5: Оптимизация и документация

### Упрощение зависимостей
Убрал `lxml` из requirements.txt, оставив только:
```
requests==2.31.31.0
beautifulsoup4==4.12.2
```

### Создание документации
- `README.md` - инструкции по использованию
- `DEVELOPMENT_LOG.md` - этот журнал разработки
- `.gitignore` - исключения для Git

## Ключевые решения и находки

### 1. Правильный поиск таблицы
Изначально искал по ID, но оказалось, что нужно искать по классу `table_results`.

### 2. Фильтрация данных
Важно было отфильтровать кнопки действий и SQL-запросы из данных.

### 3. Обработка заголовков
Заголовки находятся в первой строке таблицы, но нужно исключить кнопки действий.

### 4. Сессионное управление
Использование `requests.Session()` позволило сохранять cookies между запросами.

## Заключение

Скрипт успешно выполняет все требования задания:
-  Авторизация в phpMyAdmin через HTTP-запросы
-  Извлечение данных из таблицы users
-  Вывод в читаемом формате
-  Соблюдение всех ограничений


