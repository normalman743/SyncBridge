# syncbridge-backend

FastAPI backend for **SyncBridge** — a web-based platform for structured requirement submission, negotiation (subforms), real-time messaging (WebSocket), file upload/preview, email notifications (urgent/normal blocks), and role-based access control (client/developer).

## Python Version
Python 3.10.13


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

## Environment Variables
- **`RESEND_API_KEY`**: Resend API key for sending emails.
- **`RESEND_SENDER_EMAIL`**: Sender email address (e.g., bridge-no-reply@icu.584743.xyz).
- **`REMINDER_URGENT_MINUTES`**: Minutes threshold before urgent reminder (default: `5`).
- **`REMINDER_NORMAL_HOURS`**: Hours threshold before normal reminder (default: `48`).
- **`REMINDER_URGENT_CHECK_SECONDS`**: Urgent loop interval seconds (default: `60`).
- **`REMINDER_NORMAL_CHECK_SECONDS`**: Normal loop interval seconds (default: `3600`).

## Directory Structure
```text
syncbridge-backend/
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
