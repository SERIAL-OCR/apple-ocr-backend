# Storage Directory

This directory contains all persistent data for the Apple OCR Backend system.

## Directory Structure

```
storage/
├── database/          # SQLite database files
│   └── app.db        # Main application database
├── exports/           # Generated Excel reports and exports
│   ├── debug/        # Debug images and processing artifacts
│   ├── reports/      # Generated reports and analytics
│   └── *.xlsx        # Excel export files
├── logs/             # Application logs
│   └── *.log         # Log files
└── backups/          # Database backups and snapshots
```

## Database

The SQLite database (`database/app.db`) contains:
- Serial number scan results
- Processing timestamps
- Device type information
- Confidence scores

## Exports

The exports directory contains:
- Excel reports generated from scan data
- Debug images from OCR processing
- Parameter sweep results
- Performance analytics

## Logs

Application logs including:
- API request logs
- OCR processing logs
- Error logs
- Performance metrics

## Backups

Database backups and system snapshots for data recovery.

## Usage

- Database files are automatically managed by the application
- Excel exports are generated via API endpoints
- Logs are automatically rotated and cleaned
- Backups should be created regularly for production systems
