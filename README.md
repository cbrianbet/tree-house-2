# Tree House

A property management REST API built with Django. Handles the full lifecycle of residential rentals — from listing and tenant applications through rent collection, maintenance, disputes, and moving.

[![Django CI](https://github.com/cbrianbet/tree-house-2/actions/workflows/django.yml/badge.svg)](https://github.com/cbrianbet/tree-house-2/actions/workflows/django.yml)

---

## What it does

| App | Responsibility |
|-----|---------------|
| `authentication` | User accounts, roles, and role-specific profiles |
| `property` | Properties, units, leases, tenant applications, reviews, saved searches |
| `billing` | Invoices, Stripe payments, receipts, expenses, and financial reports |
| `maintenance` | Maintenance requests with artisan bidding |
| `notifications` | In-app notifications and email preferences |
| `messaging` | Polling-based conversations between users |
| `disputes` | Dispute tracking with a mediation workflow |
| `moving` | Moving company directory, bookings, and reviews |
| `neighborhood` | Neighborhood insights (schools, transit, safety) per property |
| `dashboard` | Role-specific dashboards for all user types |
| `monitoring` | System metrics, alert rules, and admin impersonation |

---

## Roles

Six roles are seeded by data migration. Each role has a profile table with role-specific fields.

| Role | Profile model | Notes |
|------|--------------|-------|
| Admin | — | `is_staff=True`, no profile table |
| Landlord | `LandlordProfile` | Owns properties |
| Agent | `AgentProfile` | Appointed by landlords to manage specific properties |
| Tenant | `TenantProfile` | Applies for and occupies units |
| Artisan | `ArtisanProfile` | Bids on maintenance requests |
| MovingCompany | `MovingCompanyProfile` | Lists services and receives bookings |

---

## Quick start

```bash
git clone https://github.com/cbrianbet/tree-house-2.git
cd tree-house-2
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your values
python manage.py migrate
python manage.py runserver
```

The API will be available at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/api/docs/`

> See [docs/setup.md](docs/setup.md) for a full step-by-step guide including Supabase database setup.

---

## Environment variables

Create a `.env` file at the project root:

```env
DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=5432

SECRET_KEY=

EMAIL_CONFIRM_REDIRECT_BASE_URL=http://localhost:8000/email-confirm/
PASSWORD_RESET_CONFIRM_REDIRECT_BASE_URL=http://localhost:8000/password-reset-confirm/
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

STRIPE_SECRET_KEY=sk_test_placeholder
STRIPE_WEBHOOK_SECRET=whsec_placeholder
```

The database connects via the Supabase transaction pooler. Stripe keys default to test placeholders until real keys are added.

---

## Running tests

Each app has its own test suite:

```bash
python manage.py test authentication
python manage.py test property
python manage.py test billing
python manage.py test maintenance
python manage.py test notifications
python manage.py test messaging
python manage.py test disputes
python manage.py test moving
python manage.py test neighborhood
python manage.py test dashboard
python manage.py test monitoring
```

Run everything:

```bash
python manage.py test --noinput
```

---

## Management commands

| Command | Schedule | Description |
|---------|----------|-------------|
| `python manage.py process_billing` | Daily | Generates monthly invoices, applies late fees, sends payment reminders |
| `python manage.py match_saved_searches` | Daily | Matches recently published units against saved searches and notifies users |
| `python manage.py record_metrics` | Every 15 min | Snapshots platform metrics (occupancy, revenue, overdue invoices, etc.) |
| `python manage.py check_alert_rules` | Every 15 min | Evaluates alert rules against latest metrics; fires or auto-resolves alerts |

---

## API entry points

| URL | Description |
|-----|-------------|
| `POST /api/auth/register/` | Register a new user |
| `POST /api/auth/login/` | Obtain an auth token |
| `GET /api/property/units/public/` | Browse available units (no auth required) |
| `GET /api/docs/` | Swagger UI — full interactive API reference |
| `GET /api/redoc/` | ReDoc — alternative API reference |
| `GET /api/schema/` | OpenAPI schema download |

All protected endpoints require:
```
Authorization: Token <your-token>
```

---

## Documentation

| Document | Audience |
|----------|---------|
| [CLAUDE.md](CLAUDE.md) | Developer reference — full coding conventions, all models, all endpoints, business logic |
| [docs/api-integration.md](docs/api-integration.md) | Frontend developers — permissions matrix, request/response examples for every endpoint |
| [docs/setup.md](docs/setup.md) | Anyone setting up the project — local dev, environment config, Supabase setup |
| [docs/backlog.md](docs/backlog.md) | Team — known issues, planned features, and improvement priorities |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contributors — coding conventions, migration rules, PR process |

---

## Tech stack

- **Python 3.14** · **Django 4.2** · **Django REST Framework 3.16**
- **PostgreSQL** via Supabase (connection pooler, port 5432)
- **Token authentication** (DRF `rest_framework.authtoken`)
- **dj-rest-auth** + **django-allauth** — registration, email verification, password reset
- **drf-spectacular** — auto-generated Swagger/ReDoc docs
- **Stripe** — payment processing
- **GitHub Actions** — CI with PostgreSQL 15 service
