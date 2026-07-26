#!/bin/bash
set -e

# Install Python dependencies
pip install -r requirements.txt

# Build frontend
cd frontend
npm install
npm run build
cd ..

# Collect static files
python manage.py collectstatic --noinput

# Run migrations (Vercel doesn't persist SQLite, so this is for initial setup)
# python manage.py migrate --noinput
