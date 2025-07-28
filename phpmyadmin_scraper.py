#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для авторизации в phpMyAdmin и извлечения данных из таблицы users
Тестовое задание для позиции Python Junior Developer
"""

import requests
from bs4 import BeautifulSoup
import re
import json
from urllib.parse import urljoin, urlparse, parse_qs


class PhpMyAdminScraper:
    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.token = None
        self.db_name = 'testDB'
        self.table_name = 'users'

    def get_login_page(self):
        """Получает страницу авторизации и извлекает токен"""
        try:
            response = self.session.get(f"{self.base_url}/index.php")
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ищем токен в форме авторизации
            token_input = soup.find('input', {'name': 'token'})
            if token_input:
                self.token = token_input.get('value')
                print(f"✓ Токен получен: {self.token[:20]}...")
            else:
                print("⚠ Токен не найден на странице авторизации")
                
            return True
        except Exception as e:
            print(f"❌ Ошибка при получении страницы авторизации: {e}")
            return False

    def login(self):
        """Выполняет авторизацию в phpMyAdmin"""
        if not self.token:
            print("❌ Токен не получен, невозможно выполнить авторизацию")
            return False
            
        login_data = {
            'pma_username': self.username,
            'pma_password': self.password,
            'server': '1',
            'token': self.token
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/index.php",
                data=login_data,
                allow_redirects=True
            )
            response.raise_for_status()
            
            # Проверяем успешность авторизации
            if 'pma_username' in response.text or 'login' in response.url.lower():
                print("❌ Авторизация не удалась")
                return False
            else:
                print("✓ Авторизация выполнена успешно")
                return True
                
        except Exception as e:
            print(f"❌ Ошибка при авторизации: {e}")
            return False

    def navigate_to_database(self):
        """Переходит в базу данных testDB"""
        try:
            # Получаем список баз данных
            response = self.session.get(f"{self.base_url}/index.php")
            response.raise_for_status()
            
            # Переходим в базу данных testDB
            db_url = f"{self.base_url}/index.php?db={self.db_name}"
            response = self.session.get(db_url)
            response.raise_for_status()
            
            print(f"✓ Переход в базу данных {self.db_name} выполнен")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при переходе в базу данных: {e}")
            return False

    def get_table_data(self):
        """Извлекает данные из таблицы users"""
        try:
            # Формируем URL для просмотра таблицы
            table_url = f"{self.base_url}/index.php?db={self.db_name}&table={self.table_name}"
            response = self.session.get(table_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ищем таблицу с данными (используем правильный селектор)
            data_table = soup.find('table', {'class': 'table_results'})
            if not data_table:
                # Альтернативный поиск
                tables = soup.find_all('table')
                for table in tables:
                    if 'table_results' in table.get('class', []):
                        data_table = table
                        break
            
            if not data_table:
                print("❌ Таблица с данными не найдена")
                return None
            
            # Извлекаем заголовки
            headers = []
            header_row = data_table.find('tr')
            if header_row:
                # Ищем заголовки в первой строке
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
            
            if not headers and rows:
                # Если заголовки не найдены, создаем заголовки по количеству колонок
                headers = [f"Колонка {i+1}" for i in range(len(rows[0]))]
            
            return {'headers': headers, 'rows': rows}
            
        except Exception as e:
            print(f"❌ Ошибка при извлечении данных таблицы: {e}")
            return None

    def display_data(self, data):
        """Выводит данные в консоль в читаемом виде"""
        if not data or not data['rows']:
            print("❌ Данные не найдены")
            return
        
        headers = data['headers']
        rows = data['rows']
        
        print("\n" + "="*80)
        print(f"ДАННЫЕ ИЗ ТАБЛИЦЫ {self.table_name.upper()}")
        print("="*80)
        
        # Выводим заголовки
        if headers:
            header_line = " | ".join(headers)
            print(header_line)
            print("-" * len(header_line))
        
        # Выводим данные
        for row in rows:
            row_line = " | ".join(row)
            print(row_line)
        
        print(f"\nВсего записей: {len(rows)}")
        print("="*80)

    def run(self):
        """Основной метод для выполнения всего процесса"""
        print("🚀 Запуск скрипта для извлечения данных из phpMyAdmin")
        print(f"📡 Подключение к: {self.base_url}")
        print(f"👤 Пользователь: {self.username}")
        print(f"🗄️ База данных: {self.db_name}")
        print(f"📋 Таблица: {self.table_name}")
        print("-" * 50)
        
        # Шаг 1: Получение страницы авторизации
        if not self.get_login_page():
            return False
        
        # Шаг 2: Авторизация
        if not self.login():
            return False
        
        # Шаг 3: Переход в базу данных
        if not self.navigate_to_database():
            return False
        
        # Шаг 4: Извлечение данных
        data = self.get_table_data()
        if data:
            self.display_data(data)
            return True
        else:
            return False


def main():
    """Главная функция"""
    # Параметры подключения
    BASE_URL = "http://185.244.219.162/phpmyadmin"
    USERNAME = "test"
    PASSWORD = "JHFBdsyf2eg8*"
    
    # Создаем экземпляр скрапера
    scraper = PhpMyAdminScraper(BASE_URL, USERNAME, PASSWORD)
    
    # Запускаем процесс
    success = scraper.run()
    
    if success:
        print("\n✅ Скрипт выполнен успешно!")
    else:
        print("\n❌ Скрипт завершился с ошибкой!")


if __name__ == "__main__":
    main() 