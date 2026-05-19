# MB User Sync

A Docker-based web UI tool for synchronizing users across media servers (Emby, Jellyfin, Ombi, Seerr).

## Features

- **Multi-Server Support**: Sync users across Emby, Jellyfin, Ombi, and Seerr
- **Two Sync Modes**:
  - **Primary Source**: One-way sync from a designated primary server to secondary servers
  - **Any-to-Any**: Many-to-many sync ensuring all users exist on all servers
- **Scheduled Syncing**: Configurable cron schedule (default: every 20 minutes)
- **Web UI**: Clean interface for configuration and manual sync triggers
- **Per-Server Settings**:
  - Enable/disable individual servers
  - API key and connection details
  - User exclusion lists
  - Template user for cloning settings to new users
- **Docker Deployment**: Single container, multi-platform (amd64/arm64)
- **GitHub Actions**: Automated builds and pushes to GitHub Container Registry (GHCR)

## Quick Start

### Using Docker

```bash
docker run -p 8000:8000 -v config.json:/app/config.json ghcr.io/eatprilosec/mbusersync:latest
```

Then access the web UI at `http://localhost:8000`

### Using Docker Compose

Create a `docker-compose.yml` file:

```yaml
version: '3.8'
services:
  mbusersync:
    image: ghcr.io/eatprilosec/mbusersync:latest
    ports:
      - "8000:8000"
    volumes:
      - ./config.json:/app/config.json
    restart: unless-stopped
```

Then run:
```bash
docker compose up -d
```

Access the web UI at `http://localhost:8000`

### Local Development

1. **Backend**:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r ../requirements.txt
uvicorn main:app --reload
```

2. **Frontend**:
```bash
cd frontend
npm install
npm run dev
```

## Configuration

Configuration is stored in `config.json` (auto-created on first run). Edit it to:
- Add server credentials
- Set primary source (for PRIMARY_SOURCE mode)
- Configure user exclusion lists
- Set template users for new user creation
- Adjust sync schedule (cron format)

### Example Configuration

```json
{
  "servers": {
    "emby": {
      "enabled": true,
      "host": "192.168.1.100",
      "port": 8096,
      "api_key": "your-api-key",
      "is_primary": true,
      "exclude_list": "admin, guest",
      "template_user": "template_user"
    },
    "jellyfin": {
      "enabled": true,
      "host": "192.168.1.101",
      "port": 8096,
      "api_key": "your-api-key",
      "is_primary": false,
      "exclude_list": "admin",
      "template_user": null
    }
  },
  "sync_config": {
    "sync_mode": "primary_source",
    "sync_enabled": true,
    "cron_schedule": "0 */20 * * * *"
  }
}
```

## API Endpoints

### Settings
- `GET /api/settings` - Get all settings
- `PUT /api/settings` - Update settings

### Servers
- `GET /api/servers` - List all server configs
- `GET /api/servers/{name}` - Get specific server config
- `PUT /api/servers/{name}` - Update server config
- `POST /api/servers/{name}/test` - Test connection
- `POST /api/servers/{name}/users` - Get users from server

### Sync
- `GET /api/sync/status` - Get sync status
- `POST /api/sync/run` - Manually trigger sync
- `PUT /api/sync/config` - Update sync config
- `POST /api/sync/validate` - Validate configuration

## Technology Stack

- **Backend**: FastAPI, APScheduler, HTTPX, Pydantic
- **Frontend**: React 18, React Hook Form, Zustand, Vite
- **Database**: JSON file-based configuration
- **Container**: Docker, Docker Buildx
- **CI/CD**: GitHub Actions

## Supported Media Servers

- **Emby** (v2 API)
- **Jellyfin** (v1 API - compatible with Emby)
- **Ombi** (v4 API)
- **Seerr** (Unified Overseerr/Jellyseerr)

## Security Notes

- API keys are stored in plaintext in `config.json`. Ensure proper file permissions.
- Run with non-root user in Docker (configured by default).
- Keep the container updated with latest base images.
- Consider encrypting `config.json` in production (planned for v2).

## Troubleshooting

### Sync not running
- Check if sync is enabled in Settings
- Verify cron schedule is valid
- Check app logs for errors

### Connection test fails
- Verify server is reachable on configured host/port
- Check API key is correct
- Ensure server user has admin permissions

### No users synced
- Check that at least one server is enabled
- For PRIMARY_SOURCE mode, ensure one server is marked as primary
- Check user exclusion lists
- Verify template user exists if using template cloning

## License

[Your License Here]

## Contributing

Issues and pull requests welcome!
