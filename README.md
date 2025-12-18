# Library Management System Prototype

This repository contains a minimal but functional prototype that follows the main requirements from `Plan_en.md`. The solution is built around a FastAPI backend with SQLAlchemy models and a lightweight static frontend to showcase the core flows.

## Features

- **Multi-database synchronisation**: every change on the primary database is mirrored to three SQLite replicas (standing in for MySQL, Oracle, and SQL Server) with conflict detection and logging.
- **Authentication & RBAC**: JWT-based login with `admin` and `student` roles.
- **Core modules**: book catalogue, borrowing records, fines, seat management, and seat reservations.
- **Reporting**: dashboard endpoint summarising library activity and popularity metrics.
- **Sync monitoring**: API and UI section that list recent synchronisation events.
- **Frontend demo**: `frontend/` contains a small HTML/JS client showing authentication, dashboard, book listing, and log monitoring.

## Project layout

```
backend/
  app/
    main.py          # FastAPI entry point
    models.py        # SQLAlchemy ORM models
    schemas.py       # Pydantic schemas for request/response validation
    crud.py          # Business logic with synchronisation hooks
    database.py      # Engine/session configuration and helpers
    security.py      # Password hashing & JWT helpers
    sync_manager.py  # Multi-database sync implementation
frontend/
  index.html         # Minimal UI to exercise the API
  app.js             # Client logic using the REST API
  styles.css         # Styling for the demo UI
requirements.txt     # Python dependencies
Plan_en.md           # Provided requirements (English)
Plan_ch.md           # Provided requirements (Chinese)
```

## Getting started

1. **Install dependencies**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Run the backend**:
   ```bash
   uvicorn backend.app.main:app --reload
   ```

3. **Open the frontend demo**: serve the `frontend/` directory (e.g. using VS Code Live Server or `python -m http.server 9000 -d frontend`). Configure `window.API_BASE` if you use a different backend URL.

4. **Explore the API**: visit `http://localhost:8000/docs` for interactive Swagger documentation.

## Synchronisation details

- SQLite databases located in `backend/data/` represent the primary database and replicas. They share the same schema.
- The `sync_manager` module mirrors changes after each commit, recording results in the `sync_logs` table and the `logs/sync.log` file when conflicts are detected.
- Replica conflicts favour the most recent update. Administrators can review conflicts and decide manual resolution steps.

## Tests

Manual verification can be performed using the included API docs or the frontend demo. Automated tests are not part of this initial prototype but hooks for dependency injection and separation of concerns make the system test-friendly.
