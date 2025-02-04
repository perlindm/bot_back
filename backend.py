from flask import Flask, request, jsonify
import requests
from flask_cors import CORS
import os
from dotenv import load_dotenv
import logging
from datetime import datetime

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Создаем Flask
app = Flask(__name__)
CORS(app)

# API-ключи
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
if not RAPIDAPI_KEY:
    logging.error("API-ключ не найден. Установите RAPIDAPI_KEY в .env")
    exit(1)

RAPIDAPI_HOST = "skyscanner89.p.rapidapi.com"
FLIGHTS_URL = f"https://{RAPIDAPI_HOST}/flights/one-way/list"
IATA_URL = f"https://{RAPIDAPI_HOST}/airports/auto-complete"

HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": RAPIDAPI_HOST
}

# 🔹 Функция конвертации города в IATA-код
def get_iata_code(city):
    params = {"query": city}
    response = requests.get(IATA_URL, headers=HEADERS, params=params)
    
    if response.status_code == 200:
        data = response.json()
        if data and isinstance(data, list) and len(data) > 0:
            return data[0]["iata"]  # Берём первый аэропорт
        else:
            logging.warning(f"Город '{city}' не найден в базе аэропортов.")
            return None
    else:
        logging.error(f"Ошибка API при получении IATA-кода: {response.text}")
        return None

@app.route('/')
def home():
    return "Welcome to Travel Helper! Use /search-flights to find flights."

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200

@app.route('/search-flights', methods=['GET'])
def search_flights():
    try:
        # Получаем параметры запроса
        city_from = request.args.get('origin', "").strip()
        city_to = request.args.get('destination', "").strip()
        date = request.args.get('date', "").strip()

        # Проверяем обязательные параметры
        if not city_from or not city_to or not date:
            return jsonify({"error": "Необходимо указать origin, destination и date"}), 400

        # Конвертация городов в IATA-коды
        origin = get_iata_code(city_from) if len(city_from) > 3 else city_from.upper()
        destination = get_iata_code(city_to) if len(city_to) > 3 else city_to.upper()

        if not origin or not destination:
            return jsonify({"error": "Не удалось определить IATA-коды для городов"}), 400

        # Проверяем формат даты
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "Неверный формат даты. Используйте YYYY-MM-DD (например, 2023-12-01)."}), 400

        # Логируем запрос
        logging.info(f"Поиск билетов: {origin} → {destination} ({date})")

        # Формируем параметры запроса
        querystring = {
            "origin": origin,
            "destination": destination,
            "date": date,
            "adults": "1",
            "currency": "USD"
        }

        # Отправляем запрос к Skyscanner API
        response = requests.get(FLIGHTS_URL, headers=HEADERS, params=querystring)

        # Проверяем статус ответа
        if response.status_code == 429:  # Too Many Requests
            logging.error("Превышен лимит запросов к API")
            return jsonify({"error": "Превышен лимит запросов. Попробуйте позже."}), 429

        if response.ok:
            data = response.json()
            if "flights" in data:
                return jsonify(data)
            else:
                logging.error(f"API вернул ошибку: {data}")
                return jsonify({"error": "Ошибка в данных API"}), 500
        else:
            error_data = response.json()
            error_message = error_data.get("message", "Ошибка API")
            logging.error(f"Ошибка API: {response.status_code}, {error_message}, Заголовки: {HEADERS}, Параметры: {querystring}")
            return jsonify({"error": error_message}), response.status_code

    except Exception as e:
        logging.exception("Внутренняя ошибка сервера")
        return jsonify({"error": "Внутренняя ошибка сервера"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
