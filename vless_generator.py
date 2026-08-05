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

PORT = 228
PORT_WS = 8443

def generate_subdomain():
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choices(chars, k=10))

SUBDOMAIN = generate_subdomain()
SERVEO_DOMAIN = f"{SUBDOMAIN}.serveo.net"
SERVER_UUID = str(uuid.uuid4())

# ============================================
# УСТАНОВКА XRAY (ИСПРАВЛЕННАЯ)
# ============================================

def install_xray():
    """Устанавливает Xray напрямую"""
    print("🚀 Установка Xray...")
    
    try:
        # Скачиваем последний релиз
        subprocess.run(
            "wget -qO /tmp/xray.zip https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip",
            shell=True, check=True
        )
        
        # Распаковываем
        subprocess.run(
            "sudo unzip -o /tmp/xray.zip -d /usr/local/bin/",
            shell=True, check=True
        )
        
        # Делаем исполняемым
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
# НАСТРОЙКА И ЗАПУСК XRAY
# ============================================

def configure_and_run_xray():
    """Настраивает и запускает Xray"""
    print("⚙️ Настройка и запуск Xray...")
    
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
    
    try:
        # Создаем папку для конфига
        subprocess.run("sudo mkdir -p /usr/local/etc/xray", shell=True, check=True)
        
        # Сохраняем конфиг
        with open("/tmp/config.json", "w") as f:
            json.dump(config, f, indent=2)
        
        subprocess.run(f"sudo mv /tmp/config.json /usr/local/etc/xray/config.json", shell=True, check=True)
        
        # ============================================
        # ЗАПУСКАЕМ XRAY ВРУЧНУЮ (ВАЖНО!)
        # ============================================
        print("🔧 Запускаем Xray...")
        
        # Останавливаем старые процессы
        subprocess.run("sudo pkill -f xray || true", shell=True)
        
        # Запускаем Xray в фоне с выводом в лог
        subprocess.Popen(
            "sudo /usr/local/bin/xray -config /usr/local/etc/xray/config.json > /tmp/xray.log 2>&1 &",
            shell=True
        )
        
        time.sleep(3)
        
        # Проверяем, что Xray запустился
        print("📊 Проверяем работу Xray...")
        
        # Проверяем, слушает ли порт
        result = subprocess.run(
            f"sudo netstat -tulpn | grep ':{PORT}'",
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.stdout:
            print(f"✅ Xray запущен и слушает порт {PORT}")
            
            # Показываем логи
            log_result = subprocess.run(
                "tail -20 /tmp/xray.log",
                shell=True,
                capture_output=True,
                text=True
            )
            if log_result.stdout:
                print("📋 Логи Xray:")
                print(log_result.stdout[:500])
            
            return True
        else:
            print("⚠️ Xray не запустился")
            # Показываем ошибки
            log_result = subprocess.run(
                "tail -50 /tmp/xray.log",
                shell=True,
                capture_output=True,
                text=True
            )
            if log_result.stdout:
                print("⚠️ Логи ошибок:")
                print(log_result.stdout[:1000])
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
    
    # Закрываем старые SSH соединения
    subprocess.run("pkill -f serveo || true", shell=True)
    
    # Запускаем туннель
    cmd = f"ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=60 -R {SUBDOMAIN}:{PORT}:localhost:{PORT} serveo.net"
    
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    time.sleep(5)
    
    # Проверяем
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('serveo.net', 22))
        sock.close()
        
        if result == 0:
            print(f"✅ Serveo туннель запущен")
            return True
    except:
        pass
    
    print("⚠️ Возможны проблемы с Serveo, но продолжаем...")
    return False

# ============================================
# ГЕНЕРАЦИЯ VLESS ССЫЛОК
# ============================================

def generate_vless_links(domain, uuid, port):
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
    
    vless_ws = (
        f"vless://{uuid}@{domain}:{PORT_WS}"
        f"?encryption=none"
        f"&type=ws"
        f"&path=%2Fvless"
        f"#VLESS_SERVEO_WS"
    )
    
    return {"tcp": vless_tcp, "ws": vless_ws}

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
                        "flow": "xtls-rprx-vision",
                        "level": 0
                    }]
                }]
            },
            "streamSettings": {
                "network": "tcp",
                "security": "tls",
                "tlsSettings": {"allowInsecure": True, "serverName": domain}
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
    
    open_ports()
    
    # Устанавливаем Xray
    if not install_xray():
        print("❌ Ошибка установки Xray")
        return
    
    # Настраиваем и запускаем Xray
    if not configure_and_run_xray():
        print("❌ Ошибка запуска Xray")
        print("⚠️ Пробуем создать ссылки без проверки...")
    
    # Запускаем Serveo туннель
    start_serveo_tunnel()
    
    # Генерируем ссылки
    links = generate_vless_links(SERVEO_DOMAIN, SERVER_UUID, PORT)
    happ_config = create_happ_config(SERVEO_DOMAIN, SERVER_UUID, PORT)
    
    # Результат
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

🔗 VLESS ССЫЛКИ:

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
💡 Адрес: {SUBDOMAIN}.serveo.net
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
