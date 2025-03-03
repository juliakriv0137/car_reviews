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
CAR_MODELS_FILE = "/Users/juliakriv/otzyvy/car_models.txt"
OUTPUT_CSV = "/Users/juliakriv/otzyvy/car_reviews.csv"

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
            {"role": "system", "content": "Ты - автоэксперт. Пиши структурированные SEO-оптимизированные обзоры, без воды и размышлений."},
            {"role": "user", "content": f"Напиши полный обзор автомобиля {query} на основе отзывов владельцев. "
                                         f"Выдели логичные разделы: дизайн, интерьер, технические характеристики, плюсы и минусы, заключение. "
                                         f"Форматирование: заголовки, списки, абзацы, таблицы. "
                                         f"Не используй **, <think>, ссылки типа [1], [2]."}
        ],
        "max_tokens": 2000,
        "temperature": 0.5,
        "top_p": 0.9
    }

    attempts = 3  # Количество попыток
    for attempt in range(1, attempts + 1):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)  # ⏳ Таймаут 60 секунд
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                print(f"❌ Ошибка {response.status_code} для {query}: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"⚠ Попытка {attempt}/{attempts} - ошибка соединения с API: {e}")

        time.sleep(5)  # ⏳ Задержка перед повторной попыткой

    return f"Ошибка генерации обзора для {query} - API недоступен"  # Записываем в CSV

# ✅ Функция очистки текста
def clean_text(text):
    text = re.sub(r"\[\d+\]", "", text)  # Убираем ссылки типа [1], [2]
    text = re.sub(r"\*\*", "", text)  # Убираем звездочки **
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)  # Убираем размышления AI
    text = re.sub(r"\n{2,}", "\n\n", text)  # Убираем лишние пустые строки
    text = re.sub(r"SEO-ключи:.*$", "", text, flags=re.MULTILINE)  # Убираем блок "SEO-ключи"
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
def save_to_csv(reviews):
    reset_csv = should_reset_csv()

    # Если новый месяц — перезаписываем файл
    if reset_csv:
        print("📌 Новый месяц! Удаляем старые обзоры...")
        os.remove(OUTPUT_CSV) if os.path.exists(OUTPUT_CSV) else None

    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        # Если файл создаётся заново, пишем заголовки
        if reset_csv or os.stat(OUTPUT_CSV).st_size == 0:
            writer.writerow(["id", "дата", "заголовок", "текст"])

        # Получаем текущее количество записей в файле
        existing_reviews = []
        if not reset_csv and os.path.exists(OUTPUT_CSV):
            with open(OUTPUT_CSV, "r", encoding="utf-8") as existing_file:
                reader = csv.reader(existing_file)
                existing_reviews = list(reader)

        last_id = int(existing_reviews[-1][0]) if len(existing_reviews) > 1 else 0  # Последний ID

        # Добавляем новые обзоры
        for i, (title, text) in enumerate(reviews, start=last_id + 1):
            writer.writerow([i, datetime.datetime.now().strftime("%Y-%m-%d"), title, text])

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
        review = generate_full_review(model)

        if review:
            clean_review = clean_text(review)
            reviews.append((f"Обзор {model}: характеристики, плюсы и минусы", clean_review))

        time.sleep(10)  # Задержка между запросами

    save_to_csv(reviews)

if __name__ == "__main__":
    main()
