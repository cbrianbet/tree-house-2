# Tree House 2 — CLAUDE.md

## Project Overview
Property management REST API built with Django. Handles user auth (Tenant, Landlord, Agent, Admin, Artisan roles) with role-specific profiles. Agents are appointed by landlords to manage specific properties. Includes rent collection, Stripe payments, invoice auto-generation, email reminders, a maintenance request/bidding system where artisans bid on work, in-app notifications, polling-based messaging between users, dispute tracking with mediation support, lease document storage with digital signing, and property/tenant review systems.

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
TENANT_INVITE_REDIRECT_BASE_URL=
DEFAULT_FROM_EMAIL=
MAILGUN_API_KEY=
MAILGUN_SENDER_DOMAIN=
# MAILGUN_EU=true
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
```

Stripe keys use `sk_test_placeholder` / `whsec_placeholder` as defaults until real keys are added.

**Email:** With both `MAILGUN_API_KEY` and `MAILGUN_SENDER_DOMAIN` set, Django sends via [Mailgun](https://www.mailgun.com/) (`django-anymail`). Otherwise email uses the console backend in dev. Set `DEFAULT_FROM_EMAIL` to an address on your verified Mailgun domain (e.g. `noreply@mg.example.com`). For Mailgun EU hosting, set `MAILGUN_EU=true`.

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
python manage.py test notifications
python manage.py test messaging
python manage.py test disputes
python manage.py test moving
python manage.py test neighborhood
python manage.py test dashboard
python manage.py process_billing                        # generate invoices, apply late fees, send reminders
python manage.py match_saved_searches                   # match saved searches against recently published units
python manage.py match_saved_searches --days 7          # check last 7 days instead of 1
python manage.py record_metrics                         # snapshot current system metrics to the DB
python manage.py check_alert_rules                      # evaluate alert rules; fire/auto-resolve AlertInstances
```

Kill port 8000 if already in use:
```bash
lsof -ti:8000 | xargs kill -9
```

## Project Structure
```
treeHouse/          # project config (settings, urls, wsgi)
authentication/     # user management app
  models.py         # Role, CustomUser, TenantProfile, LandlordProfile, AgentProfile, ArtisanProfile, MovingCompanyProfile
  serializers.py    # serializers for all models
  views.py          # function-based views using @api_view
  urls.py           # all URL patterns under /api/auth/
  adapter.py        # CustomAccountAdapter — saves extra fields on registration
  migrations/       # 0004 seeds roles, 0005 adds ArtisanProfile, 0006 seeds Artisan role, 0008 adds MovingCompanyProfile, 0009 seeds MovingCompany role
property/           # property management app
  models.py         # Property, Unit, Lease, PropertyImage, PropertyAgent, TenantApplication, TenantInvitation
  serializers.py    # serializers for all models
  views.py          # CRUD views + permission helpers (is_landlord, is_admin, is_agent_for) + dashboard
  urls.py           # all URL patterns under /api/property/
  migrations/       # 0005 adds PropertyAgent, 0006 adds TenantApplication, 0009 adds TenantInvitation
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
notifications/      # in-app notification delivery
  models.py         # Notification (user, notification_type, title, body, action_url, is_read, created_at)
  utils.py          # create_notification(user, type, title, body, action_url='') — cross-app utility
  serializers.py    # NotificationSerializer
  views.py          # list (with ?unread=true filter), mark-read, mark-all-read
  urls.py           # /api/notifications/
  migrations/       # 0001 depends on authentication.0007
messaging/          # polling-based user-to-user messaging
  models.py         # Conversation (property FK nullable, subject, created_by), ConversationParticipant (unique: conversation+user), Message (conversation, sender, body)
  serializers.py    # ConversationSerializer (unread_count, last_message), MessageSerializer (sender_name)
  views.py          # list/create conversations, detail, list/post messages, mark-read
  urls.py           # /api/messaging/conversations/
  migrations/       # 0001 depends on authentication.0007 + property.0006
disputes/           # dispute tracking and mediation
  models.py         # Dispute (created_by, property, unit nullable, dispute_type, status, title, description, resolved_by, resolved_at), DisputeMessage (dispute, sender, body)
  serializers.py    # DisputeSerializer, DisputeMessageSerializer (sender_name)
  views.py          # list/create disputes, detail/status-patch, list/post messages; status machine enforced
  urls.py           # /api/disputes/
  migrations/       # 0001 depends on authentication.0007 + property.0006
moving/             # moving company directory, bookings, and reviews
  models.py         # MovingBooking (company, customer, moving_date, moving_time, pickup/delivery_address, status, estimated_price), MovingCompanyReview (company, reviewer, booking nullable, rating, comment)
  serializers.py    # MovingBookingSerializer, MovingCompanyReviewSerializer, MovingCompanyListSerializer (avg rating)
  views.py          # company directory, booking CRUD + status machine, review CRUD
  urls.py           # /api/moving/
  migrations/       # 0001 depends on authentication.0009
neighborhood/       # neighborhood insights per property (schools, hospitals, safety, etc.)
  models.py         # NeighborhoodInsight (property, insight_type, name, address, distance_km, rating, lat, lng, notes, added_by)
  serializers.py    # NeighborhoodInsightSerializer
  views.py          # list/create insights (landlord/agent/admin), detail/patch/delete (adder or admin)
  urls.py           # /api/neighborhood/
  migrations/       # 0001 depends on authentication.0009 + property.0008
monitoring/         # system monitoring, alert rules, and performance reporting (admin only)
  models.py         # SystemMetric, AlertRule, AlertInstance
  serializers.py    # serializers for all models
  views.py          # metric_list, alert_rule_list_create, alert_rule_detail, alert_list, alert_detail, monitoring_dashboard
  urls.py           # /api/monitoring/
  management/commands/record_metrics.py     # snapshot current platform metrics to SystemMetric
  management/commands/check_alert_rules.py  # evaluate enabled rules; fire/auto-resolve AlertInstances, notify admins
  migrations/       # 0001 initial schema, 0002 seeds 6 default alert rules
dashboard/          # cross-cutting dashboard endpoints for all roles
  models.py         # RoleChangeLog (user, changed_by, old_role, new_role, changed_at, reason)
  serializers.py    # AdminUserSerializer, AdminUserUpdateSerializer, RoleChangeLogSerializer
  views.py          # admin overview + user mgmt + review moderation; tenant/artisan/agent/moving-company dashboards
  urls.py           # /api/dashboard/
  migrations/       # 0001 depends on authentication.0009
templates/          # Django templates directory
```

## Auth Flow
- Registration: `POST /api/auth/register/` — creates user, triggers email verification (console backend in dev)
- Login: `POST /api/auth/login/` — returns a Token
- Tenant invite accept: `POST /api/auth/tenant-invite/accept/` — no auth; body includes invitation `token` and `password`; creates tenant user, profile, lease, returns auth `key` (same as login)
- All protected endpoints require: `Authorization: Token <token>`

## Roles
Seeded via data migrations. Roles are:
- **Admin** — platform administrator, no profile table (`is_staff=True`)
- **Landlord** — has `LandlordProfile` (company_name, tax_id, verified)
- **Agent** — has `AgentProfile` (agency_name, license_number, commission_rate); appointed to properties by landlords
- **Tenant** — has `TenantProfile` (national_id, emergency_contact_name, emergency_contact_phone)
- **Artisan** — has `ArtisanProfile` (trade, bio, rating, verified); trade choices: plumbing, electrical, carpentry, painting, masonry, other
- **MovingCompany** — has `MovingCompanyProfile` (company_name, description, phone, address, city, service_areas, base_price, price_per_km, is_verified, is_active); registers to offer relocation services

## API Endpoints

### Auth (`/api/auth/`)
| Method | URL | Description |
|--------|-----|-------------|
| POST | `/api/auth/register/` | Register new user |
| POST | `/api/auth/login/` | Login, returns token |
| POST | `/api/auth/tenant-invite/accept/` | Accept tenant invitation (no auth); returns token key + user |
| POST | `/api/auth/logout/` | Logout |
| GET | `/api/auth/user/` | Current user details (dj-rest-auth) |
| POST | `/api/auth/password/reset/` | Request password reset email |
| POST | `/api/auth/password/reset/confirm/` | Confirm password reset |
| POST | `/api/auth/password/change/` | Change password (authenticated) |
| GET/PATCH | `/api/auth/me/` | View / update own account (name, email, phone) |
| GET/PATCH | `/api/auth/me/profile/` | View / update own role profile (auto-creates if missing) |
| GET/PATCH | `/api/auth/me/notifications/` | View / update notification preferences (auto-creates if missing) |
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
| GET/POST | `/api/auth/profiles/moving-company/` | List / create moving company profiles |
| GET/PUT/DELETE | `/api/auth/profiles/moving-company/<pk>/` | Moving company profile detail |

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
| GET/POST | `/api/property/units/<pk>/tenant-invitations/` | List/create invites — owner or assigned agent; if email matches existing Tenant, creates lease instead of invite |
| POST | `/api/property/tenant-invitations/<pk>/resend/` | Owner or assigned agent — new token + email |
| GET | `/api/property/units/public/` | No auth required |
| GET/POST | `/api/property/applications/` | Landlord=own units, Tenant=own, Admin=all |
| GET/PUT | `/api/property/applications/<pk>/` | Landlord: approve/reject — Tenant: withdraw |
| GET | `/api/property/dashboard/` | Landlord / Admin |
| GET/POST | `/api/property/leases/<lease_id>/documents/` | Owner/Agent=POST, Tenant on lease=GET |
| POST | `/api/property/leases/<lease_id>/documents/<doc_id>/sign/` | Tenant on lease only |
| GET/POST | `/api/property/properties/<property_id>/reviews/` | GET=any auth, POST=Tenant (active/past lease) or Landlord (owns property) |
| GET/PATCH/DELETE | `/api/property/properties/<property_id>/reviews/<review_id>/` | Reviewer or Admin |
| GET/POST | `/api/property/properties/<property_id>/tenant-reviews/` | GET=Owner/Agent/Admin, POST=Landlord/Agent |
| GET/PATCH/DELETE | `/api/property/properties/<property_id>/tenant-reviews/<review_id>/` | Reviewer or Admin |
| GET | `/api/property/units/public/` | Public (no auth); supports query-param filtering |
| GET/POST | `/api/property/saved-searches/` | Any auth — own only (Admin=all) |
| GET/PATCH/DELETE | `/api/property/saved-searches/<pk>/` | Owner or Admin |

### Billing (`/api/billing/`)
| Method | URL | Who |
|--------|-----|-----|
| GET/POST | `/api/billing/config/<property_id>/` | Owner/Admin |
| GET/POST | `/api/billing/invoices/` | GET: Admin=all, Landlord=own properties, Agent=assigned, Tenant=own — POST: Admin / property owner / assigned agent (requires billing config on property; body: `lease`, `period_start`, `period_end`, `due_date`, optional `rent_amount`) |
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

### Notifications (`/api/notifications/`)
| Method | URL | Who |
|--------|-----|-----|
| GET | `/api/notifications/` | Own notifications; `?unread=true` filter |
| POST | `/api/notifications/<pk>/read/` | Own notification only |
| POST | `/api/notifications/read-all/` | All own notifications |

### Messaging (`/api/messaging/`)
| Method | URL | Who |
|--------|-----|-----|
| GET/POST | `/api/messaging/conversations/` | Participants only |
| GET | `/api/messaging/conversations/<pk>/` | Participants only |
| GET/POST | `/api/messaging/conversations/<pk>/messages/` | Participants only |
| POST | `/api/messaging/conversations/<pk>/read/` | Participants only |

### Disputes (`/api/disputes/`)
| Method | URL | Who |
|--------|-----|-----|
| GET | `/api/disputes/` | Admin=all, Landlord=own properties, Agent=assigned, Tenant=own |
| POST | `/api/disputes/` | Tenant (active lease) or Landlord (owns property) |
| GET | `/api/disputes/<pk>/` | Participants (creator, owner, assigned agent) or Admin |
| PATCH | `/api/disputes/<pk>/` | Status transitions (see below) |
| GET/POST | `/api/disputes/<pk>/messages/` | Any dispute participant |

**Dispute status machine:**
```
open → under_review   (property owner or admin)
under_review → resolved  (admin only)
open/under_review → closed  (dispute creator only)
```

### Moving (`/api/moving/`)
| Method | URL | Who |
|--------|-----|-----|
| GET | `/api/moving/companies/` | Any auth — active companies only |
| GET | `/api/moving/companies/<pk>/` | Any auth |
| GET/POST | `/api/moving/bookings/` | Any auth — scoped: company sees own bookings, others see theirs |
| GET/PUT | `/api/moving/bookings/<pk>/` | Customer or company that owns the booking |
| GET/POST | `/api/moving/companies/<pk>/reviews/` | Any auth |
| GET/PATCH/DELETE | `/api/moving/companies/<pk>/reviews/<review_id>/` | Reviewer or Admin |

**Moving booking status machine:**
```
pending → confirmed / cancelled  (company)
confirmed → in_progress          (company)
confirmed → cancelled            (customer or company)
in_progress → completed          (company)
pending → cancelled              (customer)
```

### Neighborhood Insights (`/api/neighborhood/`)
| Method | URL | Who |
|--------|-----|-----|
| GET | `/api/neighborhood/properties/<id>/insights/` | Any auth; `?type=` filter |
| POST | `/api/neighborhood/properties/<id>/insights/` | Property owner, assigned agent, Admin |
| GET | `/api/neighborhood/properties/<id>/insights/<pk>/` | Any auth |
| PATCH/DELETE | `/api/neighborhood/properties/<id>/insights/<pk>/` | Adder or Admin |

Insight type choices: `school`, `hospital`, `safety`, `transit`, `restaurant`, `other`

### Dashboards (`/api/dashboard/`)
| Method | URL | Who |
|--------|-----|-----|
| GET | `/api/dashboard/admin/` | Admin — system overview (users, properties, billing, maintenance, disputes, moving) |
| GET | `/api/dashboard/admin/users/` | Admin — all users; `?role=`, `?search=`, `?is_active=` |
| GET/PUT | `/api/dashboard/admin/users/<pk>/` | Admin — user detail + role history / change role or active status |
| GET | `/api/dashboard/admin/moderation/reviews/` | Admin — all reviews; `?type=property\|tenant` |
| DELETE | `/api/dashboard/admin/moderation/reviews/<pk>/` | Admin — delete any review; `?type=property\|tenant` required |
| GET | `/api/dashboard/tenant/` | Tenant — active lease, invoice summary, open maintenance, unread notifications |
| GET | `/api/dashboard/artisan/` | Artisan — open jobs matching trade, active bids, completed this month |
| GET | `/api/dashboard/agent/` | Agent — assigned properties + occupancy, pending applications, open maintenance, active disputes |
| GET | `/api/dashboard/moving-company/` | MovingCompany — bookings by status, avg rating, recent reviews |

### Monitoring (`/api/monitoring/`) — Admin only
| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/monitoring/metrics/` | List recorded metrics; `?metric_type=&hours=24` |
| GET/POST | `/api/monitoring/alert-rules/` | List / create alert rules |
| GET/PATCH/DELETE | `/api/monitoring/alert-rules/<pk>/` | Rule detail |
| GET | `/api/monitoring/alerts/` | List alert instances; `?status=&severity=&hours=72` |
| GET/PATCH | `/api/monitoring/alerts/<pk>/` | Alert detail / acknowledge / resolve |
| GET | `/api/monitoring/dashboard/` | Health status, active alert counts, latest metrics, 24h trends |

**Alert instance status machine:**
```
triggered → acknowledged  (admin)
triggered → resolved      (admin)
acknowledged → resolved   (admin)
resolved → (terminal)
```
Auto-resolved by `check_alert_rules` when metric returns to normal range.

**Metric types:** `overdue_invoice_count`, `monthly_revenue`, `occupancy_rate`, `open_maintenance_count`, `open_dispute_count`, `pending_application_count`, `payment_success_rate`

**Seeded alert rules:** high overdue invoices (warning ≥10, critical ≥50), low occupancy (warning ≤70%), high open maintenance (warning ≥20), high open disputes (warning ≥5), low payment success rate (critical ≤80%)

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
- Role name checks must use the constants on `Role`: `Role.ADMIN`, `Role.LANDLORD`, `Role.AGENT`, `Role.TENANT`, `Role.ARTISAN` — never hardcode strings
- Agents can read and write but never delete — delete is owner/admin only
- Maintenance: submitter (tenant or landlord) owns accept/reject bids and marks completion; artisan owns in_progress transition

### Python 3.14 + Django 4.2 gotcha
Any uncaught exception (IntegrityError, etc.) that propagates out of a view during tests will crash the test runner via Django's error logging template (`super().__copy__()` incompatibility in `django.template.context.BaseContext`). Always wrap `serializer.save()` in `try/except IntegrityError` when unique constraints could be violated and return HTTP 400 instead of letting the error propagate.

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
- Use `Role.objects.get_or_create(name=role_name)` not `Role.objects.create(name=role_name)` — roles are seeded by data migration 0004 and unique constraint will fail on create
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

### Notifications
- `create_notification(user, type, title, body, action_url='')` lives in `notifications/utils.py` — import from there in any app that needs to trigger a notification
- Always use a lazy import inside the view function: `from notifications.utils import create_notification` — avoids circular imports
- Notification types: `message`, `maintenance`, `payment`, `lease`, `dispute`, `application`, `new_listing`, `moving`, `account`
- Wired events: dispute created → owner; dispute status change → creator; dispute message → all participants except sender; conversation created → all participants except creator; message sent → all participants except sender; tenant review → reviewed tenant; moving booking created → company; booking status change → customer; role change → affected user
- `_maybe_send_email()` in `notifications/utils.py` checks `NotificationPreference` before sending email with `fail_silently=True`

### Messaging
- Conversations are identified by `property` + `subject` — no deduplication enforced, clients should check before creating
- `last_read_at` on `ConversationParticipant` is updated via `POST /api/messaging/conversations/<pk>/read/`
- `unread_count` on `ConversationSerializer` is computed dynamically: messages after `last_read_at`

### Disputes
- `dispute_type` choices: `rent`, `maintenance`, `noise`, `damage`, `lease`, `other`
- `status` choices: `open`, `under_review`, `resolved`, `closed`
- Artisans cannot view or create disputes
- Status transitions are enforced in `_validate_status_transition()` in `disputes/views.py`

### Lease Documents
- `file_url` is a plain `CharField(500)` — document storage is external; the API stores URLs, not files
- Signing sets `signed_by` (FK to user) and `signed_at` (timestamp) — no cryptographic signing
- Only the tenant on the lease can sign; only the owner/agent can upload

### Search & Saved Searches
- `GET /api/property/units/public/` supports query params: `price_min`, `price_max`, `bedrooms`, `bathrooms`, `property_type`, `amenities` (keyword), `parking=true`, `lat`+`lng`+`radius_km` (bounding-box distance filter)
- `SavedSearch.filters` is a free-form JSONField using the same keys as the query params above
- When a unit's `is_public` changes `False → True` via `PUT /api/property/units/<pk>/`, `notify_saved_search_matches(unit)` is called inline — this fires `new_listing` notifications to all matching saved searches
- `match_saved_searches` management command re-runs matching for recently published units (use `--days N` to control lookback window); intended for catch-up after downtime
- `Unit.tour_url` stores an external 3D/virtual tour URL — optional, plain CharField(500)
- `TenantApplication.documents` is a JSONField list of uploaded document URLs (ID, payslips, references)

### Reviews
- `PropertyReview`: one review per reviewer per property (`unique_together`); reviewer must have a lease (tenant) or own the property (landlord)
- `TenantReview`: one review per reviewer+tenant+property combination; reviewer must be landlord or agent on the property
- `reviewer_name` and `tenant_name` are computed fields (first+last name, falls back to username) — no raw PII fields exposed

### Dashboards
- All dashboard views are in `dashboard/` — they import cross-app models lazily inside view functions to avoid circular imports (same pattern as `property/views.py` landlord dashboard)
- All dashboard endpoints are computed on the fly — no stored snapshot models
- Admin overview excludes `is_staff=True` users from role counts (admins aren't in `by_role`)
- Admin user management `PUT /api/dashboard/admin/users/<pk>/` updates the role FK directly — no profile migration; logs to `RoleChangeLog` only when the role actually changes (old_role ≠ new_role)
- `RoleChangeLog` lives in `dashboard/models.py`; fields: user, changed_by, old_role, new_role, changed_at, reason (optional text)
- Content moderation DELETE requires `?type=property|tenant` query param to resolve which review model to delete from
- Role-specific dashboards enforce access at the top of the view (403 if wrong role) — no shared permission helper

### Monitoring
- `record_metrics` must run on a cron schedule (e.g. every 15 min) to populate `SystemMetric` — without data, alert rules have nothing to evaluate
- `check_alert_rules` should run after each `record_metrics` run — it reads the latest metric per type, evaluates all enabled rules, and creates/auto-resolves `AlertInstance` records
- Alerts auto-resolve when the metric returns to the normal range — no manual action required for transient spikes
- Admin users are notified via `create_notification` when an alert fires; delivery respects their `NotificationPreference`
- All monitoring endpoints are admin-only (`is_staff=True`); non-admin users get 403
- New metric types require adding to `METRIC_TYPES` in `monitoring/models.py` and updating `record_metrics` command logic

### General
- Read a file before editing it
- Don't add new Django apps without confirming with the user first
- Keep `authentication/` concerns separate from other apps — no cross-app model imports
- Don't add error handling for impossible cases — only validate at system boundaries
