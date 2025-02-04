from flask import Flask, request, jsonify
import requests
from flask_cors import CORS
import os
from dotenv import load_dotenv
import logging
import sys
from datetime import datetime

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Создаем Flask
app = Flask(__name__)
CORS(app)

# Получаем API-ключ
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
if not RAPIDAPI_KEY:
    logging.error("API-ключ не найден. Установите RAPIDAPI_KEY в .env")
    sys.exit(1)

RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "skyscanner89.p.rapidapi.com")
BASE_URL = f"https://{RAPIDAPI_HOST}/flights/one-way/list"

headers = {
    'x-rapidapi-key': RAPIDAPI_KEY,
    'x-rapidapi-host': RAPIDAPI_HOST
}

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
        origin = request.args.get('origin', "").upper()
        destination = request.args.get('destination', "").upper()
        date = request.args.get('date', "")

        # Проверяем обязательные параметры
        if not origin or not destination or not date:
            return jsonify({"error": "Необходимо указать origin, destination и date"}), 400

        # Проверяем формат IATA-кодов
        if len(origin) != 3 or len(destination) != 3:
            return jsonify({"error": "Используйте трехбуквенные IATA-коды"}), 400

        # Проверяем формат даты
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "Неверный формат даты. Используйте формат YYYY-MM-DD (например, 2023-12-01)."}), 400

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
        response = requests.get(BASE_URL, headers=headers, params=querystring)

        # Проверяем статус ответа
        if response.status_code == 429:  # Too Many Requests
            logging.error("Превышен лимит запросов к API")
            return jsonify({"error": "Превышен лимит запросов. Попробуйте позже."}), 429

        if response.ok:
            data = response.json()
            if "flights" not in data:
                logging.error(f"API вернул ошибку: {data}")
                return jsonify({"error": "Ошибка в данных API"}), 500
            return jsonify(data)
        else:
            error_data = response.json()
            error_message = error_data.get("message", "Ошибка API")
            logging.error(f"Ошибка API: {response.status_code}, {error_message}, Заголовки: {headers}, Параметры: {querystring}")
            return jsonify({"error": error_message}), response.status_code

    except Exception as e:
        logging.exception("Внутренняя ошибка сервера")
        return jsonify({"error": "Внутренняя ошибка сервера"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
