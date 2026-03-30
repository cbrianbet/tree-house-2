# Tree House 2 — CLAUDE.md

## Project Overview
Property management REST API built with Django. Handles user auth (Tenant, Landlord, Agent, Admin, Artisan roles) with role-specific profiles. Agents are appointed by landlords to manage specific properties. Includes rent collection, Stripe payments, invoice auto-generation, email reminders, and a maintenance request/bidding system where artisans bid on work and tenants/landlords accept bids.

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
python manage.py test maintenance
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
  models.py         # Role, CustomUser, TenantProfile, LandlordProfile, AgentProfile, ArtisanProfile
  serializers.py    # serializers for all models
  views.py          # function-based views using @api_view
  urls.py           # all URL patterns under /api/auth/
  adapter.py        # CustomAccountAdapter — saves extra fields on registration
  migrations/       # 0004 seeds roles, 0005 adds ArtisanProfile, 0006 seeds Artisan role
property/           # property management app
  models.py         # Property, Unit, Lease, PropertyImage, PropertyAgent, TenantApplication
  serializers.py    # serializers for all models
  views.py          # CRUD views + permission helpers (is_landlord, is_admin, is_agent_for) + dashboard
  urls.py           # all URL patterns under /api/property/
  migrations/       # 0005 adds PropertyAgent, 0006 adds TenantApplication
billing/            # rent collection, invoicing, expenses, and reporting app
  models.py         # BillingConfig, Invoice, Payment, Receipt, ReminderLog, ChargeType, AdditionalIncome, Expense
  serializers.py    # serializers for all models
  views.py          # billing endpoints + Stripe webhook handler + financial report
  urls.py           # all URL patterns under /api/billing/
  utils.py          # generate_receipt_number() — format: RCP-YYYYMM-XXXX
  migrations/       # 0001 initial schema, 0002 adds ChargeType/AdditionalIncome/Expense
  management/commands/process_billing.py  # daily command: invoices + late fees + reminders
maintenance/        # maintenance request & bidding app
  models.py         # MaintenanceRequest, MaintenanceBid, MaintenanceNote, MaintenanceImage
  serializers.py    # serializers for all models
  views.py          # views + permission helpers (is_artisan, can_view_request, can_manage_request)
  urls.py           # all URL patterns under /api/maintenance/
  migrations/       # 0001 initial schema
templates/          # Django templates directory
```

## Auth Flow
- Registration: `POST /api/auth/register/` — creates user, triggers email verification (console backend in dev)
- Login: `POST /api/auth/login/` — returns a Token
- All protected endpoints require: `Authorization: Token <token>`

## Roles
Seeded via data migrations. Roles are:
- **Admin** — platform administrator, no profile table (`is_staff=True`)
- **Landlord** — has `LandlordProfile` (company_name, tax_id, verified)
- **Agent** — has `AgentProfile` (agency_name, license_number, commission_rate); appointed to properties by landlords
- **Tenant** — has `TenantProfile` (national_id, emergency_contact_name, emergency_contact_phone)
- **Artisan** — has `ArtisanProfile` (trade, bio, rating, verified); trade choices: plumbing, electrical, carpentry, painting, masonry, other

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
| GET/POST | `/api/auth/profiles/artisan/` | List / create artisan profiles |
| GET/PUT/DELETE | `/api/auth/profiles/artisan/<pk>/` | Artisan profile detail |

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
| GET/POST | `/api/property/applications/` | Landlord=own units, Tenant=own, Admin=all |
| GET/PUT | `/api/property/applications/<pk>/` | Landlord: approve/reject — Tenant: withdraw |
| GET | `/api/property/dashboard/` | Landlord / Admin |

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
| GET/POST | `/api/billing/properties/<pk>/charge-types/` | Owner/Admin (GET: Agent too) |
| GET/PUT/DELETE | `/api/billing/properties/<pk>/charge-types/<id>/` | Owner/Admin |
| GET/POST | `/api/billing/properties/<pk>/additional-income/` | Owner/Admin (GET: Agent too) |
| GET/PUT/DELETE | `/api/billing/properties/<pk>/additional-income/<id>/` | Owner/Admin |
| GET/POST | `/api/billing/properties/<pk>/expenses/` | Owner/Admin (GET: Agent too) |
| GET/PUT/DELETE | `/api/billing/properties/<pk>/expenses/<id>/` | Owner/Admin |
| GET | `/api/billing/reports/<pk>/?year=2024&month=3` | Owner/Agent/Admin — monthly report |
| GET | `/api/billing/reports/<pk>/?year=2024` | Owner/Agent/Admin — annual report |

### Maintenance (`/api/maintenance/`)
| Method | URL | Who |
|--------|-----|-----|
| GET | `/api/maintenance/requests/` | Admin=all, Landlord=own properties, Agent=assigned, Artisan=open requests matching trade, Tenant=own submitted |
| POST | `/api/maintenance/requests/` | Tenant or Landlord only (Agents and Artisans cannot submit) |
| GET | `/api/maintenance/requests/<pk>/` | Submitter, property owner, assigned agent, assigned artisan, admin |
| PUT | `/api/maintenance/requests/<pk>/` | Status transitions (see below) or field edits (submitter/admin only) |
| GET | `/api/maintenance/requests/<pk>/bids/` | Artisan=own bid, others=all bids if can_view_request |
| POST | `/api/maintenance/requests/<pk>/bids/` | Artisan only, request must be `open`, one bid per artisan |
| PUT | `/api/maintenance/requests/<pk>/bids/<bid_id>/` | Submitter only — `{"status": "accepted"}` or `{"status": "rejected"}` |
| GET/POST | `/api/maintenance/requests/<pk>/notes/` | Anyone who can view the request |
| GET/POST | `/api/maintenance/requests/<pk>/images/` | Anyone who can view the request |

**Maintenance request status machine:**
```
submitted → open         (property owner only — opens request for bidding)
open      → assigned     (auto: triggered when submitter accepts a bid)
assigned  → in_progress  (assigned artisan only)
in_progress → completed  (request submitter only)
submitted/open → cancelled  (request submitter only)
any → rejected           (property owner only)
```

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
- Permission helpers live at the top of each app's `views.py`: `is_landlord`, `is_admin`, `is_agent_for`, `is_artisan`
- Role name checks must match the seeded casing exactly — roles are title-cased: `'Landlord'`, `'Admin'`, `'Agent'`, `'Tenant'`, `'Artisan'`
- Agents can read and write but never delete — delete is owner/admin only
- Maintenance: submitter (tenant or landlord) owns accept/reject bids and marks completion; artisan owns in_progress transition

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

### Financial Reporting
- Reports are computed on the fly — no stored report model
- `ChargeType` is per-property; validate that `unit` and `charge_type` belong to the same property before saving `AdditionalIncome`
- `Expense` records are auto-created when a maintenance request transitions to `completed` — the accepted bid's `proposed_price` becomes the expense amount with `category='maintenance'`
- Report income = rent payments received + additional income entries; expenses = Expense records; net = income − expenses
- Annual report: `?year=2024`; monthly report: `?year=2024&month=3`

### Tenant Applications
- Only Tenants can submit applications; only the property owner or admin can approve/reject; only the applicant can withdraw
- Approving an application requires `start_date` and `rent_amount` in the payload — a `Lease` is auto-created and competing pending applications on the same unit are auto-rejected
- `unique_together = ('unit', 'applicant')` — one application per tenant per unit

### Dashboard
- `GET /api/property/dashboard/` is scoped automatically: landlord sees own portfolio, admin sees all
- Billing and maintenance data are imported lazily inside the view to avoid cross-app import issues
- "Almost ending leases" threshold is 60 days; "adverts" are units with `is_public=True` and `is_occupied=False`
- Performance ranking is by net income (`payments + additional_income − expenses`) for the current calendar month

### General
- Read a file before editing it
- Don't add new Django apps without confirming with the user first
- Keep `authentication/` concerns separate from other apps — no cross-app model imports
- Don't add error handling for impossible cases — only validate at system boundaries
