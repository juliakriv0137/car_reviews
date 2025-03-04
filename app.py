import requests
import json
import re
import csv
import time
import datetime
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# ✅ API-ключ Perplexity AI
PERPLEXITY_API_KEY = "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"

# ✅ Выбираем модель Perplexity AI
MODEL_NAME = "sonar-reasoning-pro"

# ✅ Пути к файлам
CAR_MODELS_FILE = "car_models.txt"
OUTPUT_CSV = "car_reviews.csv"

# ✅ Число потоков для параллельных запросов (оптимально 5)
MAX_THREADS = 5

# ✅ Функция для генерации обзора
def generate_full_review(query):
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "Ты - автоэксперт."},
            {"role": "user", "content": f"Напиши все плюсы и минусы автомобиля {query} на основе отзывов пользователей в интернете."}
        ],
        "max_tokens": 2000,
        "temperature": 0.5,
        "top_p": 0.9
    }

    attempts = 3  # Количество попыток
    for attempt in range(1, attempts + 1):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                print(f"❌ Ошибка {response.status_code} для {query}: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"⚠ Попытка {attempt}/{attempts} - ошибка соединения с API: {e}")

        time.sleep(5)  # Задержка перед повторной попыткой

    return f"Ошибка генерации обзора для {query} - API недоступен"

# ✅ Функция очистки текста
def clean_text(text):
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"\*\*", "", text)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"\n{2,}", "\n\n", text)
    text = re.sub(r"SEO-ключи:.*$", "", text, flags=re.MULTILINE)
    return text.strip()

# ✅ Функция загрузки списка моделей
def load_car_models():
    if not os.path.exists(CAR_MODELS_FILE):
        print(f"❌ Файл {CAR_MODELS_FILE} не найден.")
        return []
    
    with open(CAR_MODELS_FILE, "r", encoding="utf-8") as file:
        return [line.strip().split(" ", 1) for line in file.readlines() if line.strip()]

# ✅ Проверка, нужно ли перезаписать CSV (раз в месяц)
def should_reset_csv():
    if not os.path.exists(OUTPUT_CSV):
        return True  # Если файла нет, создаём новый

    last_modified = datetime.datetime.fromtimestamp(os.path.getmtime(OUTPUT_CSV))
    current_date = datetime.datetime.now()
    
    return last_modified.month != current_date.month  # Если месяц изменился — перезаписываем файл

# ✅ Функция записи данных в CSV (в реальном времени)
def save_review_to_csv(review_data):
    file_exists = os.path.exists(OUTPUT_CSV)

    # Если новый месяц — перезаписываем файл
    if should_reset_csv():
        print("📌 Новый месяц! Удаляем старые обзоры...")
        os.remove(OUTPUT_CSV) if os.path.exists(OUTPUT_CSV) else None
        file_exists = False

    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        # Если файл создаётся заново, пишем заголовки
        if not file_exists:
            writer.writerow(["id", "date", "title", "review", "mark", "model"])

        # Получаем текущее количество записей в файле
        existing_reviews = []
        if os.path.exists(OUTPUT_CSV):
            with open(OUTPUT_CSV, "r", encoding="utf-8") as existing_file:
                reader = csv.reader(existing_file)
                existing_reviews = list(reader)

        last_id = int(existing_reviews[-1][0]) if len(existing_reviews) > 1 else 0

        # Добавляем запись в CSV
        review_data.insert(0, last_id + 1)  # Добавляем ID
        writer.writerow(review_data)

    print(f"✅ Записано в CSV: {review_data[2]}")

# ✅ Основной процесс (многопоточный)
def main():
    car_models = load_car_models()
    if not car_models:
        print("⚠ Нет моделей автомобилей для генерации.")
        return

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        future_to_model = {executor.submit(generate_full_review, f"{mark} {model}"): (mark, model) for mark, model in car_models}

        for future in as_completed(future_to_model):
            mark, model = future_to_model[future]
            try:
                review = future.result()
                if review:
                    clean_review = clean_text(review)
                    title = f"Обзор {mark} {model}: плюсы и минусы"
                    date = datetime.datetime.now().strftime("%Y-%m-%d")
                    
                    # Сохраняем в CSV в реальном времени
                    save_review_to_csv([date, title, clean_review, mark, model])
            except Exception as e:
                print(f"❌ Ошибка обработки {mark} {model}: {e}")

if __name__ == "__main__":
    main()
