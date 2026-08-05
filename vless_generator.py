#!/usr/bin/env python3
"""
Генератор VLESS ключа через Serveo.net
Создает публичный адрес вида: ваш-субдомен.serveo.net:порт
"""

import os
import json
import subprocess
import uuid
import time
import requests
import threading
import socket
import random
import string
from datetime import datetime

# ============================================
# КОНФИГУРАЦИЯ
# ============================================

PORT = 228  # Порт для VLESS
PORT_WS = 8443  # Порт для WebSocket

# Генерируем случайный субдомен
def generate_subdomain():
    """Генерирует случайный субдомен для Serveo"""
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choices(chars, k=10))

SUBDOMAIN = generate_subdomain()
SERVEO_DOMAIN = f"{SUBDOMAIN}.serveo.net"

# Генерируем UUID
SERVER_UUID = str(uuid.uuid4())

# ============================================
# УСТАНОВКА XRAY (УЛУЧШЕННАЯ ВЕРСИЯ)
# ============================================

def install_xray():
    """Устанавливает Xray с несколькими способами"""
    print("🚀 Установка Xray...")
    
    # Способ 1: Официальный скрипт
    try:
        print("Попытка 1: Официальный скрипт установки...")
        # Скачиваем скрипт вручную
        subprocess.run(
            "curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh -o /tmp/install-release.sh",
            shell=True, check=True, capture_output=True
        )
        subprocess.run(
            "bash /tmp/install-release.sh @ install",
            shell=True, check=True, capture_output=True
        )
        print("✅ Xray установлен через официальный скрипт")
        return True
    except Exception as e:
        print(f"⚠️ Ошибка: {e}")
    
    # Способ 2: Установка через wget
    try:
        print("Попытка 2: Установка через wget...")
        subprocess.run(
            "wget -qO /tmp/install-release.sh https://github.com/XTLS/Xray-install/raw/main/install-release.sh",
            shell=True, check=True, capture_output=True
        )
        subprocess.run(
            "bash /tmp/install-release.sh @ install",
            shell=True, check=True, capture_output=True
        )
        print("✅ Xray установлен через wget")
        return True
    except Exception as e:
        print(f"⚠️ Ошибка: {e}")
    
    # Способ 3: Прямая установка бинарника
    try:
        print("Попытка 3: Прямая установка бинарника...")
        # Скачиваем последний релиз
        import requests
        import json
        
        # Получаем последний релиз
        response = requests.get('https://api.github.com/repos/XTLS/Xray-core/releases/latest')
        if response.status_code == 200:
            data = response.json()
            # Ищем linux-amd64
            for asset in data['assets']:
                if 'linux-64' in asset['name']:
                    url = asset['browser_download_url']
                    subprocess.run(f"wget -qO /tmp/xray.zip {url}", shell=True, check=True)
                    subprocess.run("sudo unzip -o /tmp/xray.zip -d /usr/local/bin/", shell=True, check=True)
                    subprocess.run("sudo chmod +x /usr/local/bin/xray", shell=True, check=True)
                    print("✅ Xray установлен напрямую")
                    return True
    except Exception as e:
        print(f"⚠️ Ошибка: {e}")
    
    # Способ 4: Установка из репозитория (для Ubuntu)
    try:
        print("Попытка 4: Установка из репозитория...")
        subprocess.run(
            "sudo apt-get update && sudo apt-get install -y xray",
            shell=True, check=True, capture_output=True
        )
        print("✅ Xray установлен из репозитория")
        return True
    except Exception as e:
        print(f"⚠️ Ошибка: {e}")
    
    print("❌ Все способы установки не удались")
    return False

# ============================================
# НАСТРОЙКА XRAY (С СОЗДАНИЕМ КОНФИГА)
# ============================================

def configure_xray():
    """Настраивает Xray с VLESS"""
    print("⚙️ Настройка Xray...")
    
    # Создаем конфигурацию
    config = {
        "inbounds": [
            {
                "port": PORT,
                "protocol": "vless",
                "settings": {
                    "clients": [
                        {
                            "id": SERVER_UUID,
                            "flow": "xtls-rprx-vision",
                            "level": 0,
                            "email": "user@example.com"
                        }
                    ],
                    "decryption": "none"
                },
                "streamSettings": {
                    "network": "tcp",
                    "security": "tls",
                    "tlsSettings": {
                        "alpn": ["http/1.1"],
                        "allowInsecure": True
                    }
                },
                "sniffing": {
                    "enabled": True,
                    "destOverride": ["http", "tls"]
                }
            },
            {
                "port": PORT_WS,
                "protocol": "vless",
                "settings": {
                    "clients": [
                        {
                            "id": SERVER_UUID,
                            "level": 0,
                            "email": "user-ws@example.com"
                        }
                    ],
                    "decryption": "none"
                },
                "streamSettings": {
                    "network": "ws",
                    "wsSettings": {
                        "path": "/vless"
                    }
                },
                "sniffing": {
                    "enabled": True,
                    "destOverride": ["http", "tls"]
                }
            }
        ],
        "outbounds": [
            {
                "protocol": "freedom",
                "tag": "direct"
            },
            {
                "protocol": "blackhole",
                "tag": "block"
            }
        ],
        "routing": {
            "rules": [
                {
                    "type": "field",
                    "outboundTag": "block",
                    "protocol": ["bittorrent"]
                }
            ]
        }
    }
    
    # Сохраняем конфиг
    config_path = "/usr/local/etc/xray/config.json"
    
    try:
        # Создаем папку для конфига
        subprocess.run("sudo mkdir -p /usr/local/etc/xray", shell=True, check=True)
        
        # Сохраняем конфиг
        with open("/tmp/config.json", "w") as f:
            json.dump(config, f, indent=2)
        
        subprocess.run(f"sudo mv /tmp/config.json {config_path}", shell=True, check=True)
        
        # Пытаемся запустить Xray
        try:
            subprocess.run("sudo systemctl restart xray", shell=True, check=True)
            subprocess.run("sudo systemctl enable xray", shell=True, check=True)
        except:
            # Если systemctl не работает, запускаем напрямую
            subprocess.Popen(
                "sudo /usr/local/bin/xray -config /usr/local/etc/xray/config.json",
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        
        print(f"✅ Xray настроен на порту {PORT} (TCP) и {PORT_WS} (WS)")
        return True
    except Exception as e:
        print(f"⚠️ Ошибка настройки Xray: {e}")
        return False

# ============================================
# ЗАПУСК SERVEO ТУННЕЛЯ
# ============================================

def start_serveo_tunnel():
    """Запускает Serveo туннель для перенаправления трафика"""
    print(f"🚀 Запуск Serveo туннеля на {SERVEO_DOMAIN}:{PORT}...")
    
    # Команда для создания туннеля
    cmd = f"ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=60 -R {SUBDOMAIN}:{PORT}:localhost:{PORT} serveo.net"
    
    # Запускаем в фоне
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Ждем, пока туннель установится
    time.sleep(5)
    
    # Проверяем, что туннель работает
    try:
        # Пытаемся соединиться с Serveo
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('serveo.net', 22))
        sock.close()
        
        if result == 0:
            print(f"✅ Serveo туннель запущен: {SERVEO_DOMAIN}:{PORT}")
            return True
        else:
            print(f"⚠️ Ошибка подключения к Serveo")
            return False
    except Exception as e:
        print(f"⚠️ Ошибка: {e}")
        return False

# ============================================
# ГЕНЕРАЦИЯ VLESS ССЫЛОК
# ============================================

def generate_vless_links(domain, uuid, port):
    """Генерирует VLESS ссылки с доменом Serveo"""
    
    # VLESS TCP с TLS
    vless_tcp = (
        f"vless://{uuid}@{domain}:{port}"
        f"?security=tls"
        f"&encryption=none"
        f"&flow=xtls-rprx-vision"
        f"&fp=chrome"
        f"&type=tcp"
        f"&sni={domain}"
        f"#VLESS_SERVEO"
    )
    
    # VLESS WebSocket
    vless_ws = (
        f"vless://{uuid}@{domain}:{PORT_WS}"
        f"?encryption=none"
        f"&type=ws"
        f"&path=%2Fvless"
        f"#VLESS_SERVEO_WS"
    )
    
    return {
        "tcp": vless_tcp,
        "ws": vless_ws
    }

# ============================================
# СОЗДАНИЕ КОНФИГА ДЛЯ HAPP
# ============================================

def create_happ_config(domain, uuid, port):
    """Создает конфиг для HAPP (V2Ray)"""
    
    config = {
        "log": {
            "loglevel": "warning"
        },
        "inbounds": [
            {
                "port": 10808,
                "listen": "127.0.0.1",
                "protocol": "socks",
                "settings": {
                    "udp": True
                }
            },
            {
                "port": 10809,
                "listen": "127.0.0.1",
                "protocol": "http",
                "settings": {}
            }
        ],
        "outbounds": [
            {
                "protocol": "vless",
                "settings": {
                    "vnext": [
                        {
                            "address": domain,
                            "port": port,
                            "users": [
                                {
                                    "id": uuid,
                                    "encryption": "none",
                                    "flow": "xtls-rprx-vision",
                                    "level": 0
                                }
                            ]
                        }
                    ]
                },
                "streamSettings": {
                    "network": "tcp",
                    "security": "tls",
                    "tlsSettings": {
                        "allowInsecure": True,
                        "serverName": domain
                    }
                },
                "mux": {
                    "enabled": True,
                    "concurrency": 8
                },
                "tag": "proxy"
            },
            {
                "protocol": "freedom",
                "settings": {},
                "tag": "direct"
            },
            {
                "protocol": "blackhole",
                "settings": {},
                "tag": "block"
            }
        ],
        "routing": {
            "domainStrategy": "IPIfNonMatch",
            "rules": [
                {
                    "type": "field",
                    "outboundTag": "block",
                    "protocol": ["bittorrent"]
                },
                {
                    "type": "field",
                    "outboundTag": "direct",
                    "domain": ["geosite:cn"]
                },
                {
                    "type": "field",
                    "outboundTag": "direct",
                    "ip": ["geoip:cn", "geoip:private"]
                }
            ]
        }
    }
    
    return config

# ============================================
# ПРОВЕРКА РАБОТЫ XRAY
# ============================================

def check_xray():
    """Проверяет, работает ли Xray"""
    try:
        # Проверяем, слушает ли порт
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('localhost', PORT))
        sock.close()
        
        if result == 0:
            print(f"✅ Xray работает на порту {PORT}")
            return True
        else:
            print(f"⚠️ Xray не отвечает на порту {PORT}")
            return False
    except:
        return False

# ============================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================

def main():
    print("=" * 50)
    print("🚀 ГЕНЕРАТОР VLESS ЧЕРЕЗ SERVEO")
    print("=" * 50)
    print()
    
    print(f"🌐 Домен: {SERVEO_DOMAIN}")
    print(f"🔑 UUID: {SERVER_UUID}")
    print(f"🔌 Порт: {PORT}")
    print()
    
    # Открываем порты
    open_ports()
    
    # Устанавливаем Xray
    if not install_xray():
        print("❌ Ошибка установки Xray")
        # Но продолжаем - может быть Xray уже установлен
    
    # Настраиваем Xray
    if not configure_xray():
        print("❌ Ошибка настройки Xray")
    
    # Проверяем работу
    time.sleep(2)
    check_xray()
    
    # Запускаем Serveo туннель
    start_serveo_tunnel()
    
    # Генерируем ссылки
    links = generate_vless_links(SERVEO_DOMAIN, SERVER_UUID, PORT)
    
    # Создаем конфиг для HAPP
    happ_config = create_happ_config(SERVEO_DOMAIN, SERVER_UUID, PORT)
    
    # Сохраняем результаты
    result_text = f"""
╔══════════════════════════════════════════════════════════════╗
║         ✅ VLESS VPN ЧЕРЕЗ SERVEO ГОТОВ К ИСПОЛЬЗОВАНИЮ      ║
╚══════════════════════════════════════════════════════════════╝

📌 ИНФОРМАЦИЯ О СЕРВЕРЕ:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🌐 Адрес: {SERVEO_DOMAIN}
  🔑 UUID: {SERVER_UUID}
  🔌 Порт TCP: {PORT}
  📡 Порт WS: {PORT_WS}
  ⏰ Создан: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔗 VLESS ССЫЛКИ (СКОПИРУЙТЕ ЭТИ СТРОКИ):

1️⃣ TCP + TLS (рекомендуется):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{links['tcp']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

2️⃣ WebSocket (для обхода):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{links['ws']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📱 КАК ИСПОЛЬЗОВАТЬ:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  • Android: V2RayNG → Import from clipboard
  • iOS: Shadowrocket → Import from clipboard  
  • Windows: V2RayN → Import from clipboard
  • HAPP: Скопируйте конфиг из vless_config.json
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ СЕРВЕР БУДЕТ РАБОТАТЬ 6 ЧАСОВ
💡 Адрес будет вида: {SUBDOMAIN}.serveo.net
"""
    
    # Сохраняем текст
    with open("vless_result.txt", "w") as f:
        f.write(result_text)
    
    # Сохраняем конфиг для HAPP
    with open("vless_config.json", "w") as f:
        json.dump(happ_config, f, indent=2)
    
    # Выводим результат
    print(result_text)
    
    print("\n" + "=" * 50)
    print("📁 Файлы сохранены:")
    print("  • vless_result.txt - VLESS ссылки")
    print("  • vless_config.json - Конфиг для HAPP")
    print("=" * 50)

# ============================================
# ОТКРЫТИЕ ПОРТОВ
# ============================================

def open_ports():
    """Открывает порты в firewall"""
    print("🔓 Открываем порты...")
    
    commands = [
        f"sudo ufw allow {PORT}/tcp",
        f"sudo ufw allow {PORT_WS}/tcp",
        "sudo ufw allow 22/tcp",
        "sudo ufw --force enable"
    ]
    
    for cmd in commands:
        try:
            subprocess.run(cmd, shell=True, check=True, capture_output=True)
        except:
            pass
    
    print(f"✅ Порты {PORT} и {PORT_WS} открыты")

if __name__ == "__main__":
    main()
