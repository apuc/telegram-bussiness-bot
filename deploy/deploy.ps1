#!/usr/bin/env pwsh
#Requires -Version 5.1
<#
.SYNOPSIS
    Деплой ИИ Пресс-секретарь на сервер с Windows-компьютера
.DESCRIPTION
    1. Архивирует проект
    2. Загружает на сервер через SCP
    3. Подключается по SSH и запускает установку
    4. Настраивает Nginx + SSL
.NOTES
    Запуск: .\deploy.ps1
#>

[CmdletBinding()]
param(
    [string]$ServerIP = "31.28.9.200",
    [string]$Username = "root",
    [string]$Password = "123edcxzaqws",
    [string]$Domain = "press.my-dpr.ru",
    [string]$RemotePath = "/opt/pressa",
    [string]$LocalProjectPath = "C:\python\pressa"
)

# === ЦВЕТА ===
$Red = "`e[31m"
$Green = "`e[32m"
$Yellow = "`e[33m"
$Blue = "`e[34m"
$NC = "`e[0m"

function Write-Status($msg) { Write-Host "${Green}[✓]${NC} $msg" }
function Write-Info($msg) { Write-Host "${Blue}[i]${NC} $msg" }
function Write-Warning($msg) { Write-Host "${Yellow}[!]${NC} $msg" }
function Write-Error($msg) { Write-Host "${Red}[✗]${NC} $msg" }

# === ПРОВЕРКА SSH/SCP ===
Write-Info "Проверка наличия SSH и SCP..."

$ssh = Get-Command ssh -ErrorAction SilentlyContinue
$scp = Get-Command scp -ErrorAction SilentlyContinue

if (-not $ssh -or -not $scp) {
    Write-Error "SSH или SCP не найдены!"
    Write-Info "Установи OpenSSH Client:"
    Write-Info "  Параметры → Приложения → Дополнительные компоненты → OpenSSH Client"
    exit 1
}

Write-Status "SSH и SCP найдены"

# === СОЗДАНИЕ АРХИВА ===
Write-Info "Создание архива проекта..."

$TempDir = "$env:TEMP\pressa-deploy"
$ArchiveName = "pressa-deploy.tar.gz"
$ArchivePath = "$env:TEMP\$ArchiveName"

# Удаляем старый архив
if (Test-Path $ArchivePath) {
    Remove-Item $ArchivePath -Force
}

# Создаём временную копию без лишнего
if (Test-Path $TempDir) {
    Remove-Item $TempDir -Recurse -Force
}
New-Item -ItemType Directory -Path $TempDir | Out-Null

# Копируем нужные файлы
$ItemsToCopy = @(
    "cabinet_service",
    "ai_core",
    "config.py",
    "requirements.txt",
    "deploy"
)

foreach ($item in $ItemsToCopy) {
    $src = Join-Path $LocalProjectPath $item
    if (Test-Path $src) {
        Copy-Item -Path $src -Destination $TempDir -Recurse -Force
    }
}

# Обновляем домен в скриптах
$nginxScript = Join-Path $TempDir "deploy\nginx-setup.sh"
if (Test-Path $nginxScript) {
    $content = Get-Content $nginxScript -Raw
    $content = $content.Replace('твой_домен.com', $Domain)
    Set-Content -Path $nginxScript -Value $content -NoNewline
}

$sslScript = Join-Path $TempDir "deploy\ssl-setup.sh"
if (Test-Path $sslScript) {
    $content = Get-Content $sslScript -Raw
    $content = $content.Replace('твой_домен.com', $Domain)
    $content = $content.Replace('твой_email@example.com', "admin@$Domain")
    Set-Content -Path $sslScript -Value $content -NoNewline
}

# Создаём архив
Write-Info "Архивирование..."
Set-Location $env:TEMP
# Используем tar если есть, иначе Compress-Archive
$tar = Get-Command tar -ErrorAction SilentlyContinue
if ($tar) {
    tar -czf $ArchiveName -C $TempDir .
} else {
    Compress-Archive -Path "$TempDir\*" -DestinationPath "$env:TEMP\pressa-deploy.zip" -Force
    $ArchiveName = "pressa-deploy.zip"
    $ArchivePath = "$env:TEMP\$ArchiveName"
}

Write-Status "Архив создан: $ArchivePath ($((Get-Item $ArchivePath).Length / 1MB | Format-Number -Format '0.0') MB)"

# === ЗАГРУЗКА НА СЕРВЕР ===
Write-Info "Загрузка на сервер $ServerIP..."

# Создаём директорию на сервере
$sshCmd = "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ${Username}@${ServerIP}"
$createDir = "mkdir -p $RemotePath && rm -rf $RemotePath/*"

Write-Info "Создание директории на сервере..."
$createDir | ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ${Username}@${ServerIP} "bash -s"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Не удалось подключиться по SSH!"
    Write-Info "Проверь:"
    Write-Info "  1. IP-адрес сервера"
    Write-Info "  2. Логин и пароль"
    Write-Info "  3. Доступность порта 22"
    exit 1
}

Write-Status "Подключение установлено"

# Загружаем архив
Write-Info "Загрузка архива..."
scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null $ArchivePath "${Username}@${ServerIP}:${RemotePath}/"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Ошибка загрузки файлов!"
    exit 1
}

Write-Status "Файлы загружены"

# === РАСПАКОВКА И УСТАНОВКА ===
Write-Info "Распаковка и установка на сервере..."

$remoteCommands = @"
cd $RemotePath

# Распаковка
if [ -f "$ArchiveName" ]; then
    tar -xzf "$ArchiveName"
    rm "$ArchiveName"
elif [ -f "pressa-deploy.zip" ]; then
    apt-get install -y unzip
    unzip -q "pressa-deploy.zip"
    rm "pressa-deploy.zip"
fi

# Перемещаем файлы из подпапки
if [ -d "cabinet_service" ]; then
    # Уже в корне
    echo "Файлы на месте"
else
    # Ищем папку с файлами
    for dir in */; do
        if [ -d "\$dir/cabinet_service" ]; then
            mv "\$dir"/* .
            rm -rf "\$dir"
            break
        fi
    done
fi

# Установка прав
chmod +x deploy/*.sh

# Запуск установки
echo "=== Запуск install.sh ==="
cd deploy
./install.sh

echo ""
echo "=== Установка завершена ==="
echo ""
echo "Не забудь настроить .env файл:"
echo "  nano $RemotePath/.env"
echo ""
echo "Перезапуск сервиса:"
echo "  systemctl restart pressa"
"@

Write-Info "Запуск установочных скриптов (это займет 5-10 минут)..."
$remoteCommands | ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ${Username}@${ServerIP} "bash -s"

if ($LASTEXITCODE -ne 0) {
    Write-Warning "Возможны ошибки при установке. Проверь логи на сервере."
}

# === НАСТРОЙКА NGINX И SSL ===
Write-Info "Настройка Nginx и SSL..."

$nginxCommands = @"
cd $RemotePath/deploy

# Nginx
sed -i "s/твой_домен.com/$Domain/g" nginx-setup.sh
./nginx-setup.sh

# SSL
sed -i "s/твой_домен.com/$Domain/g" ssl-setup.sh
sed -i "s/твой_email@example.com/admin@$Domain/g" ssl-setup.sh
./ssl-setup.sh

echo ""
echo "=== Готово! ==="
echo "Сайт доступен по адресу: https://$Domain"
"@

$nginxCommands | ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ${Username}@${ServerIP} "bash -s"

# === ФИНАЛ ===
Write-Status "Деплой завершён!"
Write-Info ""
Write-Info "🌐 Сайт: https://$Domain"
Write-Info "📁 Проект: $RemotePath"
Write-Info ""
Write-Info "Полезные команды:"
Write-Info "  ssh ${Username}@${ServerIP}"
Write-Info "  sudo systemctl status pressa"
Write-Info "  sudo journalctl -u pressa -f"
Write-Info ""
Write-Warning "⚠️  Не забудь настроить .env файл на сервере!"
Write-Info "  ssh ${Username}@${ServerIP} 'nano $RemotePath/.env'"

# Очистка
if (Test-Path $TempDir) {
    Remove-Item $TempDir -Recurse -Force
}

Set-Location $LocalProjectPath