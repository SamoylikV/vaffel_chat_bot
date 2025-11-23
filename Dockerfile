FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py cities_timezones.json .env ./

CMD ["python", "bot.py"]