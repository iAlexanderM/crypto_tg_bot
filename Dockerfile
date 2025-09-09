# Используем официальный образ Python
FROM python:3.12-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем зависимости Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY src/ ./src/

# Копируем скрипт очистки логов
COPY cleanup_logs.py ./

# Копируем файл данных пользователей из корня проекта
COPY user_data.json ./user_data.json

# Создаем директории для логов и данных
RUN mkdir -p /app/logs /app/data

# Создаем непривилегированного пользователя
RUN useradd -m botuser && chown -R botuser:botuser /app
USER botuser

# Устанавливаем переменные окружения
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Создаем volume для данных
VOLUME ["/app/data", "/app/logs"]

# Запускаем бота
CMD ["python", "src/main.py"]

# Альтернативная команда для очистки логов
# CMD ["python", "cleanup_logs.py"]