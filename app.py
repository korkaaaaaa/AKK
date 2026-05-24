from flask import Flask, render_template, request, jsonify
import requests
import os
from datetime import datetime

app = Flask(__name__)


FOLDER_ID = "b1gusfdsimq3c3knbej7"
API_KEY = os.getenv("YANDEX_API_KEY")

URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"


def call_yandex_gpt(prompt, temperature=0.1):
    body = {
        "modelUri": f"gpt://{FOLDER_ID}/yandexgpt-lite",
        "completionOptions": {
            "stream": False,
            "temperature": temperature,  # тут используем динамическую температуру
            "maxTokens": 2000
        },
        "messages": [
            {
                "role": "user",
                "text": prompt
            }
        ]
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {API_KEY}"
    }

    try:
        response = requests.post(URL, headers=headers, json=body, timeout=30)

        if response.status_code == 200:
            result = response.json()
            return result["result"]["alternatives"][0]["message"]["text"]
        else:
            return f"Ошибка API: {response.status_code} - {response.text}"

    except Exception as e:
        return f"Ошибка соединения: {str(e)}"


def save_to_history(style, user_text, summary, elapsed_time):
    try:
        with open('history.txt', 'a', encoding='utf-8') as f:
            f.write("\n" + "="*80 + "\n")
            f.write(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"🎨 Стиль: {style}\n")
            f.write(f"⏱️ Время: {elapsed_time:.1f} сек\n")
            f.write(f"📥 Текст: {len(user_text)} символов\n")
            f.write(f"📤 Конспект: {len(summary)} символов\n\n")

            f.write("ИСХОДНЫЙ ТЕКСТ:\n")
            f.write(user_text + "\n\n")

            f.write("КОНСПЕКТ:\n")
            f.write(summary + "\n")

    except Exception as e:
        print(f"Ошибка сохранения истории: {e}")



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/summarize', methods=['POST'])
def summarize():
    try:
        data = request.json

        user_text = data.get('text', '').strip()
        style = data.get('style', 'scientific')
        format_type = data.get('format', 'Тезисы')
        compression = data.get('compression', 'Среднее сжатие')

        # 🔴 Проверки
        if not user_text:
            return jsonify({'error': 'Введите текст'}), 400

        if len(user_text) > 15000:
            return jsonify({'error': 'Максимум 15000 символов'}), 400

        print("\n" + "="*50)
        print(f"📥 Новый запрос")
        print(f"Стиль: {style}")
        print(f"Формат: {format_type}")
        print(f"Сжатие: {compression}")
        print(f"Длина: {len(user_text)}")

        style_prompts = {
            'scientific': 'Пиши текст академическим стилем. Используй точные термины, структурируй информацию логично: введение, основной блок, выводы. Избегай эмоций и разговорной речи. Подкрепляй утверждения фактами, если возможно. Сохраняй строгость и объективность.',
            'kids': 'Пиши текст простым, понятным языком для ребёнка 7-10 лет. Используй короткие предложения, яркие примеры и сравнения. Объясняй сложные термины простыми словами. Сделай текст интересным и живым, чтобы ребёнку было легко понимать.',
            'short': 'Пиши текст максимально простым и понятным языком. Используй короткие предложения, избегай сложной терминологии. Сохраняй ясность, логическую последовательность и акцент на главные мысли. Текст должен быть легко читаемым.'
        }

        style_text = style_prompts.get(style, style_prompts['scientific'])

        format_rules = {
            'Абзацы': 'Представь информацию связным текстом, разделённым на абзацы. Каждый абзац должен содержать одну основную мысль или идею. Структурируй текст логически: начало, середина, конец. Не делай маркированные списки или нумерацию.',
            'Тезисы': 'Представь текст в виде коротких тезисов. Каждая мысль с новой строки. Строго по сути, без лишних слов. Тезисы должны быть лаконичными и понятными. Подчёркивай ключевые идеи, чтобы их легко было выделить глазами.',
            'Список': 'Представь текст в виде маркированного списка. Каждый пункт — отдельная мысль или факт. Используй логическую последовательность, чтобы пункты были понятны и связаны между собой. Избегай длинных абзацев внутри пунктов.'
        }

        format_text = format_rules.get(format_type, format_rules['Тезисы'])

        compression_rules = {
            'Сильное сжатие': 'Сократи текст на 70-80%, оставив только самые важные факты и ключевые идеи. Исключи все второстепенные детали, описания и повторения. Текст должен быть максимально компактным, но при этом сохранять смысл.',
            'Среднее сжатие': 'Сократи текст на 40-60%, оставив ключевые идеи и основные аргументы. Сохрани структуру и логику повествования, но убери второстепенные детали и повторы. Текст остаётся информативным, но более лаконичным.',
            'Минимальное сжатие': 'Слегка сократи текст на 20-30%, сохрани почти всю информацию. Убери только очевидные повторения, уточни и упорядочи предложения. Текст остаётся почти полным, но более структурированным и удобным для чтения.'
        }

        compression_text = compression_rules.get(compression, compression_rules['Среднее сжатие'])

        prompt = f"""
{style_text}

{format_text}

{compression_text}

Требования:
- Строго соблюдай формат
- Не добавляй лишнего
- Делай текст понятным и структурированным

Текст:
{user_text}

Конспект:
"""

        temperature_map = {
            'scientific': 0.1, 
            'kids': 1.0,       
            'short': 0.3       
        }
        temperature = temperature_map.get(style, 0.1) 

        print("🤖 Отправка в GPT...")
        start_time = datetime.now()

        summary = call_yandex_gpt(prompt, temperature=temperature)

        elapsed_time = (datetime.now() - start_time).total_seconds()

        if summary.startswith("Ошибка"):
            print("❌ Ошибка:", summary)
            return jsonify({'error': summary}), 500

        print(f"✅ Готово за {elapsed_time:.1f} сек")

        # 💾 сохраняем
        save_to_history(style, user_text, summary, elapsed_time)

        return jsonify({
            'summary': str(summary)
        })

    except Exception as e:
        print("❌ Ошибка:", str(e))
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)