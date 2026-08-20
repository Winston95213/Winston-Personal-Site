# Personal Engineering Platform

A TypeScript + Vue portfolio backed by Django. Phase 3 adds secure, invitation-only one-to-one chat rooms; personal details live in `src/data.ts`.

## Start locally

1. Copy `.env.example` to backend `.env` or export its values. Use PostgreSQL in production; the development default is SQLite.
2. In `backend/`, run `python3 manage.py makemigrations portfolio`, `python3 manage.py migrate`, and `python3 manage.py createsuperuser`.
3. Run `./venv/bin/python backend/manage.py runserver 8080` in one terminal and `npm run dev` in another. Open `http://127.0.0.1:5173` for the portfolio; Vite forwards `/api` and `/media` requests to Django on port 8080.

## Security model

- Owner authentication uses Django’s signed, HTTP-only session cookie; all owner actions check it server-side.
- Chat URLs use crypto-secure random IDs. PINs are Django password hashes and never included in a URL.
- Anonymous input is server-validated and Django’s ORM uses parameterized queries.
- CSRF protection is enabled on all write endpoints.
- Private chat details are documented in `docs/private-chat.md`.

## Before deploy

- Replace all values in `data/portfolio.ts` and add `public/resume.pdf`.
- Use a managed PostgreSQL database and run Django migrations.
- Add Redis-backed rate limiting and private S3-compatible object storage before production. The current local filesystem storage is for development only.
- Add a transactional email transport if contact-form notifications are needed.
