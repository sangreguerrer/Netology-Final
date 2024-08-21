# Используем Python 3.12 как базовый образ
FROM python:3.12-alpine

# Обновляем и устанавливаем необходимые зависимости
RUN apk update && apk add --no-cache gcc libc-dev

# Устанавливаем рабочую директорию
WORKDIR /djangoProjectFinalWork

# Устанавливаем переменные окружения
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Копируем файл зависимостей и устанавливаем их
COPY ./requirements.txt /djangoProjectFinalWork/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Копируем скрипт entrypoint.sh в контейнер
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

# Даем права на выполнение скрипта
RUN chmod +x /usr/local/bin/entrypoint.sh

# Настройте ENTRYPOINT для выполнения скрипта
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

