#!/bin/sh
set -e

echo "Waiting for postgres..."
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; do
  sleep 1
done
echo "Postgres is ready."

echo "Pending migration plan:"
python manage.py showmigrations --plan

echo "Running migrations..."
python manage.py migrate --noinput

echo "Applied migration state:"
python manage.py showmigrations

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting server..."
exec gunicorn treeHouse.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120
