# My Tracks

A Django-based backend server for the OwnTracks Android app, designed to receive and persist geolocation data from OwnTracks clients using Python 3.12+ with full type hints and modern features.

## 🚀 Quick Start

```bash
# One-command setup
bash setup

# Start server
python manage.py runserver

# Test API
curl -X POST http://localhost:8000/api/locations/ \
  -H "Content-Type: application/json" \
  -d '{"lat": 37.7749, "lon": -122.4194, "tst": 1705329600, "tid": "AB"}'
```

**See [QUICKSTART.md](QUICKSTART.md) for detailed 5-minute setup guide.**

## 📚 Documentation

- **[📖 Documentation Index](DOCS_INDEX.md)** - Complete guide to all docs
- **[🚀 QUICKSTART.md](QUICKSTART.md)** - Get running in 5 minutes
- **[📘 API.md](API.md)** - Complete API reference
- **[🚢 DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment guide
- **[⌨️ COMMANDS.md](COMMANDS.md)** - Command reference
- **[📊 PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Comprehensive project overview
- **[👥 AGENTS.md](AGENTS.md)** - Development agent workflow

## Features

- **OwnTracks HTTP Protocol Support**: Full compatibility with OwnTracks JSON format
- **Location Data Persistence**: Store location data with full context (latitude, longitude, timestamp, accuracy, altitude, velocity, battery, connection type)
- **RESTful API**: Clean API endpoints for location data with filtering and pagination
- **Device Management**: Support for multiple devices with unique identification
- **Type Safety**: Full type hints using Python 3.12+ features
- **Modern Python**: Uses dataclasses and modern Python idioms
- **Admin Interface**: Django admin for data management
- **Comprehensive Testing**: Full pytest test suite included
- **Production Ready**: Includes deployment guide and Gunicorn configuration

## Requirements

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) package manager (fast, reliable Python package installer)
- PostgreSQL (recommended for production) or SQLite (development)

**Why uv?** This project uses `uv` exclusively for dependency management - it's significantly faster than pip and provides deterministic installs.

## Installation

### Automated Setup (Recommended)

```bash
# Clone repository
git clone <repository-url>
cd my-tracks

# Run setup script
bash setup
```

This will:
1. Install `uv` if needed
2. Create project structure from PROJECT_FILES.txt
3. Set up virtual environment
4. Install all dependencies
5. Run database migrations

### Manual Setup

1. **Install uv** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd my-tracks
   ```

3. **Extract project files**:
   ```bash
   python3 install.py
   ```

4. **Create virtual environment and install dependencies**:
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv pip install -e .
   ```

5. **For development dependencies**:
   ```bash
   uv pip install -e ".[dev]"
   ```

6. **Configure environment variables**:
   Create a `.env` file in the project root:
   ```
   SECRET_KEY=your-secret-key-here
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1
   DATABASE_URL=sqlite:///db.sqlite3
   ```

6. **Run migrations**:
   ```bash
   python manage.py migrate
   ```

7. **Create a superuser** (optional, for admin access):
   ```bash
   python manage.py createsuperuser
   ```

8. **Run the development server**:
   ```bash
   python manage.py runserver
   ```

   **Planned**: A `start_server` script for easier server management (check running status, restart with confirmation). See [COMMANDS.md](COMMANDS.md#server-management-script-planned).

## OwnTracks Configuration

Configure your OwnTracks app with the following settings:

- **Mode**: HTTP
- **URL**: `http://your-server:8000/api/locations/`
- **Authentication**: Use device ID in the payload

## API Endpoints

### POST /api/locations/

Submit location data from OwnTracks client.

**Request Body** (JSON):
```json
{
  "_type": "location",
  "lat": 37.7749,
  "lon": -122.4194,
  "tst": 1234567890,
  "acc": 10,
  "alt": 50,
  "vel": 5,
  "batt": 85,
  "tid": "AB",
  "conn": "w"
}
```

**Response**: 201 Created

### GET /api/locations/

Retrieve location history.

**Query Parameters**:
- `device`: Filter by device ID
- `start_date`: Filter locations after this date (ISO 8601)
- `end_date`: Filter locations before this date (ISO 8601)
- `limit`: Maximum number of results (default: 100)

### GET /api/devices/

List all registered devices.

## Project Structure

```
my-tracks/
├── manage.py                 # Django management script
├── requirements.txt          # Python dependencies
├── mytracks/                 # Django project directory
│   ├── __init__.py
│   ├── settings.py          # Project settings
│   ├── urls.py              # URL routing
│   └── wsgi.py              # WSGI configuration
└── tracker/                  # Location tracking app
    ├── __init__.py
    ├── admin.py             # Django admin configuration
    ├── apps.py              # App configuration
    ├── models.py            # Database models
    ├── serializers.py       # DRF serializers
    ├── views.py             # API views
    ├── urls.py              # App URL routing
    └── migrations/          # Database migrations
```

## Development

### Running Tests

```bash
python manage.py test
```

### Code Style

This project follows PEP 8 guidelines. To check code style:

```bash
pip install flake8
flake8 .
```

## Production Deployment

For production deployment:

1. Set `DEBUG=False` in `.env`
2. Configure a proper database (PostgreSQL recommended)
3. Set strong `SECRET_KEY`
4. Configure `ALLOWED_HOSTS` with your domain
5. Use a production WSGI server (gunicorn is included)
6. Set up SSL/TLS certificates

Example with gunicorn:
```bash
gunicorn mytracks.wsgi:application --bind 0.0.0.0:8000
```

## License

MIT License

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.
