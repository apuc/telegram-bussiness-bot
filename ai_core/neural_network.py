import random
import os
import json
import requests
from config import PIAPI_API_KEY, PIAPI_MODEL, get_proxies

PIAPI_URL = "https://api.piapi.ai/v1/chat/completions"

class ContentGenerator:
    def __init__(self):
        """Инициализация генератора контента"""
        print("🔄 Инициализация ContentGenerator...")

        # Проверяем, есть ли ключ PiAPI
        if PIAPI_API_KEY:
            self.model = PIAPI_MODEL
            self.use_piapi = True
            print("✅ PiAPI подключен!")
        else:
            print("⚠️ PiAPI ключ не найден, использую шаблоны")
            self.use_piapi = False
        
        # Шаблоны для запасного варианта (если PiAPI не работает)
        self.templates = {
            'instagram': [
                "🔥 {business_name} — это не просто бизнес, это миссия!\n\n"
                "Рассказываю, как мы пришли к тому, что делаем сегодня.\n"
                "В {years} лет мы прошли путь от идеи до реализации.\n\n"
                "А вы знали, что {business_name} помогает {problem_solution}?\n\n"
                "👉 Напиши в комментариях, сталкивался ли ты с этой проблемой!\n\n"
                "#бизнес #предприниматель #{hashtag} #историяуспеха",
                
                "📊 {business_name} — цифры, которые вдохновляют!\n\n"
                "За {years} лет мы:\n"
                "✅ Помогли {clients} клиентам\n"
                "✅ Увеличили прибыль на {profit}%\n"
                "✅ Выросли в {growth} раз\n\n"
                "Хочешь так же? Пиши в DM! 💬\n\n"
                "#бизнес #предпринимательство #{hashtag}"
            ],
            
            'linkedin': [
                "🚀 Как {business_name} изменил рынок в {years} году?\n\n"
                "Когда мы начинали, казалось, что {problem} — это непреодолимая стена.\n"
                "Но мы нашли решение: {solution}\n\n"
                "Результат: {result} 📈\n\n"
                "Какую бизнес-задачу вы решаете сегодня? Делитесь в комментариях! 💬\n\n"
                "#бизнес #лидерство #{hashtag} #growth",
                
                "💡 5 уроков за {years} лет в бизнесе\n\n"
                "1️⃣ {lesson1}\n"
                "2️⃣ {lesson2}\n"
                "3️⃣ {lesson3}\n"
                "4️⃣ {lesson4}\n"
                "5️⃣ {lesson5}\n\n"
                "Какой урок оказался для вас самым важным? 👇\n\n"
                "#бизнес #урокипредпринимательства #{hashtag}"
            ],
            
            'telegram': [
                "💬 Привет, друзья! 👋\n\n"
                "Сегодня хочу поделиться мыслями о {business_name}.\n\n"
                "Многие спрашивают: «Как ты пришел к этому?»\n"
                "Ответ прост: {short_story}\n\n"
                "А какой бизнес вдохновляет тебя? Пиши в комментариях! 👇\n\n"
                "#бизнес #предприниматель #{hashtag}",
                
                "📌 Важный пост для предпринимателей!\n\n"
                "В {business_name} мы верим, что {belief}\n\n"
                "Поэтому сегодня делюсь {tip} советом:\n"
                "{advice}\n\n"
                "А какой совет ты бы дал себе в начале пути? 🔥\n\n"
                "#бизнес #советы #{hashtag}"
            ],
            
            'twitter': [
                "🧵 Нить: Как {business_name} за {years} лет изменил подход к {industry}\n\n"
                "1/ Мы начинали с {start_point}\n"
                "2/ Главная проблема была: {problem}\n"
                "3/ Решение нашли через {solution}\n"
                "4/ Результат: {result}\n"
                "5/ Вывод: {lesson}\n\n"
                "Согласны? Репост, если цените бизнес-мышление! 🔄\n\n"
                "#бизнес #{hashtag}",
                
                "💭 Мысль дня от {business_name}:\n\n"
                "{quote}\n\n"
                "Как думаете, это правда? 👇\n\n"
                "#бизнес #мысли #{hashtag}"
            ],
            
            'ad': [
                "🎯 Хочешь получить {benefit}?\n\n"
                "В {business_name} мы знаем, как это сделать!\n\n"
                "За {years} лет мы помогли {clients} клиентам достичь {result}\n\n"
                "Напиши «ХОЧУ» в комментариях или DM, и я расскажу как! 💬\n\n"
                "#реклама #бизнес #{hashtag}"
            ]
        }
        
        print("✅ ContentGenerator готов к работе!")

    def generate_post(self, business_type, business_description, platform):
        """
        Генерирует контент для соцсетей
        
        Args:
            business_type (str): Тип бизнеса
            business_description (str): Описание бизнеса
            platform (str): Платформа (instagram, linkedin, telegram, twitter, ad)
        
        Returns:
            str: Сгенерированный пост
        """
        print(f"🔄 Генерация поста для {platform}...")
        
        # Пробуем сгенерировать через PiAPI
        if self.use_piapi:
            try:
                post = self._generate_with_piapi(business_type, business_description, platform)
                if post and len(post) > 20:
                    print("✅ Пост сгенерирован через PiAPI!")
                    return post
            except Exception as e:
                print(f"⚠️ Ошибка PiAPI: {e}, использую шаблоны")

        # Если PiAPI не работает - используем шаблоны
        print("🔄 Использую шаблоны...")
        return self._generate_with_templates(business_type, business_description, platform)

    def _generate_with_piapi(self, business_type, business_description, platform):
        """Генерация через PiAPI (OpenAI-совместимый chat/completions)"""
        
        platform_names = {
            'instagram': 'Instagram',
            'linkedin': 'LinkedIn',
            'telegram': 'Telegram',
            'twitter': 'Twitter/X',
            'ad': 'рекламный пост'
        }
        
        prompt = f"""
Ты — профессиональный SMM-специалист и копирайтер.

Напиши интересный, живой пост для {platform_names.get(platform, 'соцсетей')} о бизнесе.

Тип бизнеса: {business_type}
Описание бизнеса: {business_description}

Требования к посту:
- Длина: 100-200 слов (но не больше 200 слов)
- Живой, разговорный стиль
- Полезный контент для предпринимателей
- Призыв к действию в конце
- Используй 2-3 эмодзи

Напиши только текст поста, без лишних пояснений.
Пост должен быть уникальным и интересным.
"""
        
        response = requests.post(
            PIAPI_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {PIAPI_API_KEY}"
            },
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "Ты профессиональный копирайтер. Пиши ярко, полезно и вовлекающе."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.9,
                "max_tokens": 500
            },
            proxies=get_proxies(),
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        return data["choices"][0]["message"]["content"].strip()

    def generate_post_with_style(self, business_type, business_description, platform, style, wishes):
        """Генерирует пост с учётом стиля и пожеланий пользователя"""
        print(f"🔄 Генерация поста в своём стиле для {platform}...")

        if self.use_piapi:
            try:
                platform_names = {
                    'instagram': 'Instagram',
                    'linkedin': 'LinkedIn',
                    'telegram': 'Telegram',
                    'twitter': 'Twitter/X',
                    'ad': 'рекламный пост'
                }

                prompt = f"""
Ты — профессиональный SMM-специалист и копирайтер.

Напиши пост для {platform_names.get(platform, 'соцсетей')} о бизнесе.

Тип бизнеса: {business_type}
Описание бизнеса: {business_description}
Стиль поста: {style}
Пожелания к посту: {wishes}

Требования к посту:
- Длина: 100-200 слов
- Строго придерживайся указанного стиля и пожеланий
- Призыв к действию в конце
- Используй 2-3 эмодзи

Напиши только текст поста, без лишних пояснений.
"""

                response = requests.post(
                    PIAPI_URL,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {PIAPI_API_KEY}"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "Ты профессиональный копирайтер. Точно следуешь стилю и пожеланиям клиента."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.9,
                        "max_tokens": 500
                    },
                    proxies=get_proxies(),
                    timeout=30
                )
                response.raise_for_status()
                post = response.json()["choices"][0]["message"]["content"].strip()
                if post and len(post) > 20:
                    print("✅ Пост в стиле сгенерирован через PiAPI!")
                    return post
            except Exception as e:
                print(f"⚠️ Ошибка PiAPI: {e}, использую шаблоны")

        print("🔄 Использую шаблоны...")
        post = self._generate_with_templates(business_type, business_description, platform)
        return f"{post}\n\n💭 Пожелания учтены частично (без ИИ): {wishes}"

    def generate_content_plan(self, business_type, business_description, days):
        """Генерирует контент-план на несколько дней вперёд"""
        print(f"🔄 Генерация контент-плана на {days} дн...")

        if self.use_piapi:
            try:
                prompt = f"""
Ты — SMM-стратег. Составь контент-план на {days} дней для бизнеса.

Тип бизнеса: {business_type}
Описание бизнеса: {business_description}

Для каждого дня укажи платформу (instagram, linkedin, telegram, twitter или ad) и короткую идею поста (1 предложение).

Верни ТОЛЬКО валидный JSON без пояснений в формате:
{{"plan": [{{"day": 1, "platform": "instagram", "idea": "..."}}, ...]}}
"""

                response = requests.post(
                    PIAPI_URL,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {PIAPI_API_KEY}"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "Ты отвечаешь только валидным JSON, без markdown и пояснений."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 1000,
                        "response_format": {"type": "json_object"}
                    },
                    proxies=get_proxies(),
                    timeout=30
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"].strip()
                parsed = json.loads(content)
                plan = parsed.get("plan")
                if plan:
                    print("✅ Контент-план сгенерирован через PiAPI!")
                    return plan
            except Exception as e:
                print(f"⚠️ Ошибка PiAPI: {e}, использую шаблонный план")

        print("🔄 Использую шаблонный план...")
        return self._generate_template_plan(business_type, days)

    def _generate_template_plan(self, business_type, days):
        """Простой контент-план без обращения к ИИ (запасной вариант)"""
        platforms = ['instagram', 'linkedin', 'telegram', 'twitter', 'ad']
        ideas = [
            f"Расскажи историю успеха {business_type}",
            f"Покажи закулисье работы {business_type}",
            "Поделись отзывом клиента",
            "Развенчай миф из твоей ниши",
            "Дай практический совет подписчикам",
            "Проведи опрос среди аудитории",
            "Расскажи о новинке или акции"
        ]
        plan = []
        for day in range(1, days + 1):
            plan.append({
                'day': day,
                'platform': platforms[(day - 1) % len(platforms)],
                'idea': ideas[(day - 1) % len(ideas)]
            })
        return plan

    def _generate_with_templates(self, business_type, business_description, platform):
        """Генерация через шаблоны (запасной вариант)"""
        
        # Если платформы нет в шаблонах - используем instagram
        if platform not in self.templates:
            platform = 'instagram'
        
        # Подготовка данных для шаблона
        data = {
            'business_name': business_type,
            'industry': business_description[:30] if business_description else "твоей нише",
            'years': random.randint(2, 15),
            'clients': random.randint(50, 5000),
            'profit': random.randint(20, 300),
            'growth': random.randint(2, 10),
            'problem': random.choice([
                "не хватало знаний", "было сложно найти клиентов", 
                "конкуренты давили", "не было системы"
            ]),
            'solution': random.choice([
                "инновационный подход", "автоматизация процессов",
                "клиентоориентированность", "стратегическое планирование"
            ]),
            'result': random.choice([
                "выручка выросла в 3 раза", "число клиентов удвоилось",
                "бренд узнали в 5 городах", "создали команду из 30 человек"
            ]),
            'problem_solution': random.choice([
                "решает главную проблему предпринимателей",
                "помогает бизнесу расти быстрее",
                "упрощает сложные процессы",
                "делает мир лучше"
            ]),
            'lesson1': "Не бойся пробовать новое",
            'lesson2': "Клиент всегда прав (почти всегда)",
            'lesson3': "Команда — это всё",
            'lesson4': "Без маркетинга никуда",
            'lesson5': "Верь в своё дело",
            'short_story': random.choice([
                "я просто начал и не остановился",
                "увидел проблему и решил её",
                "поверил в идею, несмотря на сомнения",
                "просто делал то, что люблю"
            ]),
            'belief': random.choice([
                "успех приходит к тем, кто не боится ошибаться",
                "лучший способ предсказать будущее — создать его",
                "качество всегда побеждает количество"
            ]),
            'tip': random.choice(["простой", "важный", "ключевой"]),
            'advice': random.choice([
                "не распыляйся на всё подряд — фокусируйся на главном",
                "слушай своих клиентов — они лучшие советчики",
                "инвестируй в своё развитие — это окупается",
                "не бойся делегировать задачи"
            ]),
            'start_point': random.choice([
                "идеи и ноутбука", "небольшого стартапа",
                "мечты и энтузиазма", "первых 5 клиентов"
            ]),
            'quote': random.choice([
                "Бизнес — это не про деньги, а про ценность, которую ты создаёшь",
                "Каждый отказ приближает тебя к успеху",
                "Лучший момент начать — прямо сейчас",
                "Сложно — значит ты на правильном пути"
            ]),
            'benefit': random.choice([
                "прибыль без головной боли",
                "стабильный доход",
                "финансовую свободу",
                "масштабирование бизнеса"
            ]),
            'hashtag': random.choice([
                "бизнесрост", "предприниматель", "успех", 
                "бизнесидеи", "мойбизнес", "развитие"
            ])
        }
        
        # Выбираем случайный шаблон для платформы
        template = random.choice(self.templates[platform])
        
        # Заполняем шаблон данными
        try:
            post = template.format(**data)
        except KeyError as e:
            # Если какие-то ключи отсутствуют
            post = f"📝 Пост для {platform.upper()}\n\n" \
                   f"Бизнес: {business_type}\n" \
                   f"Описание: {business_description or 'Не указано'}\n\n" \
                   f"Расскажи о своём бизнесе в комментариях! 👇\n\n#бизнес #предприниматель"
        
        return post