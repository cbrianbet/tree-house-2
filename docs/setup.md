# Setup Guide

Step-by-step instructions for getting Tree House running locally.

---

## Prerequisites

- Python 3.14
- A PostgreSQL database (Supabase free tier works; see below)
- A Stripe account (optional for local dev — placeholder keys are fine)

---

## 1. Clone and create a virtual environment

```bash
git clone https://github.com/cbrianbet/tree-house-2.git
cd tree-house-2
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

---

## 2. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** `psycopg2-binary` is used in this project. Running `python manage.py makemigrations` will fail because psycopg2 cannot build from source in this venv. **Always write migrations by hand.** See [CONTRIBUTING.md](../CONTRIBUTING.md#migrations).

---

## 3. Configure environment variables

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

Open `.env` and set each variable:

```env
# Database — see Supabase setup below
DB_NAME=postgres
DB_USER=postgres.<your-project-ref>
DB_PASSWORD=<your-db-password>
DB_HOST=aws-1-eu-west-1.pooler.supabase.com
DB_PORT=5432

# Django
SECRET_KEY=<generate-a-long-random-string>

# Email (redirect URLs for email verification and password reset flows)
EMAIL_CONFIRM_REDIRECT_BASE_URL=http://localhost:8000/email-confirm/
PASSWORD_RESET_CONFIRM_REDIRECT_BASE_URL=http://localhost:8000/password-reset-confirm/
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# Stripe (use placeholders for local dev — real keys needed for payment testing)
STRIPE_SECRET_KEY=sk_test_placeholder
STRIPE_WEBHOOK_SECRET=whsec_placeholder
```

---

## 4. Supabase database setup

1. Go to [supabase.com](https://supabase.com) and create a free project.
2. Under **Project Settings → Database**, find the **Connection string** section.
3. Select **Transaction pooler** mode and copy the host, user, and password.
4. Fill those values into your `.env` file as shown above.

> **Free tier note:** Supabase pauses inactive projects after 1 week. If you get a connection error, log in to Supabase and resume the project.

---

## 5. Run migrations

```bash
python manage.py migrate
```

This applies all migrations including the data migrations that seed roles (Admin, Landlord, Agent, Tenant, Artisan, MovingCompany).

---

## 6. Start the server

```bash
python manage.py runserver
```

The API runs at `http://localhost:8000`.

| URL | Description |
|-----|-------------|
| `http://localhost:8000/api/docs/` | Swagger UI |
| `http://localhost:8000/api/redoc/` | ReDoc |
| `http://localhost:8000/api/schema/` | OpenAPI schema download |

If port 8000 is already in use:

```bash
lsof -ti:8000 | xargs kill -9
# or use an alternate port:
python manage.py runserver 8001
```

---

## 7. Create your first admin user

```bash
python manage.py shell
```

```python
from authentication.models import CustomUser, Role
role, _ = Role.objects.get_or_create(name='Admin')
user = CustomUser.objects.create_superuser(
    username='admin',
    email='admin@example.com',
    password='yourpassword',
    role=role,
)
```

---

## 8. Register via the API

```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "jane",
    "email": "jane@example.com",
    "password1": "strongpass123",
    "password2": "strongpass123",
    "first_name": "Jane",
    "last_name": "Doe",
    "role": 2
  }'
```

Fetch the role ID list first from `GET /api/auth/roles/`.

---

## Running tests

Each app has its own test suite:

```bash
python manage.py test authentication --keepdb
python manage.py test property --keepdb
python manage.py test billing --keepdb
# etc.
```

`--keepdb` reuses the test database between runs (faster). Drop it on a fresh run if you need a clean slate.

> Tests connect to a real PostgreSQL database. Make sure your `.env` database credentials are valid before running tests.

---

## Management commands

These run periodically in production via cron. You can trigger them manually during development:

```bash
# Generate invoices, apply late fees, send payment reminders
python manage.py process_billing

# Match recently published units against saved searches
python manage.py match_saved_searches
python manage.py match_saved_searches --days 7   # look back 7 days

# Snapshot current platform metrics to the database
python manage.py record_metrics

# Evaluate alert rules; fire or auto-resolve AlertInstances
python manage.py check_alert_rules
```

---

## Stripe webhook (local testing)

To test the full payment flow locally, forward Stripe events to your local server using the Stripe CLI:

```bash
stripe listen --forward-to localhost:8000/api/billing/stripe/webhook/
```

Copy the webhook signing secret printed by the CLI into your `.env`:

```env
STRIPE_WEBHOOK_SECRET=whsec_<from-stripe-cli>
```

---

## Common issues

| Problem | Fix |
|---------|-----|
| `OperationalError: could not connect to server` | Supabase project is paused — log in and resume it |
| `Port 8000 already in use` | Run `lsof -ti:8000 \| xargs kill -9` or use port 8001 |
| `makemigrations` fails | Expected — write migrations by hand. See [CONTRIBUTING.md](../CONTRIBUTING.md#migrations) |
| Test runner hangs asking to delete test DB | Use `--noinput` flag or type `yes` |
| `django.template.context.BaseContext` error in tests | An unhandled exception propagated out of a view — wrap `serializer.save()` in `try/except IntegrityError` |
