# My Tracks - Command Reference

Quick reference for all commonly used commands.

**Package Manager**: This project uses [uv](https://github.com/astral-sh/uv) exclusively for all dependency management.

## Setup Commands

### Initial Setup

```bash
# Automated setup (recommended)
bash setup

# Manual setup
python3 install.py
uv venv
source .venv/bin/activate
uv pip install -e .
```

### Verification

```bash
# Verify setup
python3 verify_setup.py

# Check Python version
python3 --version

# Check Django installation
python -c "import django; print(django.get_version())"
```

## Virtual Environment

```bash
# Create virtual environment
uv venv

# Activate (Unix/macOS)
source .venv/bin/activate

# Activate (Windows)
.venv\Scripts\activate

# Deactivate
deactivate

# Check active environment
which python
```

## Package Management (uv)

```bash
# Install production dependencies
uv pip install -e .

# Install with dev dependencies
uv pip install -e ".[dev]"

# Update all packages
uv pip install --upgrade -e .

# List installed packages
uv pip list

# Show package info
uv pip show django
```

## Installing uv

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installation
uv --version
```

## Django Management

### Database

```bash
# Run migrations
python manage.py migrate

# Create new migrations after model changes
python manage.py makemigrations

# Show migrations
python manage.py showmigrations

# Check for migration issues
python manage.py makemigrations --check --dry-run

# Rollback migration
python manage.py migrate tracker 0001  # Rollback to migration 0001

# Reset database (SQLite only)
rm db.sqlite3
python manage.py migrate
```

### Server

```bash
# Run development server
python manage.py runserver

# Run on different port
python manage.py runserver 8080

# Run on all interfaces
python manage.py runserver 0.0.0.0:8000

# Run with specific settings
python manage.py runserver --settings=mytracks.settings_dev
```

### Server Management Script (Planned)

**TODO**: A `start_server` script needs to be created with the following features:

1. **Check if server is already running**
   - Search for existing Django development server process
   - Display PID and port if found

2. **Restart with confirmation**
   - If server is running, prompt user: "Server is running on PID XXXX. Restart? (y/n)"
   - On confirmation: kill existing process and start new server
   - On decline: exit without changes

3. **Start if not running**
   - Start server normally if no existing process found

**Example usage:**
```bash
# Start or restart server with intelligent checking
bash start_server

# Optional: specify port
bash start_server 8080
```

**Implementation requirements:**
- Check for both `runserver` and production server (gunicorn) processes
- Graceful shutdown before restart (SIGTERM, then SIGKILL if needed)
- Show server URL after successful start
- Support for different ports via argument
- **Use shebang**: `#!/usr/bin/env bash`
- **Make executable**: `chmod +x start_server`
- **No .sh extension**: Follow Unix convention for cleaner CLI

### Admin

```bash
# Create superuser
python manage.py createsuperuser

# Change user password
python manage.py changepassword username

# Create superuser non-interactively
python manage.py createsuperuser --username admin --email admin@example.com --noinput
```

### Shell

```bash
# Django shell
python manage.py shell

# Shell with IPython
python manage.py shell -i ipython

# Run Python file in Django context
python manage.py shell < script.py
```

### Static Files

```bash
# Collect static files
python manage.py collectstatic

# Collect without prompts
python manage.py collectstatic --noinput

# Clear existing and collect
python manage.py collectstatic --clear --noinput
```

### Other Django Commands

```bash
# Check for common issues
python manage.py check

# Check deployment settings
python manage.py check --deploy

# Show Django version
python manage.py version

# Clear expired sessions
python manage.py clearsessions

# Show SQL for migration
python manage.py sqlmigrate tracker 0001
```

## Testing

### Run Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest test_tracker.py

# Run specific test class
pytest test_tracker.py::TestLocationAPI

# Run specific test
pytest test_tracker.py::TestLocationAPI::test_create_location_owntracks_format

# Run with verbose output
pytest -v

# Run with output capture disabled
pytest -s

# Stop on first failure
pytest -x

# Run last failed tests
pytest --lf
```

### Coverage

```bash
# Run tests with coverage
pytest --cov=tracker

# Generate HTML coverage report
pytest --cov=tracker --cov-report=html

# Show coverage for specific module
pytest --cov=tracker.models --cov-report=term-missing

# Coverage threshold (fail if below 80%)
pytest --cov=tracker --cov-fail-under=80
```

### Django Tests

```bash
# Run Django tests
python manage.py test

# Run specific app tests
python manage.py test tracker

# Run with verbose output
python manage.py test --verbosity=2

# Keep test database
python manage.py test --keepdb
```

## Code Quality

### Formatting

```bash
# Format all Python files
black .

# Format specific file
black tracker/models.py

# Check without modifying
black --check .

# Show diff
black --diff .
```

### Linting

```bash
# Run flake8
flake8 .

# Check specific directory
flake8 tracker/

# Show statistics
flake8 --statistics .

# Generate HTML report
flake8 --format=html --htmldir=flake-report .
```

### Type Checking

```bash
# Run mypy
mypy tracker/

# Check specific file
mypy tracker/models.py

# Strict mode
mypy --strict tracker/

# Generate HTML report
mypy --html-report mypy-report tracker/
```

## API Testing

### cURL Examples

```bash
# Submit location
curl -X POST http://localhost:8000/api/locations/ \
  -H "Content-Type: application/json" \
  -d '{"lat": 37.7749, "lon": -122.4194, "tst": 1705329600, "tid": "AB"}'

# Get all locations
curl http://localhost:8000/api/locations/

# Get locations for device
curl "http://localhost:8000/api/locations/?device=AB"

# Get locations with date filter
curl "http://localhost:8000/api/locations/?start_date=2024-01-01T00:00:00Z"

# Get with pagination
curl "http://localhost:8000/api/locations/?limit=10&offset=20"

# Get all devices
curl http://localhost:8000/api/devices/

# Get device details
curl http://localhost:8000/api/devices/AB/

# Get device locations
curl http://localhost:8000/api/devices/AB/locations/
```

### HTTPie Examples (if installed)

```bash
# Submit location
http POST localhost:8000/api/locations/ \
  lat=37.7749 lon=-122.4194 tst=1705329600 tid=AB

# Get locations
http GET localhost:8000/api/locations/ device==AB

# Pretty JSON
http --pretty=format GET localhost:8000/api/locations/
```

## Git Commands

```bash
# Initialize repository
git init
git add .
git commit -m "Initial commit"

# Create .gitignore
cat > .gitignore << 'EOF'
__pycache__/
*.pyc
.venv/
db.sqlite3
.env
.DS_Store
EOF

# Check status
git status

# View changes
git diff

# Commit changes
git add .
git commit -m "Add feature"

# Push to remote
git remote add origin <repo-url>
git push -u origin main
```

## Production Commands

### Gunicorn

```bash
# Start Gunicorn
gunicorn mytracks.wsgi:application

# With specific bind address
gunicorn mytracks.wsgi:application --bind 0.0.0.0:8000

# With workers
gunicorn mytracks.wsgi:application --workers 4

# With config file
gunicorn -c gunicorn_config.py mytracks.wsgi:application

# Daemon mode
gunicorn mytracks.wsgi:application --daemon
```

### Systemd

```bash
# Enable service
sudo systemctl enable owntracks

# Start service
sudo systemctl start owntracks

# Stop service
sudo systemctl stop owntracks

# Restart service
sudo systemctl restart owntracks

# Check status
sudo systemctl status owntracks

# View logs
journalctl -u owntracks -f
```

### Database Backup (PostgreSQL)

```bash
# Backup database
pg_dump owntracks > backup.sql

# Backup with compression
pg_dump owntracks | gzip > backup.sql.gz

# Restore database
psql owntracks < backup.sql

# Restore compressed
gunzip -c backup.sql.gz | psql owntracks
```

## Monitoring

```bash
# Watch location updates
watch -n 2 'curl -s http://localhost:8000/api/locations/?limit=1'

# Monitor logs
tail -f /var/log/gunicorn/access.log

# Monitor Django development server
python manage.py runserver 2>&1 | tee server.log

# Check disk usage
du -sh db.sqlite3

# Count locations in database
echo "SELECT COUNT(*) FROM tracker_location;" | python manage.py dbshell
```

## Debugging

```bash
# Django shell with models loaded
python manage.py shell
>>> from tracker.models import Device, Location
>>> Device.objects.all()
>>> Location.objects.count()

# Run with Python debugger
python -m pdb manage.py runserver

# Enable SQL query logging (settings.py)
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}

# Test email (if configured)
python manage.py sendtestemail admin@example.com
```

## Environment Variables

```bash
# Set environment variable (Unix/macOS)
export SECRET_KEY='your-secret-key'
export DEBUG=False

# Set environment variable (Windows)
set SECRET_KEY=your-secret-key
set DEBUG=False

# Load from .env file (with python-decouple)
# Automatically loaded by Django settings

# Check environment variable
echo $SECRET_KEY
printenv | grep DJANGO
```

## Troubleshooting

```bash
# Clear Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Reinstall dependencies
uv pip install --force-reinstall -e .

# Check for port conflicts
lsof -i :8000  # Unix/macOS
netstat -ano | findstr :8000  # Windows

# Kill process on port
kill $(lsof -t -i:8000)  # Unix/macOS

# Reset migrations (careful!)
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc" -delete
python manage.py makemigrations
python manage.py migrate
```

## Quick Workflows

### Complete Fresh Start

```bash
rm -rf .venv db.sqlite3
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Deploy Update

```bash
git pull
source .venv/bin/activate
uv pip install -e .
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart owntracks
```

### Run Full Test Suite

```bash
black --check .
flake8 .
mypy tracker/
pytest --cov=tracker --cov-report=html
python manage.py check --deploy
```

## Help

```bash
# Django help
python manage.py help

# Help for specific command
python manage.py help migrate

# List all commands
python manage.py help --commands

# uv help
uv --help

# pytest help
pytest --help
```
