# Quick Start Guide

Get up and running with My Tracks in 5 minutes.

## Prerequisites

- Python 3.12 or higher
- Git
- [uv](https://github.com/astral-sh/uv) (installed automatically by setup script)

**Note**: This project uses `uv` exclusively for package management. The setup script will install it if needed.

## Installation (Automated)

### Option 1: One-Command Setup

```bash
bash setup
```

This will:
1. Check dependencies
2. Install uv if needed
3. Create project structure
4. Set up virtual environment
5. Install all dependencies
6. Run database migrations

### Option 2: Manual Setup

```bash
# 1. Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Run the installation script
python3 install.py

# 3. Create virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 4. Install dependencies
uv pip install -e .

# 5. Create environment file
cp .env.example .env

# 6. Run migrations
python manage.py migrate
```

## First Run

### 1. Start the Server

```bash
python manage.py runserver
```

The server will start at `http://localhost:8000/`

**Note**: For easier server management, a `start_server` script is planned that will:
- Check if the server is already running
- Prompt for confirmation before restarting
- Automatically start if not running

See [COMMANDS.md](COMMANDS.md#server-management-script-planned) for details.

### 2. Test the API

Submit a test location:

```bash
curl -X POST http://localhost:8000/api/locations/ \
  -H "Content-Type: application/json" \
  -d '{
    "_type": "location",
    "lat": 37.7749,
    "lon": -122.4194,
    "tst": 1705329600,
    "tid": "AB",
    "acc": 10,
    "batt": 85
  }'
```

Expected response:
```json
{
  "status": "ok",
  "message": "Location received"
}
```

### 3. View Location Data

```bash
curl http://localhost:8000/api/locations/
```

## Configure OwnTracks App

### Android/iOS App Setup

1. **Install OwnTracks**
   - Android: [Google Play Store](https://play.google.com/store/apps/details?id=org.owntracks.android)
   - iOS: [App Store](https://apps.apple.com/app/owntracks/id692424691)

2. **Configure Connection**
   - Open OwnTracks app
   - Tap on hamburger menu (≡)
   - Go to **Settings** → **Connection**
   - Set **Mode** to **HTTP**
   - Set **URL** to: `http://YOUR_IP:8000/api/locations/`
     - Replace `YOUR_IP` with your computer's IP address
     - Example: `http://192.168.1.100:8000/api/locations/`
   - Leave **Authentication** empty for now
   - Tap **Save**

3. **Set Device ID**
   - Go to **Settings** → **Identification**
   - Set **Tracker ID** to a 2-character code (e.g., "AB")
   - Set **Device ID** if desired (friendly name)

4. **Test Connection**
   - Tap the upload icon or wait for automatic update
   - Check server logs or visit `http://localhost:8000/api/locations/` to see the data

## Access Admin Panel

### 1. Create Superuser

```bash
python manage.py createsuperuser
```

Follow the prompts to set:
- Username
- Email (optional)
- Password

### 2. Login to Admin

Visit `http://localhost:8000/admin/` and login with your credentials.

From here you can:
- View all devices
- Browse location history
- Manage data

## Next Steps

### Development

- **Read the API docs**: [API.md](API.md)
- **Run tests**: `uv pip install -e ".[dev]" && pytest`
- **Check code style**: `flake8 .`
- **Format code**: `black .`

### Production

- **Read deployment guide**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **Set up PostgreSQL** for better performance
- **Configure SSL** with Let's Encrypt
- **Set up monitoring** and backups

## Common Commands

```bash
# Start development server
python manage.py runserver

# Run migrations
python manage.py migrate

# Create migrations after model changes
python manage.py makemigrations

# Create superuser
python manage.py createsuperuser

# Run tests
pytest

# Check code style
flake8 .

# Format code
black .

# Run type checks
mypy tracker/
```

## Troubleshooting

### Port Already in Use

```bash
# Use a different port
python manage.py runserver 8080
```

### Database Locked

If using SQLite and seeing "database is locked" errors:
```bash
# Remove the database and start fresh
rm db.sqlite3
python manage.py migrate
```

### Import Errors

Make sure you're in the virtual environment:
```bash
source .venv/bin/activate  # On Unix/macOS
.venv\Scripts\activate     # On Windows
```

### OwnTracks Not Connecting

1. **Check server is running**: Visit `http://localhost:8000/api/locations/` in a browser
2. **Check IP address**: Use actual IP, not `localhost`, when configuring the app
3. **Check firewall**: Ensure port 8000 is accessible
4. **Check URL format**: Must end with `/api/locations/`
5. **View server logs**: Watch terminal for incoming requests

## Example Workflows

### View Recent Locations

```bash
# Get last 10 locations
curl "http://localhost:8000/api/locations/?limit=10"

# Get locations for specific device
curl "http://localhost:8000/api/locations/?device=AB"

# Get today's locations
curl "http://localhost:8000/api/locations/?start_date=$(date -u +%Y-%m-%dT00:00:00Z)"
```

### Monitor in Real-Time

```bash
# Watch location updates in real-time
watch -n 2 'curl -s http://localhost:8000/api/locations/?limit=1 | python -m json.tool'
```

### Export Location Data

```bash
# Export to JSON file
curl "http://localhost:8000/api/locations/?device=AB" > my_locations.json

# Export to CSV (requires jq)
curl "http://localhost:8000/api/locations/" | \
  jq -r '.results[] | [.device, .latitude, .longitude, .timestamp] | @csv'
```

## Development Mode Features

When `DEBUG=True` (development):
- Detailed error pages
- SQL query logging
- Auto-reload on code changes
- Django Debug Toolbar (if installed)

## Getting Help

- **API Documentation**: [API.md](API.md)
- **Deployment Guide**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **OwnTracks Documentation**: https://owntracks.org/booklet/
- **Django Documentation**: https://docs.djangoproject.com/

## What's Next?

Now that you have the basics working:

1. **Explore the API**: Try different endpoints and filters
2. **Customize**: Modify models or add new features
3. **Secure**: Add authentication for production use
4. **Deploy**: Follow DEPLOYMENT.md to go live
5. **Integrate**: Build a web dashboard or mobile app

Happy tracking! 🗺️
