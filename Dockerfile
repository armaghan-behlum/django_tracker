FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=django_tracker.settings.staging

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN SECRET_KEY=build DEBUG=False POSTMARK_API_KEY=x \
    AWS_ACCESS_KEY_ID=x AWS_SECRET_ACCESS_KEY=x S3_BUCKET=x \
    DATA_DIR=/tmp python manage.py collectstatic --noinput

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py seed_report_options && gunicorn django_tracker.wsgi --bind 0.0.0.0:${PORT:-8000} --max-requests 500 --max-requests-jitter 50"]
