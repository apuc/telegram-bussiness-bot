import random
import os
from groq import Groq
from config import GROQ_API_KEY

class ContentGenerator:
    def __init__(self):
        """Инициализация генератора контента"""
        print("🔄 Инициализация ContentGenerator...")
        
        # Проверяем, есть ли ключ Groq
        if GROQ_API_KEY:
            try:
                self.client = Groq(api_key=GROQ_API_KEY)
                self.model = "llama-3.3-70b-versatile"
                self.use_groq = True
                print("✅ Groq API подключен!")
            except Exception as e:
                print(f"⚠️ Ошибка подключения Groq: {e}")
                self.use_groq = False
        else:
            print("⚠️ Groq API ключ не найден, использую шаблоны")
            self.use_groq = False
        
        # Шаблоны для запасного варианта (если Groq не работает)
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
        
        # Пробуем сгенерировать через Groq
        if self.use_groq:
            try:
                post = self._generate_with_groq(business_type, business_description, platform)
                if post and len(post) > 20:
                    print("✅ Пост сгенерирован через Groq!")
                    return post
            except Exception as e:
                print(f"⚠️ Ошибка Groq: {e}, использую шаблоны")
        
        # Если Groq не работает - используем шаблоны
        print("🔄 Использую шаблоны...")
        return self._generate_with_templates(business_type, business_description, platform)
    
    def _generate_with_groq(self, business_type, business_description, platform):
        """Генерация через Groq API"""
        
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
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Ты профессиональный копирайтер. Пиши ярко, полезно и вовлекающе."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.9,
            max_tokens=500
        )
        
        return response.choices[0].message.content.strip()
    
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