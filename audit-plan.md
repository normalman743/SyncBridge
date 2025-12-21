# Audit/History Plan (draft)

## Goals
- Track who changed what and when for core entities (form, function, nonfunction, message, file).
- Keep minimal, structured records suitable for troubleshooting and compliance.

## Data Model
- Table `audit_logs` (new):
  - id (pk, bigint)
  - entity_type (enum: form, function, nonfunction, message, file)
  - entity_id (int)
  - action (enum: create, update, delete, status_change, merge_subform)
  - user_id (int, nullable if system)
  - old_data (json, nullable)
  - new_data (json, nullable)
  - created_at (datetime, default now)
- Indexes: (entity_type, entity_id), (created_at), (user_id).

## Write Points (MVP)
- Form status change (`PUT /form/{id}/status`): log status_change with old/new status.
- Form content update (`PUT /form/{id}`): log update with old/new fields actually changed.
- Subform merge (`POST /form/{mainform_id}/subform/merge`): log merge_subform with copied fields and source subform id.
- Function/NonFunction CRUD: log create/update/delete with relevant fields.
- Message delete: log delete with text snippet (not full history of all messages).
- File delete: log delete with file_name/size/message_id.

## Read API (MVP)
- **NOT IMPLEMENTED YET**: No API endpoint for now. Data stored for future admin use only.
- Will be added later when admin role/dashboard is implemented.

## Non-Goals (for now)
- Full diff of message bodies over time (only delete is logged).
- Versioned restores/rollbacks.
- Per-field diff rendering; we store snapshots of changed fields only.
- API endpoints for querying audit logs (future work).

## Steps to Implement
1) Alembic migration: create `audit_logs` table with enums and indexes.
2) Model + isolated service helper: insert_log(entity_type, entity_id, action, user_id, old_data, new_data) wrapped in try-except to never break main flow.
3) Hook write points in routers/services with safe calls (forms status/update, merge, func/nonfunc CRUD, message/file delete).
4) NO API endpoint for now; data stored for future admin use.
5) Tests/manual checks: create/update/delete paths produce audit rows; failures logged but do not interrupt business logic.

## Isolation & Error Handling
- All audit writes are wrapped in try-except; failures are silently logged (or to a monitoring system).
- Audit failures will NOT cause HTTP errors or rollback main transactions.
- Audit logs are written AFTER main transaction commits (post-commit or best-effort).

## Open Questions
- Do we need to log message creation/edit as well, or only deletes? (current plan: only deletes.)
- Should admin/system actions be supported (user_id nullable)?
- Retention policy (e.g., keep 180 days)?
