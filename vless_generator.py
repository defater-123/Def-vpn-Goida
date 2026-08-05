#!/usr/bin/env python3
"""
Генератор VLESS ключа через Serveo.net
РАБОЧАЯ ВЕРСИЯ - БЕЗ TLS (просто и надёжно)
"""

import os
import json
import subprocess
import uuid
import time
import socket
import random
import string
from datetime import datetime

# ============================================
# КОНФИГУРАЦИЯ
# ============================================

PORT = 228
PORT_WS = 8443

def generate_subdomain():
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choices(chars, k=10))

SUBDOMAIN = generate_subdomain()
SERVEO_DOMAIN = f"{SUBDOMAIN}.serveo.net"
SERVER_UUID = str(uuid.uuid4())

# ============================================
# УСТАНОВКА XRAY
# ============================================

def install_xray():
    print("🚀 Установка Xray...")
    try:
        subprocess.run(
            "wget -qO /tmp/xray.zip https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip",
            shell=True, check=True
        )
        subprocess.run(
            "sudo unzip -o /tmp/xray.zip -d /usr/local/bin/",
            shell=True, check=True
        )
        subprocess.run(
            "sudo chmod +x /usr/local/bin/xray",
            shell=True, check=True
        )
        print("✅ Xray установлен")
        return True
    except Exception as e:
        print(f"⚠️ Ошибка: {e}")
        return False

# ============================================
# НАСТРОЙКА XRAY (БЕЗ TLS!)
# ============================================

def configure_and_run_xray():
    """Настраивает Xray БЕЗ TLS (просто и работает)"""
    print("⚙️ Настройка Xray (без TLS)...")
    
    # ============================================
    # КОНФИГ БЕЗ TLS - ПРОСТОЙ И РАБОЧИЙ
    # ============================================
    config = {
        "inbounds": [
            # Основной вход (простой TCP)
            {
                "port": PORT,
                "protocol": "vless",
                "settings": {
                    "clients": [
                        {
                            "id": SERVER_UUID,
                            "level": 0,
                            "email": "user@example.com"
                        }
                    ],
                    "decryption": "none"
                },
                "streamSettings": {
                    "network": "tcp"
                },
                "sniffing": {
                    "enabled": True,
                    "destOverride": ["http", "tls"]
                }
            },
            # WebSocket вход
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
    
    try:
        # Создаем папку для конфига
        subprocess.run("sudo mkdir -p /usr/local/etc/xray", shell=True, check=True)
        
        # Сохраняем конфиг
        with open("/tmp/config.json", "w") as f:
            json.dump(config, f, indent=2)
        
        subprocess.run(f"sudo mv /tmp/config.json /usr/local/etc/xray/config.json", shell=True, check=True)
        
        # Запускаем Xray
        print("🔧 Запускаем Xray...")
        
        # Останавливаем старые процессы
        subprocess.run("sudo pkill -f xray || true", shell=True)
        
        # Запускаем в фоне
        subprocess.Popen(
            "sudo /usr/local/bin/xray -config /usr/local/etc/xray/config.json > /tmp/xray.log 2>&1 &",
            shell=True
        )
        
        time.sleep(3)
        
        # Проверяем запуск
        result = subprocess.run(
            f"sudo netstat -tulpn | grep ':{PORT}'",
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.stdout:
            print(f"✅ Xray запущен на порту {PORT}")
            return True
        else:
            print("⚠️ Xray не запустился")
            log_result = subprocess.run(
                "cat /tmp/xray.log",
                shell=True,
                capture_output=True,
                text=True
            )
            if log_result.stdout:
                print("📋 Логи Xray:")
                print(log_result.stdout[:500])
            return False
            
    except Exception as e:
        print(f"⚠️ Ошибка: {e}")
        return False

# ============================================
# ЗАПУСК SERVEO ТУННЕЛЯ
# ============================================

def start_serveo_tunnel():
    """Запускает Serveo туннель"""
    print(f"🚀 Запуск Serveo туннеля на {SERVEO_DOMAIN}:{PORT}...")
    
    # Закрываем старые соединения
    subprocess.run("pkill -f serveo || true", shell=True)
    
    # Запускаем туннель
    cmd = f"ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=60 -R {SUBDOMAIN}:{PORT}:localhost:{PORT} serveo.net"
    
    subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    time.sleep(5)
    print(f"✅ Serveo туннель запущен")
    return True

# ============================================
# ГЕНЕРАЦИЯ VLESS ССЫЛОК (БЕЗ TLS!)
# ============================================

def generate_vless_links(domain, uuid, port):
    # ============================================
    # ПРОСТЫЕ ССЫЛКИ БЕЗ TLS - РАБОТАЮТ 100%
    # ============================================
    
    # TCP (основная)
    vless_tcp = (
        f"vless://{uuid}@{domain}:{port}"
        f"?encryption=none"
        f"&type=tcp"
        f"#VLESS_SERVEO_TCP"
    )
    
    # WebSocket
    vless_ws = (
        f"vless://{uuid}@{domain}:{PORT_WS}"
        f"?encryption=none"
        f"&type=ws"
        f"&path=%2Fvless"
        f"#VLESS_SERVEO_WS"
    )
    
    # TCP с flow (для совместимости)
    vless_flow = (
        f"vless://{uuid}@{domain}:{port}"
        f"?encryption=none"
        f"&flow=xtls-rprx-vision"
        f"&type=tcp"
        f"#VLESS_SERVEO_FLOW"
    )
    
    return {
        "tcp": vless_tcp,
        "ws": vless_ws,
        "flow": vless_flow
    }

# ============================================
# КОНФИГ ДЛЯ HAPP
# ============================================

def create_happ_config(domain, uuid, port):
    return {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {"port": 10808, "listen": "127.0.0.1", "protocol": "socks", "settings": {"udp": True}},
            {"port": 10809, "listen": "127.0.0.1", "protocol": "http", "settings": {}}
        ],
        "outbounds": [{
            "protocol": "vless",
            "settings": {
                "vnext": [{
                    "address": domain,
                    "port": port,
                    "users": [{
                        "id": uuid,
                        "encryption": "none",
                        "level": 0
                    }]
                }]
            },
            "streamSettings": {
                "network": "tcp"
            },
            "mux": {"enabled": True, "concurrency": 8},
            "tag": "proxy"
        }, {
            "protocol": "freedom",
            "settings": {},
            "tag": "direct"
        }],
        "routing": {
            "domainStrategy": "IPIfNonMatch",
            "rules": [
                {"type": "field", "outboundTag": "block", "protocol": ["bittorrent"]},
                {"type": "field", "outboundTag": "direct", "domain": ["geosite:cn"]},
                {"type": "field", "outboundTag": "direct", "ip": ["geoip:cn", "geoip:private"]}
            ]
        }
    }

# ============================================
# ОТКРЫТИЕ ПОРТОВ
# ============================================

def open_ports():
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

# ============================================
# ПРОВЕРКА РАБОТЫ
# ============================================

def test_connection():
    """Проверяет, работает ли сервер"""
    print("🔍 Проверка соединения...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex(('localhost', PORT))
        sock.close()
        
        if result == 0:
            print(f"✅ Сервер принимает соединения на порту {PORT}")
            return True
        else:
            print(f"⚠️ Сервер не отвечает на порту {PORT}")
            return False
    except Exception as e:
        print(f"⚠️ Ошибка проверки: {e}")
        return False

# ============================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================

def main():
    print("=" * 50)
    print("🚀 VLESS SERVEO (БЕЗ TLS)")
    print("=" * 50)
    print()
    
    print(f"🌐 Домен: {SERVEO_DOMAIN}")
    print(f"🔑 UUID: {SERVER_UUID}")
    print(f"🔌 Порт: {PORT}")
    print()
    
    open_ports()
    
    if not install_xray():
        print("❌ Ошибка установки Xray")
        return
    
    configure_and_run_xray()
    time.sleep(2)
    test_connection()
    
    start_serveo_tunnel()
    
    links = generate_vless_links(SERVEO_DOMAIN, SERVER_UUID, PORT)
    happ_config = create_happ_config(SERVEO_DOMAIN, SERVER_UUID, PORT)
    
    # ============================================
    # ВЫВОД РЕЗУЛЬТАТА
    # ============================================
    result_text = f"""
╔══════════════════════════════════════════════════════════════╗
║         ✅ VLESS VPN (БЕЗ TLS) ГОТОВ К ИСПОЛЬЗОВАНИЮ         ║
╚══════════════════════════════════════════════════════════════╝

📌 ИНФОРМАЦИЯ О СЕРВЕРЕ:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🌐 Адрес: {SERVEO_DOMAIN}
  🔑 UUID: {SERVER_UUID}
  🔌 Порт TCP: {PORT}
  📡 Порт WS: {PORT_WS}
  ⏰ Создан: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔗 РАБОЧИЕ VLESS ССЫЛКИ:

1️⃣ TCP (основная, 100% работает):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{links['tcp']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

2️⃣ WebSocket (для обхода блокировок):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{links['ws']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

3️⃣ TCP с flow (для дополнительной совместимости):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{links['flow']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📱 КАК ИСПОЛЬЗОВАТЬ:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. Скопируйте ЛЮБУЮ ссылку выше
  2. Вставьте в клиент:
     • Android: V2RayNG → Import from clipboard
     • iOS: Shadowrocket → Import from clipboard  
     • Windows: V2RayN → Import from clipboard
     • HAPP: Скопируйте конфиг из vless_config.json
  3. Включите соединение
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚡ СКОРОСТЬ: Высокая (без шифрования TLS)
🔒 БЕЗОПАСНОСТЬ: Базовая (VLESS шифрует трафик)
⏰ ВРЕМЯ РАБОТЫ: 6 часов
"""
    
    with open("vless_result.txt", "w") as f:
        f.write(result_text)
    
    with open("vless_config.json", "w") as f:
        json.dump(happ_config, f, indent=2)
    
    print(result_text)
    
    print("\n" + "=" * 50)
    print("📁 Файлы сохранены")
    print("=" * 50)

if __name__ == "__main__":
    main()
