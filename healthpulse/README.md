# HealthPulse

Personal Health Record & Appointment Management System — a single-page
Django dashboard for patients and doctors.

## Architecture

- **Django auth (SQLite)** — `User`, `Session`, `Profile` (role: patient/doctor).
  Kept on SQLite so login/logout/password handling uses Django's built-in,
  battle-tested auth stack.
- **MongoDB (via MongoEngine)** — all clinical/domain data: `Patient`,
  `Doctor`, `Vitals`, `Appointment`, `Notification`. Each document links back
  to its Django user via `django_user_id`.
- **No REST framework / PDF-CSV export yet** — scoped out of this pass on
  purpose. The AJAX endpoints under each app's `views.py` (returning
  `JsonResponse`) are what the dashboard's JS calls; they're a natural place
  to layer DRF serializers on top of later if you want a documented public API.
- **Threaded reminders** — `appointments/reminders.py` uses
  `threading.Timer` to fire an in-app notification 1 day / 2 hours / 30
  minutes before an appointment. This only works while the Django process
  stays alive (fine for `runserver` or a single worker; a restart drops
  pending reminders, and it won't scale across multiple gunicorn workers).
  For real production use, swap this for Celery + Redis/RabbitMQ.

## Setup

1. **Install MongoDB** locally (or point at a remote instance) — e.g. on
   macOS: `brew install mongodb-community && brew services start mongodb-community`.
   On Linux, follow MongoDB's official install docs for your distro. Default
   settings assume `localhost:27017` with no auth.

2. **Create a virtual environment and install dependencies:**
   ```bash
   python -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # edit .env if your Mongo instance isn't on localhost:27017
   ```

4. **Run Django migrations** (this only sets up the SQLite auth tables —
   MongoDB collections are created automatically the first time a document
   is saved):
   ```bash
   python manage.py makemigrations accounts
   python manage.py migrate
   ```

5. **(Optional) create an admin user for `/admin/`:**
   ```bash
   python manage.py createsuperuser
   ```

6. **(Optional) seed demo data** — creates 2 doctors + 2 patients with
   sample vitals and an upcoming appointment:
   ```bash
   python manage.py seed_data
   ```
   Demo logins (password `password123` for all):
   - Doctors: `dr.mehta`, `dr.rao`
   - Patients: `asha.k`, `rahul.s`

7. **Run the dev server:**
   ```bash
   python manage.py runserver
   ```
   Visit `http://127.0.0.1:8000/accounts/register/` to create an account, or
   log in with a seeded account above.

## Project layout

```
healthpulse/        Django project settings, root URLs
accounts/            Profile model (role), registration/login/logout, settings
core/                Dashboard shell view, global search, seed_data command
patients/            Patient MongoEngine document, CRUD + search endpoints
doctors/             Doctor MongoEngine document, directory + appointments
vitals/              Vitals MongoEngine document, add/chart/summary endpoints
appointments/        Appointment document, booking (with rollback), reminders
notifications/       Notification document, list/mark-read endpoints
common/               Regex validators, custom exceptions, JSON error decorator
templates/           base.html (shell) + dashboard.html (all tabs) + auth pages
static/css/style.css  Glassmorphism theme (blue/white/green), dark mode
static/js/dashboard.js Tab switching, AJAX calls, Chart.js wiring, notifications
```

## What's intentionally not built yet

- Django REST Framework `/api/` endpoints (the current AJAX views return
  JSON but aren't DRF serializers/viewsets)
- PDF/CSV report export
- Email/SMS delivery for notifications (the "email/SMS" toggles in Settings
  are stored on the Profile but nothing sends anything yet — notifications
  are in-app only)
- Automated tests

## Known simplification: appointment "transactions"

MongoDB without a replica set doesn't give you multi-document ACID
transactions the way a relational DB does. `appointments/views.py`
implements a practical approximation: save the appointment, then create the
dependent notification/reminder; if anything in that second step throws, the
appointment document is deleted again (a manual rollback) and the error is
surfaced to the user. It also re-checks for a same-slot race right after the
initial save to reduce (not eliminate) double-booking under concurrent
requests. For guaranteed atomicity you'd want a Mongo replica set with
`mongoengine`'s session/transaction support, or move slot-booking to a
relational table with a unique constraint.
