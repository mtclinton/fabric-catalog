# Fabric Catalog

A containerized full-stack application for cataloging and managing fabric information scraped from various websites.

## Quick Start

### 1. Create Required Directories

```bash
mkdir -p data backend/static/images
```

### 2. Configure URLs

Edit `fabric-config.json` with the URLs you want to scrape:

```json
{
  "urls": [
    "https://www.fabrichouse.com/int/all-fabrics/natural-fiber-fabric?order=new-arrivals&p=1",
    "https://example.com/fabric1"
  ]
}
```

### 3. Start the Application

```bash
docker-compose up --build
```

### 4. Access

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Scheduled Scraping

The scraper runs automatically **once per day at 2:00 AM** (server time).

It reads URLs from `fabric-config.json` and:
- Creates new fabric entries for URLs not in the database
- Updates existing fabrics with latest information
- Downloads images automatically
- Handles listing pages (like Fabric House) by scraping all products from all pages

## Manual Scraping

### Via Frontend

1. Open http://localhost:3000
2. Use "Single URL" input or "Batch URLs" textarea
3. Click "Scrape Fabric" or "Batch Scrape"

### Via API

```bash
# Single URL
curl -X POST "http://localhost:8000/api/fabrics/scrape" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/fabric"}'

# Multiple URLs
curl -X POST "http://localhost:8000/api/fabrics/scrape-batch" \
  -H "Content-Type: application/json" \
  -d '["https://example.com/fabric1", "https://example.com/fabric2"]'
```

### Via Container

```bash
docker-compose exec backend python -c "
import asyncio
from app.scheduled_scraper import scrape_all_bookmarks
asyncio.run(scrape_all_bookmarks())
"
```

## Data Storage

- **Database**: `./data/fabric_catalog.db` (SQLite)
- **Images**: `./backend/static/images/`

Both persist across container restarts. Data is stored on the host filesystem, not in containers.

## Features

- Rating system: Mark fabrics as yes, no, maybe, or unrated
- Filter by rating and origin (website)
- Filter by origin (website domain)
- Image downloading and display
- Automatic daily scraping
- Supports listing pages with pagination (Fabric House)

## API Endpoints

- `GET /api/fabrics` - Get all fabrics (supports `?rating=yes&origin=fabrichouse.com`)
- `GET /api/fabrics/{id}` - Get fabric by ID
- `POST /api/fabrics/scrape` - Scrape a single URL
- `POST /api/fabrics/scrape-batch` - Scrape multiple URLs
- `PATCH /api/fabrics/{id}/rating` - Update rating
- `GET /api/fabrics/stats` - Get statistics
- `DELETE /api/fabrics/{id}` - Delete fabric

See http://localhost:8000/docs for interactive API documentation.

## Troubleshooting

### Permission Errors

If you see permission denied errors:

```bash
# Fix permissions on host directories
chmod -R 777 data backend/static
chmod 644 frontend/package.json frontend/vite.config.js frontend/index.html
```

Then restart: `docker-compose restart`

### Images Not Displaying

- Check image exists: `ls backend/static/images/`
- Test URL: `http://localhost:8000/static/images/filename.jpg`
- Check backend logs: `docker-compose logs backend`

### Scraper Not Working

- Check logs: `docker-compose logs backend`
- Verify URL is accessible
- Check if website structure changed

### Container Issues

- Rebuild: `docker-compose up --build`
- View logs: `docker-compose logs -f`
- Stop: `docker-compose down`

## Stopping the Application

```bash
# Stop containers (keeps data)
docker-compose stop

# Stop and remove containers (keeps data)
docker-compose down

# Stop and remove everything including volumes (DELETES DATA)
docker-compose down -v
```
