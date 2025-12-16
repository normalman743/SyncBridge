# syncbridge-backend

FastAPI backend for **SyncBridge** — a web-based platform for structured requirement submission, negotiation (subforms), real-time messaging (WebSocket), file upload/preview, email notifications (urgent/normal blocks), and role-based access control (client/developer).

## Tech Stack
- FastAPI (REST + WebSocket)
- SQLAlchemy + MySQL
- JWT Authentication
- Local file storage (`/storage/files/{file_id}/{filename}`)
- Resend API (email)

## Key Features
- Mainform + Subform negotiation (only one active subform per mainform)
- Functions / NonFunctions (NFR) management with `is_changed` for subform diffs
- Block-based messaging (general / function / nonfunction)
- Real-time message push via WebSocket
- Email reminders:
  - urgent: no reply in 5 minutes
  - normal: no reply in 48 hours
- File upload (≤ 10MB) with preview endpoints

## Directory Structure
```text
backend/
  app/
    api/ v1/
    services/
    repositories/
    models/
    schemas/
    core/
    utils/
    main.py
  storage/
  tests/
