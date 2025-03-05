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
        "max_tokens": 2000,
        "temperature": 0.5,
        "top_p": 0.9
    }

    attempts = 3  # Количество попыток
    for attempt in range(1, attempts + 1):
        try:
            print(f"🔄 [{query}] Попытка {attempt}/{attempts} отправки запроса...")
            response = requests.post(url, headers=headers, json=payload, timeout=60)

            if response.status_code == 200:
                print(f"✅ [{query}] Обзор успешно получен!")
                return response.json()["choices"][0]["message"]["content"]
            else:
                print(f"❌ [{query}] Ошибка {response.status_code}: {response.text}")

        except requests.exceptions.RequestException as e:
            print(f"⚠ [{query}] Ошибка соединения: {e}")

        time.sleep(5)  # Задержка перед повторной попыткой

    print(f"⛔ [{query}] Все попытки не удались.")
    return f"Ошибка генерации обзора для {query} - API недоступен"

# ✅ Функция очистки текста и форматирования
def clean_text(text):
    text = re.sub(r"\[\d+\]", "", text)  # Убираем ссылки типа [1], [2]
    text = re.sub(r"\*\*", "", text)  # Убираем звездочки **
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)  # Убираем размышления AI
    text = re.sub(r"SEO-ключи:.*$", "", text, flags=re.MULTILINE)  # Убираем блок "SEO-ключи"

    # Убираем лишние символы заголовков и форматируем текст
    text = re.sub(r"^(?:===|#)+\s*", "", text, flags=re.MULTILINE)  # Убираем === и ##
    text = re.sub(r"^-{3,}", "", text, flags=re.MULTILINE)  # Убираем "---"
    text = re.sub(r"\n{2,}", "\n\n", text)  # Убираем лишние пустые строки

    return text.strip()

# ✅ Функция загрузки списка моделей
def load_car_models():
    if not os.path.exists(CAR_MODELS_FILE):
        print(f"❌ Файл {CAR_MODELS_FILE} не найден.")
        return []
    
    with open(CAR_MODELS_FILE, "r", encoding="utf-8") as file:
        return [line.strip() for line in file.readlines() if line.strip()]

# ✅ Функция сохранения обзоров в CSV (запись в реальном времени)
def save_to_csv(title, review, mark, model):
    file_exists = os.path.exists(OUTPUT_CSV)

    # Проверяем, есть ли заголовки в файле
    headers_needed = not file_exists or os.stat(OUTPUT_CSV).st_size == 0

    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        # **Добавляем заголовки, если их нет**
        if headers_needed:
            writer.writerow(["id", "date", "title", "review", "mark", "model"])
            print("📌 Заголовки добавлены в CSV.")

        # **Определяем последний ID**
        last_id = 0
        if file_exists:
            with open(OUTPUT_CSV, "r", encoding="utf-8") as existing_file:
                reader = csv.reader(existing_file)
                existing_reviews = list(reader)
                if len(existing_reviews) > 1:
                    try:
                        last_id = int(existing_reviews[-1][0])
                    except ValueError:
                        last_id = 0

        # **Записываем новую строку**
        writer.writerow([last_id + 1, datetime.datetime.now().strftime("%Y-%m-%d"), title, review, mark, model])

    print(f"✅ [{mark} {model}] Данные записаны в {OUTPUT_CSV}")

# ✅ Основной процесс
def main():
    car_models = load_car_models()
    if not car_models:
        print("⚠ Нет моделей автомобилей для генерации.")
        return

    # Последовательная обработка машин (по одной за раз)
    for model in car_models:
        print(f"🔄 Начинаю обработку модели: {model}")

        # Разделяем марку и модель
        parts = model.split(maxsplit=1)
        if len(parts) < 2:
            print(f"⚠ Ошибка в названии: {model}. Пропускаем.")
            continue
        mark, model_name = parts

        review = generate_full_review(model)

        if review:
            clean_review = clean_text(review)
            print(f"✅ Обзор {model} успешно создан!")
            save_to_csv(f"Обзор {model}: плюсы и минусы", clean_review, mark, model_name)
        else:
            print(f"❌ Ошибка при генерации обзора для {model}")

        time.sleep(10)  # Задержка между запросами

if __name__ == "__main__":
    main()
