# Tree House 2 — CLAUDE.md

## Project Overview
Property management REST API built with Django. Handles user auth (Tenant, Landlord, Agent, Admin roles) with role-specific profiles. Agents are appointed by landlords to manage specific properties. Includes rent collection, Stripe payments, invoice auto-generation, and email reminders. Maintenance requests to come.

## Tech Stack
- **Django 4.2** + **Django REST Framework**
- **dj-rest-auth** + **django-allauth** — registration, login, email verification, password reset
- **Token authentication** (DRF `rest_framework.authtoken`)
- **drf-spectacular** — auto-generated Swagger/ReDoc docs
- **PostgreSQL** via Supabase (connection pooler on port 5432)
- **dj-database-url** — parses DB connection from env vars
- **Stripe** — payment processing (`stripe` SDK)
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
DEFAULT_FROM_EMAIL=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
```

Stripe keys use `sk_test_placeholder` / `whsec_placeholder` as defaults until real keys are added.

DB connects via Supabase transaction pooler (`aws-1-eu-west-1.pooler.supabase.com:5432`). If connection fails, check that the Supabase project is not paused (free tier pauses after inactivity).

## Common Commands
```bash
python manage.py runserver          # start dev server (default port 8000)
python manage.py runserver 8001     # use alternate port if 8000 is taken
python manage.py migrate            # apply migrations
python manage.py test authentication
python manage.py test property
python manage.py test billing
python manage.py process_billing      # generate invoices, apply late fees, send reminders
```

Kill port 8000 if already in use:
```bash
lsof -ti:8000 | xargs kill -9
```

## Project Structure
```
treeHouse/          # project config (settings, urls, wsgi)
authentication/     # user management app
  models.py         # Role, CustomUser, TenantProfile, LandlordProfile, AgentProfile
  serializers.py    # serializers for all models
  views.py          # function-based views using @api_view
  urls.py           # all URL patterns under /api/auth/
  adapter.py        # CustomAccountAdapter — saves extra fields on registration
  migrations/       # 0004 seeds the 4 roles via data migration
property/           # property management app
  models.py         # Property, Unit, Lease, PropertyImage, PropertyAgent
  serializers.py    # serializers for all models
  views.py          # CRUD views + permission helpers (is_landlord, is_admin, is_agent_for)
  urls.py           # all URL patterns under /api/property/
  migrations/       # 0005 adds PropertyAgent
billing/            # rent collection and invoicing app
  models.py         # BillingConfig, Invoice, Payment, Receipt, ReminderLog
  serializers.py    # serializers for all models
  views.py          # billing endpoints + Stripe webhook handler
  urls.py           # all URL patterns under /api/billing/
  utils.py          # generate_receipt_number() — format: RCP-YYYYMM-XXXX
  migrations/       # 0001 initial schema
  management/commands/process_billing.py  # daily command: invoices + late fees + reminders
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

### Auth (`/api/auth/`)
| Method | URL | Description |
|--------|-----|-------------|
| POST | `/api/auth/register/` | Register new user |
| POST | `/api/auth/login/` | Login, returns token |
| POST | `/api/auth/logout/` | Logout |
| GET | `/api/auth/user/` | Current user details |
| POST | `/api/auth/password/reset/` | Request password reset email |
| POST | `/api/auth/password/reset/confirm/` | Confirm password reset |
| GET/POST | `/api/auth/roles/` | List / create roles |
| GET/PUT/DELETE | `/api/auth/roles/<pk>/` | Role detail |
| GET/POST | `/api/auth/profiles/tenant/` | List / create tenant profiles |
| GET/PUT/DELETE | `/api/auth/profiles/tenant/<pk>/` | Tenant profile detail |
| GET/POST | `/api/auth/profiles/landlord/` | List / create landlord profiles |
| GET/PUT/DELETE | `/api/auth/profiles/landlord/<pk>/` | Landlord profile detail |
| GET/POST | `/api/auth/profiles/agent/` | List / create agent profiles |
| GET/PUT/DELETE | `/api/auth/profiles/agent/<pk>/` | Agent profile detail |

### Property (`/api/property/`)
| Method | URL | Who |
|--------|-----|-----|
| GET | `/api/property/properties/` | Admin=all, Landlord=own, Agent=assigned |
| POST | `/api/property/properties/` | Landlord only |
| GET/PUT | `/api/property/properties/<pk>/` | Admin, owner, assigned agent |
| DELETE | `/api/property/properties/<pk>/` | Admin, owner only |
| GET | `/api/property/properties/<pk>/units/` | Any authenticated |
| POST | `/api/property/properties/<pk>/units/` | Admin, owner, assigned agent |
| GET/POST | `/api/property/properties/<pk>/agents/` | Admin, owner only |
| DELETE | `/api/property/properties/<pk>/agents/<id>/` | Admin, owner only |
| GET/PUT | `/api/property/units/<pk>/` | Admin, owner, assigned agent |
| DELETE | `/api/property/units/<pk>/` | Admin, owner only |
| GET/POST | `/api/property/units/<pk>/images/` | GET=any, POST=admin/owner/agent |
| GET/POST | `/api/property/units/<pk>/lease/` | Admin, owner, assigned agent |
| GET | `/api/property/units/public/` | No auth required |

### Billing (`/api/billing/`)
| Method | URL | Who |
|--------|-----|-----|
| GET/POST | `/api/billing/config/<property_id>/` | Owner/Admin |
| GET | `/api/billing/invoices/` | Admin=all, Landlord=own properties, Agent=assigned, Tenant=own |
| GET | `/api/billing/invoices/<pk>/` | Owner/Agent/Tenant |
| POST | `/api/billing/invoices/<pk>/pay/` | Tenant only |
| GET | `/api/billing/invoices/<pk>/payments/` | Owner/Agent/Tenant |
| GET | `/api/billing/receipts/` | Scoped by role |
| GET | `/api/billing/receipts/<pk>/` | Owner/Agent/Tenant |
| POST | `/api/billing/stripe/webhook/` | Stripe (no auth, CSRF exempt) |

### Docs
| GET | `/api/docs/` | Swagger UI |
| GET | `/api/redoc/` | ReDoc |
| GET | `/api/schema/` | OpenAPI schema download |

## Coding Conventions

### Views
- Always use function-based views with `@api_view` and `@permission_classes([IsAuthenticated])`
- Never use class-based views unless integrating a third-party library that requires it
- PUT endpoints always use `partial=True` on the serializer — callers only send what they want to change
- Shared view logic goes in factory functions (see `_profile_list_view` / `_profile_detail_view` pattern)
- Always add `@extend_schema` with `OpenApiExample` when writing a new view — request body examples are required

### Models
- New domain entities that are role-specific get their own profile table as a `OneToOneField` to `CustomUser`
- Many-to-many relationships with extra data (e.g. who appointed, when) use an explicit through model — see `PropertyAgent`
- Always define `__str__` on every model
- List queries on related models use `select_related` to avoid N+1 queries

### Permissions
- Permission helpers live at the top of each app's `views.py`: `is_landlord`, `is_admin`, `is_agent_for`
- Role name checks must match the seeded casing exactly — roles are title-cased: `'Landlord'`, `'Admin'`, `'Agent'`, `'Tenant'`
- Agents can read and write but never delete — delete is owner/admin only

### Migrations
- Always write migrations manually — psycopg2 won't build from source in this venv so `makemigrations` can't run
- Seed/reference data goes in a data migration, not fixtures
- Data migrations always use `get_or_create` so they're safe to re-run
- Name migrations descriptively: `0003_add_profile_models`, `0004_seed_roles`

### Serializers
- Use `ModelSerializer` for all models
- Explicitly list `fields` — never use `fields = '__all__'`

### Tests
- Every new endpoint gets tests covering: list, create, retrieve, update, delete, and 404
- Each test class has a `setUp` that creates a role, user, and token, and sets client credentials
- Use the `make_user(username, role_name)` helper pattern (see `property/tests.py`) to reduce setUp boilerplate
- Tests live in the app's `tests.py`
- Permission boundary tests are required — test that the wrong role gets 403, not just that the right role succeeds

---

## Workflow Rules

### Before building new models
- Show a DB diagram first and get sign-off before writing any code
- Identify how the new model relates to `CustomUser` and existing models before proposing fields

### Before building new endpoints
- Confirm the URL structure and HTTP methods first
- New endpoints always ship with: serializer + view + URL pattern + swagger example + tests — all in one go

### Migrations
- Never run `makemigrations` — write migration files by hand
- Schema migration and data migration always go in separate files

### Stripe
- Webhook endpoint is CSRF exempt and uses `AllowAny` — Stripe signature verification replaces auth
- Payment flow: frontend receives `client_secret` from `/pay/` → Stripe confirms → webhook updates Payment + Invoice + generates Receipt
- Receipt numbers are auto-generated via `billing/utils.py` — never set manually
- `process_billing` must run daily via cron. Late fees and reminders only fire through this command — they are not triggered by API calls

### General
- Read a file before editing it
- Don't add new Django apps without confirming with the user first
- Keep `authentication/` concerns separate from other apps — no cross-app model imports
- Don't add error handling for impossible cases — only validate at system boundaries
