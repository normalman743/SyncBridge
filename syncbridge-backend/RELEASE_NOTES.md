# SyncBridge Backend Release Notes

Version: 0.33.89
Stats: 33 PRs, 89 commits (as of HEAD)
Date: 2025-12-22
Scope: Backend (app/)

## Completed
- User registration/login with JWT, license activation/validation, and role-based access (client/developer).
- Requirement submission, detail view, and lifecycle management (preview -> available -> processing -> rewrite/error/end) with mutual approval flags.
- Subform negotiation flow (create/merge/terminate) and requirement item management (functions/nonfunctions).
- Messaging by blocks (general/function/nonfunction) with WebSocket real-time updates.
- File upload/download with 10MB limit and access checks.
- Email reminders for urgent/normal blocks (5 minutes / 48 hours).
- Audit logging for CRUD and status changes.

## Partially Completed
- Notifications: reminders only; no event-triggered emails for submission/status/message.
- Functions/Nonfunctions: `is_changed` exists but is not enforced to be subform-only.
- Files: no preview endpoint; external-link fallback is manual (message text).
- Audit access: logs recorded but no query/export API.
- License events: activation/validation work, but license-specific audit entries are not exposed.

## Not Implemented (Planned)
- Logout endpoint and password recovery workflow.
- Notification preferences.
- Form aggregation endpoint (`GET /form/{id}/full`).
- CORS configuration and rate limiting.
- Unit/integration tests and monitoring endpoints.
