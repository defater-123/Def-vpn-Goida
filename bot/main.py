#!/usr/bin/env python3
"""
VPN Keys Monitor
Проверяет доступность серверов из ключей в публичных репозиториях
"""

import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
import config


class KeyMonitor:
    def __init__(self):
        self.status = {}
        self.failed_keys = []
        self.results = []
        
    def fetch_repos_list(self) -> List[Tuple[str, str, str]]:
        """Читает список репозиториев из файла"""
        repos = []
        try:
            with open(config.REPOS_FILE, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    parts = line.split('|')
                    if len(parts) >= 3:
                        repo, branch, path = parts[0], parts[1], parts[2]
                        repos.append((repo, branch, path))
                    else:
                        print(f"⚠️  Неверный формат: {line}")
        except FileNotFoundError:
            print(f"❌ Файл {config.REPOS_FILE} не найден!")
            sys.exit(1)
        
        print(f"📚 Загружено {len(repos)} репозиториев")
        return repos
    
    def fetch_keys_from_repo(self, repo: str, branch: str, path: str) -> List[str]:
        """Загружает ключи из публичного репозитория"""
        url = f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"
        keys = []
        
        try:
            print(f"  📥 Загрузка из {repo}")
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                content = response.text
                # Парсим ключи (строки, не начинающиеся с #)
                for line in content.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Извлекаем IP/домен из строки с ключом
                        # Пример: vless://uuid@ip:port?params#name
                        # Или просто ip:port
                        key = self.extract_host_from_key(line)
                        if key:
                            keys.append(key)
                
                print(f"    ✅ Найдено {len(keys)} ключей")
            else:
                print(f"    ❌ Ошибка {response.status_code}: {repo}")
                
        except Exception as e:
            print(f"    ❌ Ошибка загрузки {repo}: {e}")
        
        return keys
    
    def extract_host_from_key(self, key_line: str) -> Optional[str]:
        """Извлекает хост из строки ключа"""
        # Пропускаем комментарии
        if key_line.startswith('#'):
            return None
        
        # Пробуем разные форматы ключей
        try:
            # Формат vless://uuid@host:port
            if 'vless://' in key_line or 'vmess://' in key_line or 'trojan://' in key_line:
                # Извлекаем часть после @ и до : или /
                import re
                match = re.search(r'://[^@]+@([^:/]+)', key_line)
                if match:
                    return match.group(1)
            
            # Формат host:port
            if ':' in key_line and not key_line.startswith('http'):
                parts = key_line.split(':')
                if len(parts) >= 2:
                    host = parts[0].strip()
                    # Проверяем, что это не порт
                    if not host.isdigit():
                        return host
            
            # Просто IP или домен
            if '.' in key_line or ':' in key_line:
                # Убираем порт если есть
                host = key_line.split(':')[0].split('/')[0].split('?')[0].strip()
                if host and not host.isdigit():
                    return host
                    
        except Exception:
            pass
        
        return None
    
    def ping_host(self, host: str) -> Tuple[bool, float]:
        """Пингует хост и возвращает (доступен, время_ответа)"""
        try:
            # Используем ping с таймаутом
            cmd = ['ping', '-c', str(config.PING_COUNT), '-W', str(config.PING_TIMEOUT), host]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=config.PING_TIMEOUT + 2
            )
            
            if result.returncode == 0:
                # Извлекаем среднее время из вывода
                import re
                match = re.search(r'=.*?([\d.]+)\s*ms', result.stdout)
                rtt = float(match.group(1)) if match else 0
                return True, rtt
            else:
                return False, 0
                
        except subprocess.TimeoutExpired:
            return False, 0
        except Exception:
            return False, 0
    
    def check_all_keys(self, all_keys: List[str]) -> Dict:
        """Проверяет все ключи параллельно"""
        results = {}
        print(f"\n🔍 Проверка {len(all_keys)} ключей...")
        
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            future_to_host = {
                executor.submit(self.ping_host, host): host 
                for host in all_keys
            }
            
            for future in as_completed(future_to_host):
                host = future_to_host[future]
                try:
                    is_up, rtt = future.result()
                    results[host] = {
                        'status': 'up' if is_up else 'down',
                        'rtt_ms': round(rtt, 2) if is_up else None,
                        'checked_at': datetime.now().isoformat()
                    }
                    
                    if is_up:
                        print(f"  ✅ {host} - {rtt:.1f}ms")
                    else:
                        print(f"  ❌ {host} - DOWN")
                        self.failed_keys.append(host)
                        
                except Exception as e:
                    results[host] = {
                        'status': 'error',
                        'error': str(e),
                        'checked_at': datetime.now().isoformat()
                    }
                    print(f"  ⚠️ {host} - ERROR: {e}")
        
        return results
    
    def load_previous_status(self) -> Dict:
        """Загружает предыдущий статус"""
        if os.path.exists(config.STATUS_FILE):
            try:
                with open(config.STATUS_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def save_status(self, results: Dict):
        """Сохраняет текущий статус"""
        # Загружаем предыдущий статус для сравнения
        previous = self.load_previous_status()
        
        # Обновляем статус
        status = {
            'last_update': datetime.now().isoformat(),
            'total_keys': len(results),
            'up_count': sum(1 for r in results.values() if r.get('status') == 'up'),
            'down_count': sum(1 for r in results.values() if r.get('status') == 'down'),
            'results': results
        }
        
        # Сохраняем
        with open(config.STATUS_FILE, 'w') as f:
            json.dump(status, f, indent=2)
        
        print(f"\n📊 Статус сохранен:")
        print(f"   Всего: {status['total_keys']}")
        print(f"   🟢 UP: {status['up_count']}")
        print(f"   🔴 DOWN: {status['down_count']}")
        
        # Отправляем уведомления о новых падениях
        self.send_notifications(previous, results)
        
        return status
    
    def send_notifications(self, previous: Dict, current: Dict):
        """Отправляет уведомления в Telegram"""
        if not config.TELEGRAM_ENABLED:
            return
        
        # Проверяем новые падения
        prev_results = previous.get('results', {})
        new_failures = []
        
        for host, data in current.items():
            prev_data = prev_results.get(host, {})
            if data.get('status') == 'down' and prev_data.get('status') != 'down':
                new_failures.append(host)
        
        if new_failures:
            message = f"🚨 VPN Keys Monitor\n\n"
            message += f"⚠️ Новые недоступные серверы:\n"
            for host in new_failures:
                message += f"  ❌ {host}\n"
            message += f"\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            message += f"\n📊 Всего DOWN: {len(self.failed_keys)}"
            
            self.send_telegram(message)
    
    def send_telegram(self, message: str):
        """Отправляет сообщение в Telegram"""
        if not config.TELEGRAM_ENABLED:
            return
        
        try:
            url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {
                'chat_id': config.TELEGRAM_CHAT_ID,
                'text': message,
                'parse_mode': 'HTML'
            }
            response = requests.post(url, data=data, timeout=10)
            if response.status_code == 200:
                print("📱 Уведомление отправлено в Telegram")
            else:
                print(f"⚠️ Ошибка отправки в Telegram: {response.status_code}")
        except Exception as e:
            print(f"⚠️ Ошибка отправки в Telegram: {e}")
    
    def generate_html(self, status: Dict):
        """Генерирует HTML страницу для GitHub Pages"""
        html = f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VPN Keys Monitor</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0e17;
            color: #e0e0e0;
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            padding: 30px 0;
            border-bottom: 1px solid #1a2332;
            margin-bottom: 30px;
        }}
        .header h1 {{
            font-size: 2.5em;
            background: linear-gradient(135deg, #00d4ff, #7b2ffc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }}
        .header p {{
            color: #8892b0;
            font-size: 0.9em;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: #111927;
            padding: 20px;
            border-radius: 12px;
            text-align: center;
            border: 1px solid #1a2332;
        }}
        .stat-card .number {{
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .stat-card .label {{
            color: #8892b0;
            font-size: 0.85em;
        }}
        .stat-card.up .number {{ color: #4ade80; }}
        .stat-card.down .number {{ color: #f87171; }}
        .stat-card.total .number {{ color: #60a5fa; }}
        
        .servers {{
            display: grid;
            gap: 8px;
        }}
        .server-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 20px;
            background: #111927;
            border-radius: 8px;
            border-left: 4px solid #1a2332;
            transition: all 0.3s;
        }}
        .server-item.up {{ border-left-color: #4ade80; }}
        .server-item.down {{ border-left-color: #f87171; }}
        .server-item.error {{ border-left-color: #fbbf24; }}
        
        .server-item .host {{
            font-family: 'Courier New', monospace;
            font-size: 0.95em;
        }}
        .server-item .status {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .badge {{
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.75em;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .badge.up {{ background: #064e3b; color: #4ade80; }}
        .badge.down {{ background: #7f1d1d; color: #f87171; }}
        .badge.error {{ background: #78350f; color: #fbbf24; }}
        
        .rtt {{
            color: #8892b0;
            font-size: 0.85em;
            min-width: 60px;
            text-align: right;
        }}
        .update-time {{
            text-align: center;
            color: #8892b0;
            font-size: 0.8em;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #1a2332;
        }}
        @media (max-width: 600px) {{
            .server-item {{ flex-direction: column; align-items: flex-start; gap: 8px; }}
            .server-item .status {{ width: 100%; justify-content: space-between; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ VPN Keys Monitor</h1>
            <p>Мониторинг доступности VPN серверов</p>
        </div>
        
        <div class="stats">
            <div class="stat-card total">
                <div class="number">{status.get('total_keys', 0)}</div>
                <div class="label">Всего серверов</div>
            </div>
            <div class="stat-card up">
                <div class="number">{status.get('up_count', 0)}</div>
                <div class="label">🟢 Доступны</div>
            </div>
            <div class="stat-card down">
                <div class="number">{status.get('down_count', 0)}</div>
                <div class="label">🔴 Недоступны</div>
            </div>
        </div>
        
        <div class="servers">
'''
        
        # Сортируем: сначала DOWN, потом UP
        results = status.get('results', {})
        sorted_hosts = sorted(
            results.items(),
            key=lambda x: (0 if x[1].get('status') == 'down' else 1, x[0])
        )
        
        for host, data in sorted_hosts:
            status_class = data.get('status', 'unknown')
            rtt = data.get('rtt_ms')
            rtt_text = f"{rtt}ms" if rtt else "—"
            
            html += f'''
            <div class="server-item {status_class}">
                <span class="host">{host}</span>
                <div class="status">
                    <span class="rtt">{rtt_text}</span>
                    <span class="badge {status_class}">{status_class.upper()}</span>
                </div>
            </div>
'''
        
        html += f'''
        </div>
        <div class="update-time">
            Последнее обновление: {status.get('last_update', 'Неизвестно')}
            <br>
            <span style="font-size:0.8em;">Обновляется каждые 15 минут</span>
        </div>
    </div>
</body>
</html>
'''
        
        # Сохраняем HTML
        os.makedirs(os.path.dirname(config.PAGES_FILE), exist_ok=True)
        with open(config.PAGES_FILE, 'w') as f:
            f.write(html)
        
        print(f"🌐 Страница обновлена: {config.PAGES_FILE}")

def main():
    print("🚀 VPN Keys Monitor Starting...")
    print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    monitor = KeyMonitor()
    
    # 1. Получаем список репозиториев
    repos = monitor.fetch_repos_list()
    if not repos:
        print("❌ Нет репозиториев для проверки")
        sys.exit(1)
    
    # 2. Загружаем ключи из всех репозиториев
    all_keys = []
    for repo, branch, path in repos:
        keys = monitor.fetch_keys_from_repo(repo, branch, path)
        all_keys.extend(keys)
    
    # Убираем дубликаты
    all_keys = list(set(all_keys))
    print(f"\n📋 Всего уникальных ключей: {len(all_keys)}")
    
    if not all_keys:
        print("❌ Не найдено ни одного ключа")
        sys.exit(1)
    
    # 3. Проверяем все ключи
    results = monitor.check_all_keys(all_keys)
    
    # 4. Сохраняем статус
    status = monitor.save_status(results)
    
    # 5. Генерируем HTML страницу
    monitor.generate_html(status)
    
    print("\n✅ Мониторинг завершен успешно!")

if __name__ == "__main__":
    main()
