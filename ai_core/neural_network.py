import random
import os
import json
import requests
from config import PIAPI_API_KEY, PIAPI_MODEL, get_proxies

PIAPI_URL = "https://api.piapi.ai/v1/chat/completions"


class ContentGenerator:
    def __init__(self, provider_settings=None):
        """Инициализация генератора контента.
        provider_settings — опциональный dict с ключами:
          provider_type, api_key, base_url, text_model
        Если не передан — используются глобальные настройки PiAPI из config."""
        print("🔄 Инициализация ContentGenerator...")

        if provider_settings and provider_settings.get("api_key"):
            # Per-user настройки
            self.api_key = provider_settings["api_key"]
            self.base_url = provider_settings.get("base_url") or PIAPI_URL.replace("/chat/completions", "")
            self.model = provider_settings.get("text_model") or PIAPI_MODEL
            self.use_piapi = True
            self.chat_url = self.base_url.rstrip("/") + "/chat/completions"
            self.provider_type = provider_settings.get("provider_type", "custom")
            # Прокси используется для всех провайдеров (если настроен в .env)
            # Это нужно для доступа из России к зарубежным API
            self.proxies = get_proxies()
            print(f"✅ Провайдер: {self.provider_type} | модель: {self.model} | прокси: {'да' if self.proxies else 'нет'}")
        elif PIAPI_API_KEY:
            # Глобальные настройки из config
            self.api_key = PIAPI_API_KEY
            self.base_url = PIAPI_URL.replace("/chat/completions", "")
            self.model = PIAPI_MODEL
            self.use_piapi = True
            self.chat_url = PIAPI_URL
            self.provider_type = "piapi"
            self.proxies = get_proxies()
            print("✅ PiAPI подключен (глобальные настройки)!")
        else:
            print("⚠️ API ключ не найден, использую шаблоны")
            self.use_piapi = False
            self.api_key = None
            self.chat_url = PIAPI_URL
            self.model = PIAPI_MODEL
            self.provider_type = "piapi"
            self.proxies = get_proxies()
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
            self.chat_url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
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
            proxies=self.proxies,
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
                    self.chat_url,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}"
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
                    proxies=self.proxies,
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

    def generate_post_from_brand_profile(self, brand_data, platform, style, wishes):
        """Генерирует пост на основе медиа-образа (данных опроса brand_survey).
        brand_data — dict с полями опроса."""
        print(f"🔄 Генерация поста из медиа-образа для {platform}...")

        brand_type = brand_data.get("brand_type", "personal")
        is_org = (brand_type == "organization")
        is_community = (brand_type == "community")

        # Собираем ключевые поля медиа-образа
        client_name = brand_data.get("client_name", "")
        client_role = brand_data.get("client_role", "")
        brand_essence = brand_data.get("brand_essence", "")
        positioning_who = brand_data.get("positioning_who", "")
        positioning_problem = brand_data.get("positioning_problem", "")
        positioning_result = brand_data.get("positioning_result", "")
        usp = brand_data.get("usp", "")
        tov_description = brand_data.get("tov_description", "")
        tov_references = brand_data.get("tov_references", "")
        tov_axes = brand_data.get("tov_axes", "")
        prompt_context = brand_data.get("prompt_context", "")
        prompt_tov = brand_data.get("prompt_tov", "")
        prompt_structure = brand_data.get("prompt_structure", "")
        prompt_directions = brand_data.get("prompt_directions", "")
        prompt_formats = brand_data.get("prompt_formats", "")
        prompt_technical = brand_data.get("prompt_technical", "")

        # Поля организации
        org_name = brand_data.get("org_name", "")
        org_industry = brand_data.get("org_industry", "")
        org_mission = brand_data.get("org_mission", "")
        org_products = brand_data.get("org_products", "")
        org_team_size = brand_data.get("org_team_size", "")
        positioning_difference = brand_data.get("positioning_difference", "")
        community_formats = brand_data.get("community_formats", "")

        platform_names = {
            'instagram': 'Instagram',
            'linkedin': 'LinkedIn',
            'telegram': 'Telegram',
            'twitter': 'Twitter/X',
            'ad': 'рекламный пост'
        }

        if is_community:
            identity_name = org_name
            identity_role = org_industry
            identity_block = f"""=== ОБЩЕСТВЕННАЯ ОРГАНИЗАЦИЯ ===
Название: {org_name}
Сфера: {org_industry}
Миссия: {org_mission}
Направления деятельности: {org_products}
Участников: {org_team_size}
Формат взаимодействия: {community_formats}
Сущность бренда: {brand_essence}
УТП: {usp}"""
            positioning_block = f"""=== ПОЗИЦИОНИРОВАНИЕ ===
Для кого создано: {positioning_who}
Какую проблему решает: {positioning_problem}
Ценность для участника: {positioning_result}
Чем отличаемся от других: {positioning_difference}"""
            tone_intro = "Ты — профессиональный копирайтер, создающий контент для общественной организации / бизнес-сообщества."
            post_intro = f"Напиши пост для {platform_names.get(platform, 'соцсетей')} от имени организации «{org_name}»."
            system_msg = f"Ты профессиональный копирайтер. Пишешь контент для бизнес-сообщества «{org_name}» в соответствии с его миссией, ценностями и Tone of Voice."
        elif is_org:
            identity_name = org_name
            identity_role = org_industry
            identity_block = f"""=== ОРГАНИЗАЦИЯ ===
Название: {org_name}
Сфера: {org_industry}
Миссия: {org_mission}
Продукты/услуги: {org_products}
Сотрудников: {org_team_size}
Сущность бренда: {brand_essence}
УТП: {usp}"""
            positioning_block = f"""=== ПОЗИЦИОНИРОВАНИЕ ===
Кому помогаем: {positioning_who}
Какую проблему решаем: {positioning_problem}
Какой результат получает клиент: {positioning_result}
Почему выбирают нас: {positioning_difference}"""
            tone_intro = "Ты — профессиональный копирайтер, создающий контент для организации."
            post_intro = f"Напиши пост для {platform_names.get(platform, 'соцсетей')} от имени организации «{org_name}»."
            system_msg = f"Ты профессиональный копирайтер. Пишешь контент для организации «{org_name}» в соответствии с её Tone of Voice и позиционированием."
        else:
            identity_name = client_name
            identity_role = client_role
            identity_block = f"""=== ЛИЧНОСТЬ И КОНТЕКСТ ===
Имя: {client_name}
Роль: {client_role}
Сущность бренда: {brand_essence}
УТП: {usp}"""
            positioning_block = f"""=== ПОЗИЦИОНИРОВАНИЕ ===
Кому помогаю: {positioning_who}
Какую проблему решаю: {positioning_problem}
Какой результат получает клиент: {positioning_result}"""
            tone_intro = "Ты — профессиональный копирайтер-психолог, который глубоко понимает образ и стратегию личного бренда."
            post_intro = f"Напиши пост для {platform_names.get(platform, 'соцсетей')} от лица автора медиа-образа."
            system_msg = "Ты профессиональный копирайтер-психолог. Пишешь в точном соответствии с образом и Tone of Voice автора."

        if self.use_piapi:
            try:
                prompt = f"""
{tone_intro}

{post_intro}

{identity_block}

{positioning_block}

=== TONE OF VOICE ===
Описание тона: {tov_description}
Референсы: {tov_references}
Оси ToV: {tov_axes}

=== СТРУКТУРА МЫСЛИ ===
{prompt_structure}

=== КОНТЕНТ-НАПРАВЛЕНИЯ ===
{prompt_directions}

=== ФОРМАТЫ И ШАБЛОНЫ ===
{prompt_formats}

=== ТЕХНИЧЕСКИЕ ТРЕБОВАНИЯ ===
{prompt_technical}

=== ПАРАМЕТРЫ ЭТОГО ПОСТА ===
Платформа: {platform_names.get(platform, 'соцсети')}
Стиль: {style}
Пожелания: {wishes}

Напиши только текст поста, без лишних пояснений. Следуй структуре мысли и Tone of Voice.
"""
                response = requests.post(
                    self.chat_url,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_msg},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.9,
                        "max_tokens": 4000
                    },
                    proxies=self.proxies,
                    timeout=90
                )
                response.raise_for_status()
                msg = response.json()["choices"][0]["message"]
                post = (msg.get("content") or "").strip()
                if post and len(post) > 20:
                    print("✅ Пост из медиа-образа сгенерирован через API!")
                    return post
                # Если content пустой — возможно reasoning-модель не успела завершить
                raise RuntimeError("API вернул пустой ответ (content пуст). Увеличьте max_tokens или попробуйте другую модель.")
            except requests.exceptions.HTTPError as e:
                status = e.response.status_code if e.response is not None else "?"
                body = e.response.text[:200] if e.response is not None else ""
                raise RuntimeError(f"API вернул ошибку {status}: {body}")
            except requests.exceptions.ConnectionError as e:
                raise RuntimeError(f"Не удалось подключиться к API: {e}")
            except requests.exceptions.Timeout:
                raise RuntimeError("Превышен таймаут запроса к API (30 сек)")
            except Exception as e:
                raise RuntimeError(f"Ошибка API: {e}")

        # Fallback — шаблонный пост с данными медиа-образа
        print("🔄 Использую шаблонный пост из медиа-образа...")
        return self._generate_template_brand_post(brand_data, platform, wishes)

    def modify_post(self, original_post: str, instruction: str) -> str:
        """Модифицирует существующий пост по инструкции пользователя.
        original_post — текущий текст поста
        instruction — что нужно сделать («сократи вдвое», «сделай официальнее» и т.д.)
        Возвращает новый текст поста.
        """
        print(f"🔄 Модификация поста: «{instruction[:60]}»...")

        prompt = f"""Ты — профессиональный копирайтер. Пользователь просит изменить пост.

=== ТЕКУЩИЙ ПОСТ ===
{original_post}

=== ИНСТРУКЦИЯ ===
{instruction}

=== ЗАДАЧА ===
Перепиши пост, выполнив инструкцию. Сохрани общий смысл и стиль. Верни ТОЛЬКО готовый пост без пояснений и markdown."""

        if self.use_piapi:
            try:
                response = requests.post(
                    self.chat_url,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "Ты профессиональный копирайтер. Ты редактируешь посты строго по инструкции."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 4000
                    },
                    proxies=self.proxies,
                    timeout=90
                )
                response.raise_for_status()
                post = response.json()["choices"][0]["message"]["content"].strip()
                if post and len(post) > 20:
                    print("✅ Пост модифицирован!")
                    return post
            except Exception as e:
                print(f"⚠️ Ошибка API при модификации: {e}")

        # Если ИИ не сработал — возвращаем оригинал с пометкой
        return f"{original_post}\n\n💬 [ИИ не смог изменить пост: {instruction}]"

    def _generate_template_brand_post(self, brand_data, platform, wishes):
        """Простой пост из медиа-образа без обращения к ИИ (запасной вариант)."""
        client_name = brand_data.get("client_name", "Автор")
        brand_essence = brand_data.get("brand_essence", "")
        usp = brand_data.get("usp", "")
        positioning_result = brand_data.get("positioning_result", "")

        platform_emoji = {
            "instagram": "📸", "linkedin": "💼", "telegram": "📱",
            "twitter": "🐦", "ad": "📢"
        }
        emoji = platform_emoji.get(platform, "📝")

        post = (
            f"{emoji} {brand_essence}\n\n"
            f"Меня зовут {client_name}.\n"
            f"{usp}\n\n"
            f"Я помогаю получить: {positioning_result}\n\n"
        )
        if wishes:
            post += f"💭 {wishes}\n\n"
        post += "Напишите в комментариях, какая у вас сейчас задача 👇\n\n#личныйбренд #бизнес"
        return post

    def suggest_image_concepts(self, post_text, brand_data=None):
        """Анализирует текст поста и предлагает 4 варианта концепции изображения.
        Возвращает список dict: [{title, description, style, size}, ...]"""
        print(f"🔄 Анализ поста для подбора концепции изображения ({len(post_text)} символов)...")

        if not self.use_piapi:
            # Fallback — базовые концепции без ИИ
            return [
                {"title": "Тематическая фотография", "description": "Профессиональная фотография, иллюстрирующая ключевую идею поста", "style": "photo", "size": "wide"},
                {"title": "Минималистичный баннер", "description": "Чистый баннер с текстом поста на минималистичном фоне", "style": "minimal", "size": "wide"},
                {"title": "Абстрактная иллюстрация", "description": "Цветная абстрактная иллюстрация в тон поста", "style": "illustration", "size": "square"},
                {"title": "Инфографика", "description": "Визуализация данных и ключевых тезисов поста", "style": "flat", "size": "tall"},
            ]

        brand_context = ""
        if brand_data:
            brand_context = f"""
Контекст бренда:
- Имя: {brand_data.get('client_name', '')}
- Роль: {brand_data.get('client_role', '')}
- Сущность: {brand_data.get('brand_essence', '')}
- УТП: {brand_data.get('usp', '')}
"""

        prompt = f"""Ты — арт-директор и визуальный стратег. Проанализируй текст поста и предложи 4 разных варианта визуального оформления.

=== ТЕКСТ ПОСТА ===
{post_text}
{brand_context}
=== ЗАДАЧА ===
Предложи 4 контрастных варианта изображения. Каждый вариант — это отдельная идея с уникальным настроением и стилем.

Для каждого варианта укажи:
- title: краткое название (2-4 слова на русском)
- description: что изображено (1 предложение на русском)
- style: один из: photo, illustration, minimal, 3d, flat
- size: один из: square, wide, tall

Верни ТОЛЬКО JSON-массив без markdown и пояснений:
[{{"title": "...", "description": "...", "style": "...", "size": "..."}}, ...]"""

        try:
            response = requests.post(
                self.chat_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "Ты — арт-директор. Отвечай только валидным JSON без markdown-обёрток."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.8,
                    "max_tokens": 1000
                },
                proxies=self.proxies,
                timeout=60
            )
            response.raise_for_status()
            raw = response.json()["choices"][0]["message"]["content"].strip()

            # Убираем markdown-обёртку если есть
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1]
                if raw.endswith("```"):
                    raw = raw[:-3]
                raw = raw.strip()

            concepts = json.loads(raw)
            if isinstance(concepts, list) and len(concepts) > 0:
                print(f"✅ Получено {len(concepts)} концепций от ИИ")
                return concepts[:5]  # макс 5
        except Exception as e:
            print(f"⚠️ Ошибка при получении концепций: {e}")

        # Fallback
        return [
            {"title": "Тематическая фотография", "description": "Профессиональная фотография, иллюстрирующая ключевую идею поста", "style": "photo", "size": "wide"},
            {"title": "Минималистичный баннер", "description": "Чистый баннер с текстом поста на минималистичном фоне", "style": "minimal", "size": "wide"},
            {"title": "Абстрактная иллюстрация", "description": "Цветная абстрактная иллюстрация в тон поста", "style": "illustration", "size": "square"},
            {"title": "Инфографика", "description": "Визуализация данных и ключевых тезисов поста", "style": "flat", "size": "tall"},
        ]

    def parse_brand_doc_to_survey(self, doc_text):
        """Разбирает текст .docx документа стратегии личного бренда
        и извлекает структурированные поля опроса через PiAPI.
        Возвращает dict с полями brand_survey.data или None при ошибке."""
        print(f"🔄 Разбор документа медиа-образа ({len(doc_text)} символов)...")

        if not self.use_piapi:
            print("⚠️ PiAPI недоступен — разбор документа невозможен")
            return None

        # Ограничиваем длину, чтобы влезть в контекст
        text = doc_text[:12000]

        prompt = f"""
Ты — аналитик. Извлеки структурированные данные из документа стратегии личного бренда и верни их в виде JSON.

Документ:
---
{text}
---

Извлеки следующие поля (если поле отсутствует в документе — оставь пустую строку ""):

{{
  "client_name": "Имя клиента",
  "client_role": "Профессия/роль",
  "client_location": "Город/регион",
  "current_situation": "Описание текущей ситуации",
  "goal_audience_number": "число подписчиков",
  "goal_audience_platform": "основная платформа",
  "goal_audience_description": "описание аудитории",
  "goal_expert_field": "область экспертизы",
  "goal_expert_speaking": "число выступлений в год",
  "goal_commercial_leads": "число заявок в месяц",
  "goal_commercial_services": "услуги",
  "goal_content_system": "описание контент-системы",
  "brand_essence": "сущность бренда одной строкой",
  "positioning_who": "кому помогаю",
  "positioning_problem": "какую проблему решаю",
  "positioning_result": "какой результат получает клиент",
  "usp": "УТП",
  "ideal_audiences": "идеальные подписчики, по строкам",
  "visual_concept": "концепция визуала",
  "color_main_name": "название основного цвета",
  "color_main_hex": "HEX основного цвета",
  "color_accent1_name": "название акцентного цвета 1",
  "color_accent1_hex": "HEX акцентного цвета 1",
  "color_accent2_name": "название акцентного цвета 2",
  "color_accent2_hex": "HEX акцентного цвета 2",
  "color_neutral": "нейтральная база",
  "typography_headings": "шрифт заголовков",
  "typography_body": "шрифт текста",
  "typography_accents": "шрифт акцентов",
  "tov_description": "описание тона",
  "tov_references": "референсы",
  "tov_axes": "оси ToV по строкам",
  "pillar1_name": "название столпа 1",
  "pillar1_goal": "цель столпа 1",
  "pillar1_formats": "форматы столпа 1 по строкам",
  "pillar1_frequency": "частота столпа 1",
  "pillar2_name": "название столпа 2",
  "pillar2_goal": "цель столпа 2",
  "pillar2_formats": "форматы столпа 2 по строкам",
  "pillar2_frequency": "частота столпа 2",
  "pillar3_name": "название столпа 3",
  "pillar3_goal": "цель столпа 3",
  "pillar3_formats": "форматы столпа 3 по строкам",
  "pillar3_frequency": "частота столпа 3",
  "special_formats": "особые форматы",
  "product_lead_magnet": "лид-магнит",
  "product_simple": "простая услуга",
  "product_converter": "услуга-конвертер",
  "product_complex": "комплексные решения",
  "product_expert": "экспертные продукты",
  "metrics_quantitative": "количественные метрики, формат: Название | Значение | Измерение, по строкам",
  "metrics_qualitative": "качественные метрики, тот же формат",
  "metrics_commercial": "коммерческие метрики, тот же формат",
  "risks": "риски, формат: Риск | Решение, по строкам",
  "recommendations": "рекомендации по строкам",
  "archetype_key_name": "название ключевого архетипа",
  "archetype_key_essence": "суть ключевого архетипа",
  "archetype_key_manifestations": "проявления по строкам",
  "archetype_supporting": "вспомогательные архетипы, формат: Название | Суть | Проявления, по строкам",
  "archetype_synthesis": "синтез архетипов",
  "archetype_table": "таблица проявлений, формат: Ситуация | Архетип | Описание, по строкам",
  "prompt_context": "контекст и личность для промпта",
  "prompt_tov": "Tone of Voice для промпта",
  "prompt_structure": "структура мысли",
  "prompt_directions": "контент-направления по строкам",
  "prompt_formats": "форматы и шаблоны",
  "prompt_technical": "технические требования к тексту"
}}

Верни ТОЛЬКО валидный JSON без пояснений и markdown.
"""

        try:
            response = requests.post(
                self.chat_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "Ты отвечаешь только валидным JSON, без markdown и пояснений."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 3000,
                    "response_format": {"type": "json_object"}
                },
                proxies=self.proxies,
                timeout=60
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"].strip()
            parsed = json.loads(content)
            print("✅ Документ медиа-образа разобран через PiAPI!")
            # Гарантируем наличие channels и funnel
            if "channels" not in parsed:
                parsed["channels"] = []
            if "funnel" not in parsed:
                parsed["funnel"] = []
            return parsed
        except Exception as e:
            print(f"⚠️ Ошибка разбора документа: {e}")
            return None

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
                    self.chat_url,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}"
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
                    proxies=self.proxies,
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

    def generate_content_plan_from_brand_profile(self, brand_data, days):
        """Генерирует контент-план на основе медиа-образа."""
        print(f"🔄 Генерация контент-плана из медиа-образа на {days} дн...")

        brand_type = brand_data.get("brand_type", "personal")
        is_org = (brand_type == "organization")
        is_community = (brand_type == "community")

        client_name = brand_data.get("client_name", "")
        org_name = brand_data.get("org_name", "")
        brand_essence = brand_data.get("brand_essence", "")
        positioning_who = brand_data.get("positioning_who", "")
        usp = brand_data.get("usp", "")
        tov_description = brand_data.get("tov_description", "")
        prompt_directions = brand_data.get("prompt_directions", "")
        pillar1_formats = brand_data.get("pillar1_formats", "")
        pillar2_formats = brand_data.get("pillar2_formats", "")
        pillar3_formats = brand_data.get("pillar3_formats", "")

        if is_community:
            entity_name = org_name
            pillar1_label = "О миссии"
            pillar2_label = "Мероприятия"
            pillar3_label = "Участники"
            entity_type = "Бизнес-сообщество / общественная организация"
        elif is_org:
            entity_name = org_name
            pillar1_label = "О продукте"
            pillar2_label = "Экспертиза"
            pillar3_label = "Вовлечение"
            entity_type = "Организация"
        else:
            entity_name = client_name
            pillar1_label = "Кто я"
            pillar2_label = "Решаю боль"
            pillar3_label = "Втягиваю"
            entity_type = "Автор"

        if self.use_piapi:
            try:
                prompt = f"""
Ты — SMM-стратег. Составь контент-план на {days} дней.

{entity_type}: {entity_name}
Сущность бренда: {brand_essence}
УТП: {usp}
Аудитория: {positioning_who}
Tone of Voice: {tov_description}

Контент-направления:
{prompt_directions}

Три столпа контента:
1. «{pillar1_label}» (форматы): {pillar1_formats}
2. «{pillar2_label}» (форматы): {pillar2_formats}
3. «{pillar3_label}» (форматы): {pillar3_formats}

Для каждого дня укажи платформу (instagram, linkedin, telegram, twitter или ad) и короткую идею поста (1 предложение), учитывая три столпа и Tone of Voice.

Верни ТОЛЬКО валидный JSON без пояснений в формате:
{{"plan": [{{"day": 1, "platform": "instagram", "idea": "..."}}, ...]}}
"""
                response = requests.post(
                    self.chat_url,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "Ты отвечаешь только валидным JSON, без markdown и пояснений."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 1200,
                        "response_format": {"type": "json_object"}
                    },
                    proxies=self.proxies,
                    timeout=30
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"].strip()
                parsed = json.loads(content)
                plan = parsed.get("plan")
                if plan:
                    print("✅ Контент-план из медиа-образа сгенерирован через PiAPI!")
                    return plan
            except Exception as e:
                print(f"⚠️ Ошибка PiAPI: {e}, использую шаблонный план")

        print("🔄 Использую шаблонный план...")
        return self._generate_template_plan(brand_essence or client_name or "бизнес", days)

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