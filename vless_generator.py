#!/usr/bin/env python3
"""
Генератор VLESS ключа для одного сервера
Без бота, просто создает готовый ключ
"""

import os
import json
import subprocess
import uuid
import time
import socket
import requests
from datetime import datetime

# ============================================
# КОНФИГУРАЦИЯ
# ============================================

# ⚠️ ИЗМЕНИТЕ ЭТИ ПАРАМЕТРЫ:
DOMAIN = "servisdlyaip.com"  # Ваш домен или IP
PORT = 228  # Порт для подключения
PORT_WS = 8443  # Порт для WebSocket (опционально)

# Автоматически определим IP
def get_public_ip():
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=5)
        return response.json()['ip']
    except:
        try:
            response = requests.get('https://ifconfig.me/ip', timeout=5)
            return response.text.strip()
        except:
            return "0.0.0.0"

SERVER_IP = get_public_ip()
SERVER_DOMAIN = DOMAIN  # Используем домен, если есть

# Генерируем UUID
SERVER_UUID = str(uuid.uuid4())

# ============================================
# УСТАНОВКА XRAY
# ============================================

def install_xray():
    """Устанавливает Xray"""
    print("🚀 Установка Xray...")
    
    # Скачиваем и устанавливаем Xray
    install_cmd = 'bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install'
    subprocess.run(install_cmd, shell=True, check=True)
    
    print("✅ Xray установлен")

# ============================================
# НАСТРОЙКА XRAY
# ============================================

def configure_xray():
    """Настраивает Xray с VLESS"""
    print("⚙️ Настройка Xray...")
    
    # Создаем конфигурацию
    config = {
        "inbounds": [
            # Основной вход (TCP + TLS)
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
            # WebSocket вход (для обхода блокировок)
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
    with open("/tmp/config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    # Перемещаем в системную папку
    subprocess.run(f"sudo mv /tmp/config.json {config_path}", shell=True, check=True)
    
    # Запускаем Xray
    subprocess.run("sudo systemctl restart xray", shell=True, check=True)
    subprocess.run("sudo systemctl enable xray", shell=True, check=True)
    
    print(f"✅ Xray настроен на порту {PORT} (TCP) и {PORT_WS} (WS)")
    
    return config

# ============================================
# ГЕНЕРАЦИЯ VLESS ССЫЛОК
# ============================================

def generate_vless_links(ip, uuid, port, domain=None):
    """Генерирует VLESS ссылки"""
    
    # Используем домен или IP
    host = domain if domain else ip
    
    # VLESS TCP с TLS
    vless_tcp = (
        f"vless://{uuid}@{host}:{port}"
        f"?security=tls"
        f"&encryption=none"
        f"&flow=xtls-rprx-vision"
        f"&fp=chrome"
        f"&type=tcp"
        f"&sni={host}"
        f"#VLESS_TCP"
    )
    
    # VLESS WebSocket (без TLS для простоты)
    vless_ws = (
        f"vless://{uuid}@{host}:{PORT_WS}"
        f"?encryption=none"
        f"&type=ws"
        f"&path=%2Fvless"
        f"#VLESS_WS"
    )
    
    # VLESS TCP с Reality (более безопасный)
    vless_reality = (
        f"vless://{uuid}@{host}:{port}"
        f"?security=reality"
        f"&encryption=none"
        f"&pbk=Wrx6xXkFJqJiZrY2Q1QzY2MzA3NjE4MDk0MzU3NjE4"
        f"&fp=chrome"
        f"&type=tcp"
        f"&sni=cloudflare.com"
        f"&sid=6f1a"
        f"#VLESS_REALITY"
    )
    
    return {
        "tcp": vless_tcp,
        "ws": vless_ws,
        "reality": vless_reality
    }

# ============================================
# СОЗДАНИЕ КОНФИГА ДЛЯ HAPP
# ============================================

def create_happ_config(ip, uuid, port):
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
                            "address": ip,
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
                        "serverName": ip
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
            subprocess.run(cmd, shell=True, check=True)
        except:
            pass
    
    print(f"✅ Порты {PORT} и {PORT_WS} открыты")

# ============================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================

def main():
    print("=" * 50)
    print("🚀 ГЕНЕРАТОР VLESS VPN")
    print("=" * 50)
    print()
    
    # Получаем информацию о сервере
    ip = SERVER_IP
    domain = SERVER_DOMAIN
    
    print(f"🌐 IP сервера: {ip}")
    print(f"🏠 Домен: {domain}")
    print(f"🔑 UUID: {SERVER_UUID}")
    print(f"🔌 Порт: {PORT}")
    print()
    
    # Устанавливаем Xray
    try:
        install_xray()
    except Exception as e:
        print(f"⚠️ Ошибка установки Xray: {e}")
        print("Продолжаем...")
    
    # Настраиваем Xray
    try:
        configure_xray()
    except Exception as e:
        print(f"⚠️ Ошибка настройки Xray: {e}")
        print("Продолжаем...")
    
    # Открываем порты
    try:
        open_ports()
    except Exception as e:
        print(f"⚠️ Ошибка открытия портов: {e}")
    
    # Генерируем ссылки
    links = generate_vless_links(domain, SERVER_UUID, PORT)
    
    # Создаем конфиг для HAPP
    happ_config = create_happ_config(domain, SERVER_UUID, PORT)
    
    # Сохраняем результаты
    result_text = f"""
╔══════════════════════════════════════════════════════════════╗
║              ✅ VLESS VPN ГОТОВ К ИСПОЛЬЗОВАНИЮ              ║
╚══════════════════════════════════════════════════════════════╝

📌 ИНФОРМАЦИЯ О СЕРВЕРЕ:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🌐 IP: {ip}
  🏠 Домен: {domain}
  🔑 UUID: {SERVER_UUID}
  🔌 Порт: {PORT}
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

3️⃣ Reality (экспериментальный):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{links['reality']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📱 КАК ИСПОЛЬЗОВАТЬ:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  • Android: V2RayNG → Import from clipboard
  • iOS: Shadowrocket → Import from clipboard  
  • Windows: V2RayN → Import from clipboard
  • HAPP: Скопируйте конфиг из vless_config.json
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ СЕРВЕР БУДЕТ РАБОТАТЬ 6 ЧАСОВ
"""
    
    # Сохраняем текст
    with open("vless_result.txt", "w") as f:
        f.write(result_text)
    
    # Сохраняем конфиг для HAPP
    with open("vless_config.json", "w") as f:
        json.dump(happ_config, f, indent=2)
    
    # Выводим результат
    print(result_text)
    
    # Дополнительная информация
    print("\n" + "=" * 50)
    print("📁 Файлы сохранены:")
    print("  • vless_result.txt - VLESS ссылки")
    print("  • vless_config.json - Конфиг для HAPP")
    print("=" * 50)

if __name__ == "__main__":
    main()
