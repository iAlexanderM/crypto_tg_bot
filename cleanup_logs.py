#!/usr/bin/env python3
"""
Скрипт для очистки старых логов.
"""
import os
import glob
import time
from datetime import datetime, timedelta

def cleanup_old_logs(log_dir=".", max_age_days=7, max_size_mb=100):
    """
    Очищает старые лог файлы.
    
    Args:
        log_dir: Директория с логами
        max_age_days: Максимальный возраст файлов в днях
        max_size_mb: Максимальный размер всех логов в MB
    """
    print(f"🧹 Очистка логов в {log_dir}")
    
    # Находим все лог файлы
    log_patterns = ["*.log", "*.log.*"]
    log_files = []
    
    for pattern in log_patterns:
        log_files.extend(glob.glob(os.path.join(log_dir, pattern)))
    
    if not log_files:
        print("📝 Лог файлы не найдены")
        return
    
    # Очистка по возрасту
    cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
    deleted_count = 0
    total_size = 0
    
    for log_file in log_files:
        try:
            file_stat = os.stat(log_file)
            file_size = file_stat.st_size
            file_age = file_stat.st_mtime
            
            total_size += file_size
            
            # Удаляем старые файлы
            if file_age < cutoff_time:
                os.remove(log_file)
                deleted_count += 1
                print(f"🗑️ Удален старый лог: {log_file}")
                
        except Exception as e:
            print(f"❌ Ошибка при обработке {log_file}: {e}")
    
    # Проверяем общий размер
    total_size_mb = total_size / (1024 * 1024)
    print(f"📊 Общий размер логов: {total_size_mb:.2f} MB")
    
    if total_size_mb > max_size_mb:
        print(f"⚠️ Размер логов превышает {max_size_mb} MB!")
        # Можно добавить дополнительную логику очистки
    
    print(f"✅ Очистка завершена. Удалено файлов: {deleted_count}")

if __name__ == "__main__":
    cleanup_old_logs()
