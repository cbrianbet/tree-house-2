# Tree House 2 — CLAUDE.md

## Project Overview
Property management REST API built with Django. Handles user auth (Tenant, Landlord, Agent, Admin roles) with role-specific profiles. More domain models (properties, leases, payments) to come.

## Tech Stack
- **Django 4.2** + **Django REST Framework**
- **dj-rest-auth** + **django-allauth** — registration, login, email verification, password reset
- **Token authentication** (DRF `rest_framework.authtoken`)
- **drf-spectacular** — auto-generated Swagger/ReDoc docs
- **PostgreSQL** via Supabase (connection pooler on port 5432)
- **dj-database-url** — parses DB connection from env vars
- **Python 3.14**, virtualenv at `venv/`

## Environment Setup
```bash
source venv/bin/activate
pip install -r requirements.txt
```

`.env` file required at project root with:
```
DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=
EMAIL_CONFIRM_REDIRECT_BASE_URL=
PASSWORD_RESET_CONFIRM_REDIRECT_BASE_URL=
```

DB connects via Supabase transaction pooler (`aws-1-eu-west-1.pooler.supabase.com:5432`). If connection fails, check that the Supabase project is not paused (free tier pauses after inactivity).

## Common Commands
```bash
python manage.py runserver          # start dev server (default port 8000)
python manage.py runserver 8001     # use alternate port if 8000 is taken
python manage.py migrate            # apply migrations
python manage.py makemigrations authentication --name="<name>"
python manage.py test authentication
```

Kill port 8000 if already in use:
```bash
lsof -ti:8000 | xargs kill -9
```

## Project Structure
```
treeHouse/          # project config (settings, urls, wsgi)
authentication/     # main app
  models.py         # Role, CustomUser, TenantProfile, LandlordProfile, AgentProfile
  serializers.py    # serializers for all models
  views.py          # function-based views using @api_view
  urls.py           # all URL patterns
  adapter.py        # CustomAccountAdapter — saves extra fields on registration
  migrations/       # includes data migration (0004) that seeds the 4 roles
templates/          # Django templates directory
```

## Auth Flow
- Registration: `POST /api/auth/register/` — creates user, triggers email verification (console backend in dev)
- Login: `POST /api/auth/login/` — returns a Token
- All protected endpoints require: `Authorization: Token <token>`

## Roles
Seeded via migration `0004_seed_roles`. The four roles are:
- **Admin** — platform administrator, no profile table (`is_staff=True`)
- **Landlord** — has `LandlordProfile` (company_name, tax_id, verified)
- **Agent** — has `AgentProfile` (agency_name, license_number, commission_rate)
- **Tenant** — has `TenantProfile` (national_id, emergency_contact_name, emergency_contact_phone)

## API Endpoints
| Method | URL | Description |
|--------|-----|-------------|
| POST | `/api/auth/register/` | Register new user |
| POST | `/api/auth/login/` | Login, returns token |
| POST | `/api/auth/logout/` | Logout |
| GET | `/api/auth/user/` | Current user details |
| POST | `/api/auth/password/reset/` | Request password reset |
| POST | `/api/auth/password/reset/confirm/` | Confirm password reset |
| GET/POST | `/api/auth/roles/` | List / create roles |
| GET/PUT/DELETE | `/api/auth/roles/<pk>/` | Role detail |
| GET/POST | `/api/auth/profiles/tenant/` | List / create tenant profiles |
| GET/PUT/DELETE | `/api/auth/profiles/tenant/<pk>/` | Tenant profile detail |
| GET/POST | `/api/auth/profiles/landlord/` | List / create landlord profiles |
| GET/PUT/DELETE | `/api/auth/profiles/landlord/<pk>/` | Landlord profile detail |
| GET/POST | `/api/auth/profiles/agent/` | List / create agent profiles |
| GET/PUT/DELETE | `/api/auth/profiles/agent/<pk>/` | Agent profile detail |
| GET | `/api/docs/` | Swagger UI |
| GET | `/api/redoc/` | ReDoc |
| GET | `/api/schema/` | OpenAPI schema download |

## Conventions
- Views are function-based using `@api_view` and `@permission_classes([IsAuthenticated])`
- All profile views share logic via `_profile_list_view` / `_profile_detail_view` factory functions in `views.py`
- PUT on detail endpoints uses `partial=True` (no need to send all fields)
- Migrations are written manually (psycopg2 won't build from source in this venv)
- Data migrations use `get_or_create` so they're safe to run multiple times
