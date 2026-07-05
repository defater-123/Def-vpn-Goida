import argparse
import concurrent.futures
import os
import sys
import re
import subprocess
from src.config import URLS, DEFAULT_MAX_WORKERS
from src.logger import updated_files, _UPDATED_FILES_LOCK, LOGS_BY_FILE
from src.file_manager import download_and_save, create_filtered_configs
from src.release_fetcher import fetch_latest_release_links, fetch_vc_runtime_link
from src.readme_updater import update_readme_download_links, update_readme_table
from src.git_ops import git_commit_and_push

# Настройка кодировки вывода
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# ===== НОВАЯ ФУНКЦИЯ ДЛЯ ФИЛЬТРАЦИИ =====
def filter_keys(input_file, output_file, top_n=50):
    """Проверяет ключи и сохраняет только живые"""
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            keys = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"❌ Не удалось прочитать {input_file}: {e}")
        return

    print(f"🔍 Проверяю {len(keys)} ключей...")
    alive_keys = []
    checked = 0

    for key in keys:
        checked += 1
        # Извлекаем IP и порт из ключа
        match = re.search(r'@([^:]+):([0-9]+)', key)
        if not match:
            continue

        ip = match.group(1)
        port = match.group(2)

        # Проверка через nc (быстрая)
        try:
            result = subprocess.run(
                ['timeout', '3', 'nc', '-zv', ip, port],
                capture_output=True,
                text=True,
                timeout=5
            )
            is_alive = result.returncode == 0
        except Exception:
            is_alive = False

        if is_alive:
            alive_keys.append(key)
            print(f"  ✅ Ключ #{checked} ЖИВ")
        else:
            print(f"  ❌ Ключ #{checked} МЕРТВ")

        if len(alive_keys) >= top_n:
            break

    # Сохраняем результат
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(alive_keys))
        print(f"💾 Сохранено {len(alive_keys)} ключей в {output_file}")
    except Exception as e:
        print(f"❌ Ошибка сохранения {output_file}: {e}")

# ===== ОСНОВНАЯ ФУНКЦИЯ =====
def main(dry_run: bool = False):
    max_workers_download = min(DEFAULT_MAX_WORKERS, max(1, len(URLS)))

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers_download) as pool:
        futures = [pool.submit(download_and_save, i) for i in range(len(URLS))]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                _, file_index = result
                with _UPDATED_FILES_LOCK:
                    updated_files.add(file_index)

    local_path_26 = create_filtered_configs()
    if os.path.exists(local_path_26):
        with _UPDATED_FILES_LOCK:
            updated_files.add(26)

    # ===== НОВАЯ ЛОГИКА: объединение и фильтрация =====
    print("\n📦 Объединяю все ключи в один файл...")
    all_keys = []
    for i in range(1, 27):  # 26 источников
        file_path = f"githubmirror/{i}.txt"
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    keys = [line.strip() for line in f if line.strip()]
                    all_keys.extend(keys)
                    print(f"  ✅ Загружено {len(keys)} ключей из {i}.txt")
            except Exception as e:
                print(f"  ❌ Ошибка чтения {file_path}: {e}")

    if all_keys:
        # Сохраняем все ключи
        all_file = "githubmirror/all.txt"
        try:
            with open(all_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(all_keys))
            print(f"📁 Сохранено {len(all_keys)} ключей в {all_file}")
        except Exception as e:
            print(f"❌ Ошибка сохранения {all_file}: {e}")

        # Создаём ТОП-50
        top_file = "githubmirror/top_50.txt"
        filter_keys(all_file, top_file, top_n=50)
    else:
        print("⚠️ Не найдено ни одного ключа!")

    # Обновляем README и коммитим
    release_links = fetch_latest_release_links()
    vc_runtime_link = fetch_vc_runtime_link()
    update_readme_download_links(release_links, vc_runtime_link)
    update_readme_table()
    git_commit_and_push(dry_run=dry_run)

    # Вывод логов
    ordered_keys = sorted(k for k in LOGS_BY_FILE if k != 0)
    output_lines = []
    for k in ordered_keys:
        output_lines.append(f"----- {k}.txt -----")
        output_lines.extend(LOGS_BY_FILE[k])
    if LOGS_BY_FILE.get(0):
        output_lines.append("----- Общие сообщения -----")
        output_lines.extend(LOGS_BY_FILE[0])
    print("\n".join(output_lines))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Скачивание репозитория и коммит в GitHub")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Сохранять файлы локально и делать коммит, но не пушить",
    )
    args = parser.parse_args()
    main(dry_run=args.dry_run)
