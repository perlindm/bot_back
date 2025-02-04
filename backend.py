from flask import Flask, request, jsonify, redirect
import requests
from flask_cors import CORS
import os
from dotenv import load_dotenv
import logging

# Загружаем переменные окружения из файла .env
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)

# Создаем экземпляр Flask
app = Flask(__name__)
CORS(app)  # Разрешаем CORS для всех доменов

# Получаем переменные окружения
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
if not RAPIDAPI_KEY:
    logging.error("API-ключ не найден. Убедитесь, что переменная окружения RAPIDAPI_KEY установлена.")
    raise ValueError("API-ключ не найден. Убедитесь, что переменная окружения RAPIDAPI_KEY установлена.")

RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "skyscanner89.p.rapidapi.com")  # Значение по умолчанию

# Базовый URL для запросов к Skyscanner API
BASE_URL = f"https://{RAPIDAPI_HOST}/flights/one-way/list"

# Заголовки для запросов
headers = {
    'x-rapidapi-key': RAPIDAPI_KEY,
    'x-rapidapi-host': RAPIDAPI_HOST
}

# Маршрут для корневого пути
@app.route('/')
def home():
    return "Welcome to Travelink! Use the /search-flights endpoint to find flights."

# Маршрут для поиска авиабилетов
@app.route('/search-flights', methods=['GET'])
def search_flights():
    try:
        # Получаем параметры из запроса
        origin = request.args.get('origin')
        destination = request.args.get('destination')
        date = request.args.get('date')

        # Проверяем, что все параметры указаны
        if not origin or not destination or not date:
            return jsonify({"error": "Необходимо указать origin, destination и date"}), 400

        # Формируем параметры запроса
        querystring = {
            "origin": origin,
            "destination": destination,
            "date": date,
            "adults": "1",
            "currency": "USD"
        }

        # Логируем запрос
        logging.debug(f"Параметры запроса: origin={origin}, destination={destination}, date={date}")

        # Отправляем запрос к Skyscanner API
        response = requests.get(BASE_URL, headers=headers, params=querystring)
        data = response.json()

        # Логируем ответ от Skyscanner API
        logging.debug(f"Ответ от Skyscanner API: {response.status_code}, {data}")

        # Проверяем статус ответа
        if response.status_code == 200 and "flights" in data:
            return jsonify(data)
        elif response.status_code == 401:
            logging.error("Недействительный API-ключ. Проверьте настройки переменных окружения.")
            return jsonify({"error": "Недействительный API-ключ. Проверьте настройки."}), 401
        else:
            error_message = data.get("message", "Не удалось получить данные")
            logging.error(f"Ошибка Skyscanner API: {response.status_code}, {error_message}")
            return jsonify({"error": error_message}), response.status_code

    except Exception as e:
        logging.error(f"Произошла ошибка: {str(e)}")
        return jsonify({"error": "Внутренняя ошибка сервера"}), 500


# Запуск приложения
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
