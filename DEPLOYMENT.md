# Deployment Guide

This guide covers deploying My Tracks to production.

**Package Manager**: This project uses [uv](https://github.com/astral-sh/uv) exclusively for fast, reliable dependency management.

## Prerequisites

- Python 3.12+
- PostgreSQL 14+ (recommended for production)
- Nginx or Apache (for reverse proxy)
- SSL certificate (Let's Encrypt recommended)
- Domain name

## Production Configuration

### 1. Environment Variables

Create a `.env` file with production settings:

```bash
# Security
SECRET_KEY=<generate-a-strong-random-key>
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DATABASE_URL=postgresql://username:password@localhost:5432/owntracks

# CSRF
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### 2. Generate Secret Key

```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

### 3. PostgreSQL Setup

Install PostgreSQL:
```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# macOS
brew install postgresql
```

Create database:
```bash
sudo -u postgres psql
CREATE DATABASE owntracks;
CREATE USER owntrackuser WITH PASSWORD 'your_password';
ALTER ROLE owntrackuser SET client_encoding TO 'utf8';
ALTER ROLE owntrackuser SET default_transaction_isolation TO 'read committed';
ALTER ROLE owntrackuser SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE owntracks TO owntrackuser;
\q
```

### 4. Install Dependencies

```bash
# Create virtual environment
uv venv

# Activate
source .venv/bin/activate

# Install dependencies
uv pip install -e .

# Install additional production dependencies
uv pip install psycopg2-binary gunicorn
```

### 5. Django Setup

```bash
# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### 6. Gunicorn Configuration

Create `gunicorn_config.py`:

```python
"""Gunicorn configuration for production."""
import multiprocessing

bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 30
keepalive = 2

# Logging
accesslog = "/var/log/gunicorn/access.log"
errorlog = "/var/log/gunicorn/error.log"
loglevel = "info"
```

### 7. Systemd Service

Create `/etc/systemd/system/owntracks.service`:

```ini
[Unit]
Description=OwnTracks Django Backend
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/path/to/my-tracks
Environment="PATH=/path/to/my-tracks/.venv/bin"
ExecStart=/path/to/my-tracks/.venv/bin/gunicorn \
    --config gunicorn_config.py \
    mytracks.wsgi:application

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable owntracks
sudo systemctl start owntracks
sudo systemctl status owntracks
```

### 8. Nginx Configuration

Create `/etc/nginx/sites-available/owntracks`:

```nginx
upstream owntracks_backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;
    
    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    client_max_body_size 4G;
    
    # Static files
    location /static/ {
        alias /path/to/my-tracks/staticfiles/;
        expires 30d;
    }
    
    # Django application
    location / {
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Host $http_host;
        proxy_redirect off;
        proxy_pass http://owntracks_backend;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/owntracks /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 9. SSL Certificate (Let's Encrypt)

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

### 10. Firewall Configuration

```bash
sudo ufw allow 'Nginx Full'
sudo ufw allow OpenSSH
sudo ufw enable
```

## Monitoring and Maintenance

### Log Locations

- Application logs: `/var/log/gunicorn/`
- Nginx logs: `/var/log/nginx/`
- System logs: `journalctl -u owntracks`

### Database Backups

Create daily backup script `/usr/local/bin/backup_owntracks`:

```bash
#!/usr/bin/env bash
BACKUP_DIR="/backups/owntracks"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
pg_dump owntracks > $BACKUP_DIR/owntracks_$DATE.sql
gzip $BACKUP_DIR/owntracks_$DATE.sql

# Keep only last 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
```

Add to crontab:
```bash
0 2 * * * /usr/local/bin/backup_owntracks
```

Make executable:
```bash
chmod +x /usr/local/bin/backup_owntracks
```

### Health Checks

Create a health check endpoint or use Django's built-in admin health check.

### Updating the Application

```bash
# Pull latest code
git pull

# Activate virtualenv
source .venv/bin/activate

# Update dependencies
uv pip install -e .

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Restart service
sudo systemctl restart owntracks
```

## Security Checklist

- [ ] DEBUG=False in production
- [ ] Strong SECRET_KEY
- [ ] PostgreSQL with strong password
- [ ] SSL/TLS enabled
- [ ] Firewall configured
- [ ] Regular security updates
- [ ] Database backups enabled
- [ ] Monitoring configured
- [ ] Rate limiting (consider django-ratelimit)
- [ ] ALLOWED_HOSTS configured correctly

## Performance Optimization

### Database Indexing

Already implemented in models:
- Device lookup by device_id
- Location queries by device and timestamp

### Caching

Add Redis caching for improved performance:

```bash
uv pip install django-redis
```

Update settings.py:
```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

### Database Connection Pooling

For PostgreSQL:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'owntracks',
        'USER': 'owntrackuser',
        'PASSWORD': 'password',
        'HOST': 'localhost',
        'PORT': '5432',
        'CONN_MAX_AGE': 600,
    }
}
```

## Troubleshooting

### Check Service Status
```bash
sudo systemctl status owntracks
journalctl -u owntracks -f
```

### Check Nginx
```bash
sudo nginx -t
sudo systemctl status nginx
tail -f /var/log/nginx/error.log
```

### Database Issues
```bash
sudo -u postgres psql owntracks
\dt  # List tables
\d+ tracker_location  # Describe table
```

### Permission Issues
```bash
sudo chown -R www-data:www-data /path/to/my-tracks
sudo chmod -R 755 /path/to/my-tracks
```

## Support

For issues, please create an issue on the GitHub repository.
