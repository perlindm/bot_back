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

# Amadeus API Credentials
AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY")
AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET")

if not AMADEUS_API_KEY or not AMADEUS_API_SECRET:
    logging.error("API-ключ или секрет не найдены. Установите AMADEUS_API_KEY и AMADEUS_API_SECRET в .env")
    exit(1)

# Базовые URL для Amadeus API
AUTH_URL = "https://test.api.amadeus.com/v1/security/oauth2/token"
FLIGHTS_URL = "https://test.api.amadeus.com/v2/shopping/flight-offers"

# 🔹 Функция для получения токена доступа
def get_access_token():
    try:
        payload = {
            "grant_type": "client_credentials",
            "client_id": AMADEUS_API_KEY,
            "client_secret": AMADEUS_API_SECRET
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        response = requests.post(AUTH_URL, data=payload, headers=headers)
        if response.ok:
            return response.json().get("access_token")
        else:
            logging.error(f"Ошибка при получении токена: {response.text}")
            return None
    except Exception as e:
        logging.error(f"Ошибка при получении токена: {str(e)}")
        return None

@app.route('/')
def home():
    return "Welcome to Travelink! Use /search-flights to find flights."

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

        # Проверяем формат даты
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "Неверный формат даты. Используйте YYYY-MM-DD (например, 2023-12-01)."}), 400

        # Логируем запрос
        logging.info(f"Поиск билетов: {city_from} → {city_to} ({date})")

        # Получаем токен доступа
        access_token = get_access_token()
        if not access_token:
            return jsonify({"error": "Не удалось получить токен доступа"}), 500

        # Формируем заголовки и параметры запроса
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        querystring = {
            "originLocationCode": city_from,
            "destinationLocationCode": city_to,
            "departureDate": date,
            "adults": "1",
            "currencyCode": "USD",
            "max": "10"  # Максимальное количество результатов
        }

        # Отправляем запрос к Amadeus API
        response = requests.get(FLIGHTS_URL, headers=headers, params=querystring)

        # Логируем ответ от API
        logging.debug(f"Ответ от API: {response.status_code}, {response.text}")

        # Проверяем статус ответа
        if response.ok:
            data = response.json()
            if "data" in data and len(data["data"]) > 0:
                return jsonify(data)
            else:
                logging.error(f"API вернул пустой ответ: {data}")
                return jsonify({"error": "Билеты не найдены"}), 404
        else:
            error_data = response.json()
            error_message = error_data.get("errors", [{"detail": "Ошибка API"}])[0].get("detail", "Ошибка API")
            logging.error(f"Ошибка API: {response.status_code}, {error_message}")
            return jsonify({"error": error_message}), response.status_code

    except Exception as e:
        logging.exception("Внутренняя ошибка сервера")
        return jsonify({"error": "Внутренняя ошибка сервера"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
