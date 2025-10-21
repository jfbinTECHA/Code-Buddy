# Bytebot Mission Control Dashboard

A comprehensive real-time monitoring and recovery dashboard for the Bytebot system.

## Features

- **Real-time Health Monitoring**: Live service status with uptime and latency metrics
- **Interactive Health Table**: Clickable service rows with detailed information
- **Sparklines with Tooltips**: Mini latency charts with hover details
- **WebSocket Live Updates**: Instant updates without page refresh
- **Recovery Operations**: Automated and manual service recovery
- **Historical Data**: Persistent storage of health metrics
- **Modern UI**: Responsive design with dark/light theme support

## Quick Start

### Using Docker Compose (Recommended)

1. **Build and start the dashboard:**
   ```bash
   docker-compose -f docker-compose.dashboard.yml up -d
   ```

2. **Access the dashboard:**
   - HTTP: http://localhost:9993
   - WebSocket: ws://localhost:9994

3. **View logs:**
   ```bash
   docker-compose -f docker-compose.dashboard.yml logs -f bytebot-dashboard
   ```

4. **Stop the dashboard:**
   ```bash
   docker-compose -f docker-compose.dashboard.yml down
   ```

### Manual Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the dashboard:**
   ```bash
   python3 dashboard/server.py
   ```

## API Endpoints

### HTTP Endpoints (Port 9993)

- `GET /` - Main dashboard UI
- `GET /api/health` - Current system health snapshot
- `GET /api/history` - Historical health data (last 50 snapshots)
- `GET /api/logs` - Recent recovery logs
- `GET /api/metrics` - System metrics and statistics
- `GET /api/loop-status` - Monitor loop status
- `POST /api/health-check` - Trigger manual health check
- `POST /api/recovery` - Trigger recovery operation
- `DELETE /api/logs` - Clear recovery logs

### WebSocket Endpoint (Port 9994)

- `ws://localhost:9994/ws` - Real-time health updates

## Configuration

### Health Configuration (`config/health_config.json`)

```json
{
  "services": [
    {
      "name": "bytebot-agent",
      "port": 3000,
      "health_endpoint": "/health"
    }
  ],
  "thresholds": {
    "restart_failures": 5,
    "cpu_max": 90,
    "mem_max": 90
  }
}
```

### Environment Variables

- `HEALTH_CONFIG_PATH` - Path to health configuration file
- `HISTORY_FILE_PATH` - Path for historical data storage
- `LOG_FILE_PATH` - Path for dashboard logs

## Architecture

### Components

1. **HTTP Server** (`http.server`) - Serves dashboard UI and REST API
2. **WebSocket Server** (`websockets`) - Real-time updates
3. **Health Monitor** - Background service monitoring loop
4. **Data Persistence** - JSON file storage for history
5. **Recovery System** - Automated service recovery

### Data Flow

1. Health monitor runs every 40 seconds
2. Collects service metrics and health status
3. Stores data in history and broadcasts via WebSocket
4. Dashboard UI updates in real-time
5. Recovery triggers on unhealthy services

## Development

### Project Structure

```
bytebotd/
├── dashboard/
│   └── server.py          # Main dashboard server
├── config/
│   └── health_config.json # Service configuration
├── ops/
│   ├── recover_bytebot.sh # Recovery scripts
│   └── bytebot_health.py  # Health check logic
├── docker-compose.dashboard.yml
├── Dockerfile.dashboard
├── requirements.txt
└── README.dashboard.md
```

### Adding New Services

1. Update `config/health_config.json` with new service details
2. Ensure service exposes health endpoint
3. Restart dashboard to pick up changes

### Customizing UI

- Edit HTML template in `dashboard/server.py` (HTML_TEMPLATE variable)
- Modify CSS styles inline or add external stylesheets
- Update JavaScript for new functionality

## Troubleshooting

### Common Issues

1. **Port conflicts**: Ensure ports 9993 and 9994 are available
2. **Permission errors**: Check file permissions for config and data directories
3. **WebSocket connection fails**: Verify firewall allows WebSocket connections
4. **Health checks fail**: Check service endpoints and network connectivity

### Logs

- Dashboard logs: `/var/log/bytebot-dashboard.log`
- Recovery logs: `/tmp/bytebot-recovery.log`
- Health history: `/tmp/health_history.json`

### Health Checks

The dashboard includes built-in health checks:

```bash
# Container health check
docker ps | grep bytebot-dashboard

# API health check
curl http://localhost:9993/api/health

# WebSocket connectivity
wscat -c ws://localhost:9994/ws
```

## Security Considerations

- Currently runs without authentication (development mode)
- For production, consider adding:
  - API key authentication
  - HTTPS/TLS encryption
  - Origin validation for WebSocket connections
  - Rate limiting for API endpoints

## Performance

- **Memory**: ~50MB base + history storage
- **CPU**: Minimal, peaks during health checks
- **Network**: WebSocket connections for real-time updates
- **Storage**: ~1MB/day for health history (configurable)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit pull request

## License

See main project LICENSE file.