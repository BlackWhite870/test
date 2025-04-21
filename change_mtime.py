import os
import time
from pathlib import Path

def set_mtime_for_all_files(directory: Path, days_ago: int):
    new_time = time.time() - days_ago * 86400
    for path in directory.rglob("*"):
        if path.is_file():
            try:
                os.utime(path, (new_time, new_time))
                print(f"[✓] Обновлено: {path}")
            except Exception as e:
                print(f"[!] Ошибка при обновлении {path}: {e}")

if __name__ == "__main__":
    target_dir = Path(input("Введите путь к директории (Enter для текущей): ") or Path.cwd())
    days = int(input("На сколько дней назад изменить дату?: "))

    if target_dir.exists():
        set_mtime_for_all_files(target_dir, days)
    else:
        print("❌ Указанная директория не существует.")
