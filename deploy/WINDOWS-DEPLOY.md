# Деплой с Windows на сервер

## ⚡ Быстрый старт

1. **Открой PowerShell** (от имени администратора не обязательно)

2. **Перейди в папку проекта:**
```powershell
cd C:\python\pressa\deploy
```

3. **Запусти деплой:**
```powershell
.\deploy.ps1
```

## 📋 Что делает скрипт

1. ✅ Архивирует проект (исключая venv, __pycache__)
2. ✅ Подключается к серверу по SSH
3. ✅ Загружает файлы через SCP
4. ✅ Распаковывает на сервере
5. ✅ Запускает `install.sh` (установка Python, Nginx, SSL)
6. ✅ Настраивает домен `press.my-dpr.ru`
7. ✅ Получает SSL сертификат

## ⏱️ Время выполнения

- Загрузка: 1-2 минуты
- Установка на сервере: 5-10 минут
- **Итого: ~10 минут**

## 🔧 Параметры (опционально)

Если нужно изменить настройки:

```powershell
.\deploy.ps1 -ServerIP "31.28.9.200" -Domain "press.my-dpr.ru"
```

Доступные параметры:
- `-ServerIP` — IP сервера
- `-Username` — логин (по умолчанию root)
- `-Password` — пароль
- `-Domain` — домен
- `-RemotePath` — путь на сервере (по умолчанию /opt/pressa)
- `-LocalProjectPath` — путь к проекту на компьютере

## 🆘 Если не работает

### Ошибка "SSH не найден"

Установи OpenSSH Client:
1. Параметры → Приложения → Дополнительные компоненты
2. Добавить компонент → OpenSSH Client
3. Перезагрузи PowerShell

### Ошибка подключения

Проверь:
```powershell
# Пинг сервера
ping 31.28.9.200

# Проверка SSH
ssh root@31.28.9.200
```

### Ручной деплой (если скрипт не сработал)

1. Запакуй проект в zip
2. Загрузи через FileZilla / WinSCP на сервер
3. Подключись по SSH через PuTTY
4. Выполни команды из `install.sh` вручную

## ✅ После деплоя

1. **Настрой .env файл:**
```bash
ssh root@31.28.9.200
nano /opt/pressa/.env
```

Заполни:
```env
BOT_TOKEN=твой_токен_бота
PIAPI_API_KEY=твой_piapi_ключ
PROXY_URL=http://user:pass@host:port
CABINET_URL=https://press.my-dpr.ru
```

2. **Перезапусти сервис:**
```bash
systemctl restart pressa
```

3. **Проверь статус:**
```bash
systemctl status pressa
journalctl -u pressa -f
```

## 🌐 Доступ

После успешного деплоя:
- **Сайт:** https://press.my-dpr.ru
- **API:** https://press.my-dpr.ru/api/

## 📞 Поддержка

Если что-то пошло не так — проверь логи:
```bash
# На сервере
journalctl -u pressa -n 50
tail -f /var/log/nginx/pressa-error.log
```