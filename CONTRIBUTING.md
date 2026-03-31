# Contributing to Tree House

---

## Before you start

- Read [CLAUDE.md](CLAUDE.md) — it is the authoritative reference for all coding conventions, business logic, and API design decisions.
- Read [docs/setup.md](docs/setup.md) to get the project running locally.
- Check [docs/backlog.md](docs/backlog.md) for known issues and planned work before opening a new issue.

---

## Workflow

1. Branch off `main` — use a descriptive name: `42-lease-renewal-workflow`
2. Open a PR against `main` when ready
3. CI must pass (all tests green) before merging
4. At least one review required for anything touching `billing/`, `authentication/`, or `monitoring/`

---

## Views

- Always use **function-based views** with `@api_view` and `@permission_classes([IsAuthenticated])`. Never use class-based views unless a third-party library requires it.
- `PUT` endpoints always use `partial=True` on the serializer — callers only send the fields they want to change.
- Shared view logic goes in factory functions — see `_profile_list_view` / `_profile_detail_view` in `authentication/views.py`.
- Always add `@extend_schema` with at least one `OpenApiExample` when writing a new view. Request body examples are required.

```python
@extend_schema(
    methods=['POST'],
    summary="Create a lease document",
    examples=[
        OpenApiExample('Upload document', value={'type': 'lease', 'file_url': 'https://...'})
    ],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def my_view(request):
    ...
```

---

## Models

- New domain entities that are role-specific get their own profile table as a `OneToOneField` to `CustomUser`.
- Many-to-many relationships with extra data use an explicit through model — see `PropertyAgent`.
- Always define `__str__` on every model.
- List queries on related models use `select_related` to avoid N+1 queries.

---

## Permissions

- Permission helpers live at the top of each app's `views.py`: `is_landlord`, `is_admin`, `is_agent_for`, `is_artisan`.
- Role name checks must use the constants on `Role`: `Role.ADMIN`, `Role.LANDLORD`, `Role.AGENT`, `Role.TENANT`, `Role.ARTISAN`. **Never hardcode strings.**
- Agents can read and write but never delete — delete is owner/admin only.

---

## Serializers

- Use `ModelSerializer` for all models.
- Always explicitly list `fields` — **never** use `fields = '__all__'`.

```python
class MySerializer(serializers.ModelSerializer):
    class Meta:
        model = MyModel
        fields = ['id', 'name', 'created_at']  # explicit list required
```

---

## Migrations

> **`python manage.py makemigrations` cannot run in this project.** psycopg2 will not build from source in this venv. All migrations must be written by hand.

Rules:
- Schema migration and data migration always go in **separate files**.
- Seed/reference data goes in a data migration, not fixtures.
- Data migrations always use `get_or_create` so they are safe to re-run.
- Name migrations descriptively: `0003_add_profile_models`, `0004_seed_roles`.

Example schema migration:

```python
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('myapp', '0002_previous')]

    operations = [
        migrations.AddField(
            model_name='mymodel',
            name='new_field',
            field=models.CharField(max_length=100, blank=True),
        ),
    ]
```

Example data migration:

```python
from django.db import migrations

def seed_data(apps, schema_editor):
    MyModel = apps.get_model('myapp', 'MyModel')
    MyModel.objects.get_or_create(name='default', defaults={'value': 42})

class Migration(migrations.Migration):
    dependencies = [('myapp', '0003_add_field')]
    operations = [migrations.RunPython(seed_data, reverse_code=migrations.RunPython.noop)]
```

---

## Tests

Every new endpoint needs tests covering: list, create, retrieve, update, delete, and 404.  
**Permission boundary tests are required** — test that the wrong role gets 403, not just that the right role succeeds.

```python
class MyFeatureTestCase(TestCase):
    def setUp(self):
        # Use get_or_create for roles — they are seeded by migration and unique
        role, _ = Role.objects.get_or_create(name=Role.TENANT)
        self.user = CustomUser.objects.create_user(
            username='test', role=role, email='test@ex.com'
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def test_wrong_role_gets_403(self):
        # Always test the boundary, not just the happy path
        response = self.client.get('/api/some-admin-endpoint/')
        self.assertEqual(response.status_code, 403)
```

Use the `make_user(username, role_name)` helper pattern from `property/tests.py` to reduce `setUp` boilerplate.

---

## Error handling

- Wrap `serializer.save()` in `try/except IntegrityError` when unique constraints could be violated — return HTTP 400 instead of letting the exception propagate.
- Do not add error handling for impossible cases — only validate at system boundaries.

```python
from django.db import IntegrityError

try:
    serializer.save(user=request.user)
except IntegrityError:
    return Response({'detail': 'Already exists.'}, status=status.HTTP_400_BAD_REQUEST)
```

> **Python 3.14 + Django 4.2 gotcha:** Any uncaught exception that propagates out of a view during tests will crash the test runner via a `super().__copy__()` incompatibility in `django.template.context.BaseContext`. Always catch `IntegrityError` before it reaches the view layer.

---

## Notifications

Import `create_notification` lazily inside the view function to avoid circular imports:

```python
def my_view(request):
    from notifications.utils import create_notification
    create_notification(
        user=tenant,
        notification_type='payment',
        title='Payment received',
        body='Your rent of KES 50,000 was received.',
        action_url='/invoices/42/',
    )
```

Valid `notification_type` values: `message`, `maintenance`, `payment`, `lease`, `dispute`, `application`, `new_listing`, `moving`, `account`.

---

## Cross-app imports

Use lazy imports inside view functions (not at module level) when importing models from other apps. This matches the pattern used in `property/views.py` and `dashboard/views.py` and prevents circular import errors.

```python
# Good — lazy import inside the function
def my_view(request):
    from billing.models import Invoice
    invoices = Invoice.objects.filter(...)

# Bad — module-level cross-app import
from billing.models import Invoice  # can cause circular imports
```

---

## New apps

Do not create a new Django app without first confirming with the team. Apps should map to a cohesive domain — not a single model or endpoint.

When a new app is approved:
1. Add it to `INSTALLED_APPS` in `treeHouse/settings.py`
2. Add its URL include to `treeHouse/urls.py`
3. Write `0001_initial.py` migration by hand
4. Add test commands to `CLAUDE.md` and `README.md`
5. Document it in `docs/api-integration.md`
