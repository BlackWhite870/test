import os
import sys
import hashlib
import shutil
import json
import logging
import time
from datetime import datetime, timedelta
from zipfile import ZipFile
from pathlib import Path

logging.basicConfig(
    filename='log.txt',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)

CACHE_FILE = 'cache.json'
REPORT_FILE = 'report.txt'
ARCHIVE_DIR = 'archive'
DAYS_OLD = 30

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f)

def md5sum(filepath):
    hash_md5 = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logging.warning(f"Не удалось рассчитать MD5 для {filepath}: {e}")
        return None

def is_old_file(path):
    file_time = datetime.fromtimestamp(path.stat().st_mtime)
    return datetime.now() - file_time > timedelta(days=DAYS_OLD)

def analyze_directory(root):
    file_info = {}
    size_by_folder = {}
    dups_by_hash = {}
    old_files = []

    for foldername, _, filenames in os.walk(root):
        for fname in filenames:
            fpath = Path(foldername) / fname
            try:
                stat = fpath.stat()
                size = stat.st_size
                mtime = stat.st_mtime
                hash = md5sum(fpath)

                if not hash:
                    continue

                rel_path = str(fpath.relative_to(root))
                file_info[rel_path] = {'size': size, 'mtime': mtime, 'md5': hash}

                size_by_folder.setdefault(foldername, 0)
                size_by_folder[foldername] += size

                dups_by_hash.setdefault((size, hash), []).append(str(fpath))

                if is_old_file(fpath):
                    old_files.append(fpath)
            except Exception as e:
                logging.warning(f"Ошибка при обработке файла {fpath}: {e}")

    return file_info, size_by_folder, dups_by_hash, old_files

def write_report(size_by_folder):
    with open(REPORT_FILE, 'w') as f:
        for folder, size in size_by_folder.items():
            f.write(f"{folder}: {size / 1024:.2f} KB\n")

def archive_old_files(files):
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    archive_name = f"archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    archive_path = Path(ARCHIVE_DIR) / archive_name

    with ZipFile(archive_path, 'w') as zipf:
        for file in files:
            try:
                zipf.write(file, arcname=file.name)
                os.remove(file)
                logging.info(f"Файл заархивирован и удалён: {file}")
            except Exception as e:
                logging.warning(f"Не удалось архивировать {file}: {e}")

def get_changed_files(old_cache, new_info):
    changed = {}
    for path, info in new_info.items():
        if path not in old_cache or old_cache[path] != info:
            changed[path] = info
    return changed

def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    logging.info(f"Начат анализ директории: {root}")

    try:
        cache = load_cache()
        new_info, size_by_folder, dups, old_files = analyze_directory(root)
        changed_info = get_changed_files(cache, new_info)

        if changed_info:
            logging.info(f"Обнаружено {len(changed_info)} новых/изменённых файлов")
        else:
            logging.info("Нет новых или изменённых файлов")

        write_report(size_by_folder)
        archive_old_files(old_files)
        save_cache(new_info)

        # Отчёт по дубликатам
        for (size, hash), paths in dups.items():
            if len(paths) > 1:
                logging.info(f"Дубликаты (размер: {size}, md5: {hash}): {paths}")
    except Exception as e:
        logging.error(f"Критическая ошибка: {e}")

if __name__ == '__main__':
    main()
