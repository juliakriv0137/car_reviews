import requests
import json
import re
import csv
import time
import datetime
import os

# ✅ API-ключ Perplexity AI
PERPLEXITY_API_KEY = "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"

# ✅ Выбираем модель Perplexity AI
MODEL_NAME = "sonar-reasoning-pro"

# ✅ Пути к файлам
CAR_MODELS_FILE = "car_models.txt"
OUTPUT_CSV = "car_reviews.csv"

# ✅ Функция для генерации обзора (с 3 попытками)
def generate_full_review(query):
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "Ты - автоэксперт"},
            {"role": "user", "content": f"Напиши все плюсы и минусы автомобиля {query} на основе отзывов пользователей в интернете."}
        ],
        "max_tokens": 1500,
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

        time.sleep(5)  # ⏳ Задержка перед повторной попыткой

    return f"Ошибка генерации обзора для {query} - API недоступен"

# ✅ Функция очистки текста
def clean_text(text):
    text = re.sub(r"\[\d+\]", "", text)  # Убираем ссылки типа [1], [2]
    text = re.sub(r"\*\*", "", text)  # Убираем звездочки **
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)  # Убираем размышления AI
    text = re.sub(r"\n{2,}", "\n\n", text)  # Убираем лишние пустые строки
    return text.strip()

# ✅ Функция загрузки списка моделей
def load_car_models():
    if not os.path.exists(CAR_MODELS_FILE):
        print(f"❌ Файл {CAR_MODELS_FILE} не найден.")
        return []
    
    with open(CAR_MODELS_FILE, "r", encoding="utf-8") as file:
        return [line.strip() for line in file.readlines() if line.strip()]

# ✅ Проверка, нужно ли перезаписать CSV (раз в месяц)
def should_reset_csv():
    if not os.path.exists(OUTPUT_CSV):
        return True  # Если файла нет, создаём новый

    last_modified = datetime.datetime.fromtimestamp(os.path.getmtime(OUTPUT_CSV))
    current_date = datetime.datetime.now()
    
    return last_modified.month != current_date.month  # Если месяц изменился — перезаписываем файл

# ✅ Функция сохранения обзоров в CSV
def save_to_csv(review_data):
    reset_csv = should_reset_csv()

    # Если новый месяц — перезаписываем файл
    if reset_csv:
        print("📌 Новый месяц! Удаляем старые обзоры...")
        os.remove(OUTPUT_CSV) if os.path.exists(OUTPUT_CSV) else None

    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        # Если файл создаётся заново, пишем заголовки
        if reset_csv or os.stat(OUTPUT_CSV).st_size == 0:
            writer.writerow(["id", "date", "title", "review", "mark", "model"])

        # Получаем текущее количество записей в файле
        existing_reviews = []
        if not reset_csv and os.path.exists(OUTPUT_CSV):
            with open(OUTPUT_CSV, "r", encoding="utf-8") as existing_file:
                reader = csv.reader(existing_file)
                existing_reviews = list(reader)

        last_id = int(existing_reviews[-1][0]) if len(existing_reviews) > 1 else 0  # Последний ID

        # Записываем данные в файл
        for i, (title, review, mark, model) in enumerate(review_data, start=last_id + 1):
            writer.writerow([i, datetime.datetime.now().strftime("%Y-%m-%d"), title, review, mark, model])

    # ✅ Гарантируем, что файл изменён для GitHub Actions
    with open(OUTPUT_CSV, "a", encoding="utf-8") as f:
        f.write("\n")

    print(f"✅ Файл обновлён: {OUTPUT_CSV}")

# ✅ Основной процесс
def main():
    car_models = load_car_models()
    if not car_models:
        print("⚠ Нет моделей автомобилей для генерации.")
        return

    reviews = []
    for model in car_models:
        print(f"🔄 Генерация обзора: {model}...")

        # Разделяем марку и модель (если указаны через пробел)
        parts = model.split(" ", 1)
        mark = parts[0] if len(parts) > 1 else model
        model_name = parts[1] if len(parts) > 1 else ""

        review = generate_full_review(model)

        if review:
            clean_review = clean_text(review)
            reviews.append((f"Плюсы и минусы {model}", clean_review, mark, model_name))
            save_to_csv([(f"Плюсы и минусы {model}", clean_review, mark, model_name)])

        time.sleep(10)  # Задержка между запросами

if __name__ == "__main__":
    main()
