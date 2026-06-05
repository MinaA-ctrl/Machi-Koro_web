# TASK-006 — Table Password API Contract (canonical)

> Shared interface between Backend (api.php) and Web (app.js). PM-owned. Frontend is already built to this; Backend must conform.

## Rule
- `is_protected` is the **only** flag exposed to clients (boolean, = `password_hash IS NOT NULL`).
- **Never** return `password_hash` (or `host_id`) to the client. See WEB-001.

## Endpoints

### POST `/tables` (create)
- **Body:** `{ name, is_public, password? }` — `password` optional; when present & non-empty, store `wp_hash_password(password)` in `password_hash`.
- **Response:** `{ code }`

### GET `/tables` (list) and GET `/tables/{code}` (detail)
- **Response includes:** `is_protected` (bool). **Excludes** `password_hash`, `host_id`.

### POST `/tables/{code}/join`
- **Body:** `{ guest_name?, password? }`
- **Behavior:** if table is protected → require `password`, verify with `wp_check_password()`. Wrong/missing → **403** `{ error }`.
- **Response (success):** `{ seat }`

## Frontend behavior (already implemented)
- Create panel: optional "Password (optional)" field → sent only when typed.
- List: 🔒 shown when `is_protected` is true.
- Join: protected tables open a modal; 403 keeps modal open with retryable "Wrong password. Try again." Degrades gracefully if `is_protected` absent (no flag → no prompt).
