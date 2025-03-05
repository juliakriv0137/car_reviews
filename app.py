import requests
import json
import re
import csv
import time
import datetime
import os

# ✅ API-ключ Perplexity
PERPLEXITY_API_KEY = "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"

# ✅ Модель Perplexity
MODEL_NAME = "sonar-small-chat"

# ✅ Пути к файлам
CAR_MODELS_FILE = "car_models.txt"
OUTPUT_CSV = "car_reviews.csv"

# ✅ Список пропущенных машин
skipped_models = []

# ✅ Функция для генерации обзора (1 попытка, без повторов)
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

    print(f"📡 [{query}] Отправка запроса в API...")
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)

        if response.status_code == 200:
            print(f"✅ [{query}] Ответ от API получен!")
            return response.json()["choices"][0]["message"]["content"]
        else:
            print(f"❌ [{query}] Ошибка {response.status_code}: {response.text}")
            return None

    except requests.exceptions.Timeout:
        print(f"⏳ [{query}] Тайм-аут 60 сек! API не ответил. Машина пропущена.")
        skipped_models.append(query)  # Добавляем в список пропущенных
        return None

    except requests.exceptions.RequestException as e:
        print(f"⚠ [{query}] Ошибка соединения: {e}")
        skipped_models.append(query)  # Добавляем в список пропущенных
        return None

# ✅ Проверяем, есть ли заголовки в файле
def ensure_csv_headers():
    if not os.path.exists(OUTPUT_CSV) or os.stat(OUTPUT_CSV).st_size == 0:
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["id", "date", "title", "review", "mark", "model"])
        print("📌 Заголовки добавлены в CSV.")

# ✅ Функция очистки текста
def clean_text(text):
    text = re.sub(r"\[\d+\]", "", text)  # Убираем ссылки типа [1], [2]
    text = re.sub(r"\*\*", "", text)  # Убираем звездочки **
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)  # Убираем размышления AI
    text = re.sub(r"SEO-ключи:.*$", "", text, flags=re.MULTILINE)  # Убираем блок "SEO-ключи"

    # Убираем заголовочные символы (===, ##, ---)
    text = re.sub(r"^(?:===|#)+\s*", "", text, flags=re.MULTILINE)  # Убираем === и ##
    text = re.sub(r"^-{3,}", "", text, flags=re.MULTILINE)  # Убираем "---"
    
    # Логическое форматирование текста
    text = re.sub(r"\n{2,}", "\n\n", text)  # Убираем лишние пустые строки

    return text.strip()

# ✅ Функция сохранения обзоров в CSV
def save_to_csv(title, review, mark, model):
    ensure_csv_headers()
    
    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        # Определяем последний ID
        last_id = 0
        with open(OUTPUT_CSV, "r", encoding="utf-8") as existing_file:
            reader = csv.reader(existing_file)
            existing_reviews = list(reader)
            if len(existing_reviews) > 1:
                try:
                    last_id = int(existing_reviews[-1][0])
                except ValueError:
                    last_id = 0

        writer.writerow([last_id + 1, datetime.datetime.now().strftime("%Y-%m-%d"), title, review, mark, model])

    print(f"✅ [{mark} {model}] Данные записаны в CSV")

# ✅ Основной процесс (1 машина за раз, без повторов)
def main():
    with open(CAR_MODELS_FILE, "r", encoding="utf-8") as file:
        car_models = [line.strip() for line in file.readlines() if line.strip()]

    if not car_models:
        print("⚠ Нет моделей автомобилей для генерации.")
        return

    print(f"🔄 Всего машин для обработки: {len(car_models)}")

    for idx, model in enumerate(car_models, 1):
        print(f"🚗 [{idx}/{len(car_models)}] Обрабатываю: {model}")

        parts = model.split(maxsplit=1)
        if len(parts) < 2:
            print(f"⚠ Ошибка в названии: {model}. Пропускаем.")
            skipped_models.append(model)  # Добавляем в список пропущенных
            continue
        mark, model_name = parts

        review = generate_full_review(model)
        if review:
            clean_review = clean_text(review)
            save_to_csv(f"Обзор {model}: плюсы и минусы", clean_review, mark, model_name)
        else:
            print(f"❌ [{idx}/{len(car_models)}] Ошибка при генерации обзора.")
            skipped_models.append(model)  # Добавляем в список пропущенных

        time.sleep(30)  # **Пауза 30 секунд перед обработкой следующей машины**

    # Выводим список пропущенных машин
    if skipped_models:
        print("\n⛔ **Пропущенные машины:**")
        for car in skipped_models:
            print(f"🚨 {car}")
    else:
        print("\n✅ **Все машины успешно обработаны!**")

if __name__ == "__main__":
    main()
