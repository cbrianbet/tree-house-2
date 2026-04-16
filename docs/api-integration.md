# Tree House API — Frontend Integration Guide

Base URL: `http://localhost:8000` (dev) / `https://<your-domain>` (prod)
All protected endpoints require: `Authorization: Token <token>`
Content-Type: `application/json`

---

## Role Permissions Matrix

`✓` = allowed   `✗` = forbidden (403)   `—` = not applicable to this role


| Action                                      | Public | Admin       | Landlord     | Agent       | Tenant            | Artisan            | MovingCompany |
| ------------------------------------------- | ------ | ----------- | ------------ | ----------- | ----------------- | ------------------ | ------------- |
| **— ACCOUNT —**                             |        |             |              |             |                   |                    |               |
| Register / Login / Logout                   | ✓      | ✓           | ✓            | ✓           | ✓                 | ✓                  | ✓             |
| Accept tenant invitation (no auth)          | ✓      | ✓           | ✓            | ✓           | ✓                 | ✓                  | ✓             |
| View & update own account                   | ✗      | ✓           | ✓            | ✓           | ✓                 | ✓                  | ✓             |
| View & update own role profile              | ✗      | ✗           | ✓            | ✓           | ✓                 | ✓                  | ✓             |
| Change password                             | ✗      | ✓           | ✓            | ✓           | ✓                 | ✓                  | ✓             |
| Manage notification preferences             | ✗      | ✓           | ✓            | ✓           | ✓                 | ✓                  | ✓             |
| **— PROPERTIES —**                          |        |             |              |             |                   |                    |               |
| Browse & filter public units                | ✓      | ✓           | ✓            | ✓           | ✓                 | ✓                  | ✓             |
| Create / manage saved searches              | ✗      | ✓           | ✓            | ✓           | ✓                 | ✓                  | ✓             |
| List properties                             | ✗      | All         | Own          | Assigned    | ✗                 | ✗                  | ✗             |
| Create property                             | ✗      | ✓           | ✓            | ✗           | ✗                 | ✗                  | ✗             |
| View / update property                      | ✗      | ✓           | Own          | Assigned    | ✗                 | ✗                  | ✗             |
| Delete property                             | ✗      | ✓           | Own          | ✗           | ✗                 | ✗                  | ✗             |
| List units on property                      | ✗      | ✓           | ✓            | ✓           | ✓                 | ✓                  | ✓             |
| Create / update unit                        | ✗      | ✓           | Own          | Assigned    | ✗                 | ✗                  | ✗             |
| Delete unit                                 | ✗      | ✓           | Own          | ✗           | ✗                 | ✗                  | ✗             |
| Upload unit images                          | ✗      | ✓           | Own          | Assigned    | ✗                 | ✗                  | ✗             |
| Delete unit images                          | ✗      | ✓           | Own          | Assigned    | ✗                 | ✗                  | ✗             |
| Appoint / remove agent                      | ✗      | ✓           | Own          | ✗           | ✗                 | ✗                  | ✗             |
| Portfolio dashboard                         | ✗      | All         | Own          | ✗           | ✗                 | ✗                  | ✗             |
| **— APPLICATIONS —**                        |        |             |              |             |                   |                    |               |
| Submit application                          | ✗      | ✗           | ✗            | ✗           | ✓                 | ✗                  | ✗             |
| List applications                           | ✗      | All         | Own units    | ✗           | Own               | ✗                  | ✗             |
| Approve / reject application                | ✗      | ✓           | Own units    | ✗           | ✗                 | ✗                  | ✗             |
| Withdraw application                        | ✗      | ✗           | ✗            | ✗           | Own               | ✗                  | ✗             |
| List / create tenant invitations (per unit) | ✗      | All         | Own units    | Assigned    | ✗                 | ✗                  | ✗             |
| Resend tenant invitation                    | ✗      | All         | Own units    | Assigned    | ✗                 | ✗                  | ✗             |
| **— LEASES & DOCUMENTS —**                  |        |             |              |             |                   |                    |               |
| View / create lease                         | ✗      | ✓           | Own          | Assigned    | ✗                 | ✗                  | ✗             |
| List / upload lease documents               | ✗      | ✓           | Own          | Assigned    | On lease          | ✗                  | ✗             |
| Delete lease documents                      | ✗      | ✓           | Own          | Assigned    | ✗                 | ✗                  | ✗             |
| Sign lease document                         | ✗      | ✗           | ✗            | ✗           | On lease          | ✗                  | ✗             |
| **— BILLING —**                             |        |             |              |             |                   |                    |               |
| View billing config & billing preview       | ✗      | ✓           | Own          | Assigned    | ✗                 | ✗                  | ✗             |
| Create / update billing config              | ✗      | ✓           | Own          | ✗           | ✗                 | ✗                  | ✗             |
| List / view invoices                        | ✗      | All         | Own          | Assigned    | Own               | ✗                  | ✗             |
| Create invoice (manual)                     | ✗      | ✓           | Own          | Assigned    | ✗                 | ✗                  | ✗             |
| Record manual invoice payment               | ✗      | ✓           | Own          | Assigned    | ✗                 | ✗                  | ✗             |
| Pay invoice (Stripe)                        | ✗      | ✗           | ✗            | ✗           | Own               | ✗                  | ✗             |
| View payments & receipts                    | ✗      | All         | Own          | Assigned    | Own               | ✗                  | ✗             |
| Manage charge types                         | ✗      | ✓           | Own          | View only   | ✗                 | ✗                  | ✗             |
| Record additional income                    | ✗      | ✓           | Own          | View only   | ✗                 | ✗                  | ✗             |
| Record / view expenses                      | ✗      | ✓           | Own          | View only   | ✗                 | ✗                  | ✗             |
| Financial reports                           | ✗      | ✓           | Own          | Assigned    | ✗                 | ✗                  | ✗             |
| **— MAINTENANCE —**                         |        |             |              |             |                   |                    |               |
| List requests                               | ✗      | All         | Own          | Assigned    | Own               | Open (trade match) | ✗             |
| Submit request                              | ✗      | ✓           | Own          | ✗           | ✓                 | ✗                  | ✗             |
| View request detail                         | ✗      | ✓           | Own          | Assigned    | Own               | Assigned           | ✗             |
| Open for bidding                            | ✗      | ✓           | Own          | ✗           | ✗                 | ✗                  | ✗             |
| Cancel request                              | ✗      | ✗           | If submitter | ✗           | If submitter      | ✗                  | ✗             |
| Reject request                              | ✗      | ✓           | Own          | ✗           | ✗                 | ✗                  | ✗             |
| Place bid                                   | ✗      | ✗           | ✗            | ✗           | ✗                 | ✓                  | ✗             |
| Accept / reject bid                         | ✗      | ✗           | If submitter | ✗           | If submitter      | ✗                  | ✗             |
| Mark in progress                            | ✗      | ✗           | ✗            | ✗           | ✗                 | Assigned           | ✗             |
| Mark completed                              | ✗      | ✗           | If submitter | ✗           | If submitter      | ✗                  | ✗             |
| Add notes / images                          | ✗      | ✓           | If can view  | If can view | If can view       | If can view        | ✗             |
| **— NOTIFICATIONS —**                       |        |             |              |             |                   |                    |               |
| View & manage own notifications             | ✗      | ✓           | ✓            | ✓           | ✓                 | ✓                  | ✓             |
| **— MESSAGING —**                           |        |             |              |             |                   |                    |               |
| Start conversation                          | ✗      | ✓           | ✓            | ✓           | ✓                 | ✓                  | ✓             |
| View / reply in conversation                | ✗      | Participant | Participant  | Participant | Participant       | Participant        | Participant   |
| **— DISPUTES —**                            |        |             |              |             |                   |                    |               |
| List disputes                               | ✗      | All         | Own          | Assigned    | Own               | ✗                  | ✗             |
| Submit dispute                              | ✗      | ✓           | Own          | ✗           | Active lease      | ✗                  | ✗             |
| View dispute detail                         | ✗      | ✓           | Own          | Assigned    | Own               | ✗                  | ✗             |
| Move to under review                        | ✗      | ✓           | Own          | ✗           | ✗                 | ✗                  | ✗             |
| Resolve dispute                             | ✗      | ✓           | ✗            | ✗           | ✗                 | ✗                  | ✗             |
| Close dispute                               | ✗      | ✗           | If creator   | ✗           | If creator        | ✗                  | ✗             |
| Post dispute message                        | ✗      | ✓           | Participant  | Participant | Participant       | ✗                  | ✗             |
| **— REVIEWS —**                             |        |             |              |             |                   |                    |               |
| View property reviews                       | ✗      | ✓           | ✓            | ✓           | ✓                 | ✓                  | ✓             |
| Write property review                       | ✗      | ✓           | Own property | ✗           | Active/past lease | ✗                  | ✗             |
| Edit / delete property review               | ✗      | ✓           | Own review   | ✗           | Own review        | ✗                  | ✗             |
| View tenant reviews                         | ✗      | ✓           | Own          | Assigned    | ✗                 | ✗                  | ✗             |
| Write tenant review                         | ✗      | ✗           | Own          | Assigned    | ✗                 | ✗                  | ✗             |
| Edit / delete tenant review                 | ✗      | ✓           | Own review   | Own review  | ✗                 | ✗                  | ✗             |
| **— MOVING —**                              |        |             |              |             |                   |                    |               |
| Browse moving companies                     | ✗      | ✓           | ✓            | ✓           | ✓                 | ✓                  | ✓             |
| Create / cancel booking                     | ✗      | ✓           | ✓            | ✓           | ✓                 | ✗                  | ✗             |
| Confirm / complete booking                  | ✗      | ✓           | ✗            | ✗           | ✗                 | ✗                  | Own bookings  |
| Write / edit company review                 | ✗      | ✓           | ✓            | ✓           | ✓                 | ✗                  | ✗             |
| **— NEIGHBORHOOD INSIGHTS —**               |        |             |              |             |                   |                    |               |
| View insights for a property                | ✗      | ✓           | ✓            | ✓           | ✓                 | ✓                  | ✓             |
| Add insight to a property                   | ✗      | ✓           | Own          | Assigned    | ✗                 | ✗                  | ✗             |
| Edit / delete insight                       | ✗      | ✓           | If adder     | If adder    | ✗                 | ✗                  | ✗             |
| **— DASHBOARDS —**                          |        |             |              |             |                   |                    |               |
| Admin system overview                       | ✗      | ✓           | ✗            | ✗           | ✗                 | ✗                  | ✗             |
| Admin user management                       | ✗      | ✓           | ✗            | ✗           | ✗                 | ✗                  | ✗             |
| Admin content moderation                    | ✗      | ✓           | ✗            | ✗           | ✗                 | ✗                  | ✗             |
| Tenant dashboard                            | ✗      | ✗           | ✗            | ✗           | ✓                 | ✗                  | ✗             |
| Artisan dashboard                           | ✗      | ✗           | ✗            | ✗           | ✗                 | ✓                  | ✗             |
| Agent dashboard                             | ✗      | ✗           | ✗            | ✓           | ✗                 | ✗                  | ✗             |
| Moving company dashboard                    | ✗      | ✗           | ✗            | ✗           | ✗                 | ✗                  | ✓             |
| **— MONITORING —**                          |        |             |              |             |                   |                    |               |
| View system metrics                         | ✗      | ✓           | ✗            | ✗           | ✗                 | ✗                  | ✗             |
| Manage alert rules                          | ✗      | ✓           | ✗            | ✗           | ✗                 | ✗                  | ✗             |
| View / acknowledge / resolve alerts         | ✗      | ✓           | ✗            | ✗           | ✗                 | ✗                  | ✗             |
| Monitoring dashboard                        | ✗      | ✓           | ✗            | ✗           | ✗                 | ✗                  | ✗             |
| Impersonate any non-admin user              | ✗      | ✓           | ✗            | ✗           | ✗                 | ✗                  | ✗             |
| View impersonation logs                     | ✗      | ✓           | ✗            | ✗           | ✗                 | ✗                  | ✗             |


---

## Authentication

### Register

`POST /api/auth/register/`

```json
// Request
{
  "username": "jane",
  "email": "jane@example.com",
  "password1": "strongpass123",
  "password2": "strongpass123",
  "first_name": "Jane",
  "last_name": "Doe",
  "phone": "+254712345678",
  "role": 2
}

// Response 201
{
  "key": "abc123tokenhere"
}
```

`role` is the role ID (integer). Fetch available roles from `GET /api/auth/roles/`.

---

### Login

`POST /api/auth/login/`

```json
// Request
{
  "username": "jane",
  "password": "strongpass123"
}

// Response 200
{
  "key": "abc123tokenhere"
}
```

Store the token and include it on every subsequent request:

```
Authorization: Token abc123tokenhere
```

---

### Accept tenant invitation

`POST /api/auth/tenant-invite/accept/` — **no** `Authorization` header. Use the `token` value from the invite email (query string on the frontend URL is for UX only; the API expects `token` in the JSON body).

```json
// Request
{
  "token": "<url-safe-token-from-email>",
  "password": "strongpass123",
  "first_name": "Jane",
  "last_name": "Doe",
  "phone": "+254712345678",
  "national_id": "",
  "emergency_contact_name": "",
  "emergency_contact_phone": ""
}

// Response 201
{
  "key": "abc123tokenhere",
  "user": { "pk": 1, "username": "jane@example.com", "email": "jane@example.com", "role": 2, "...": "..." }
}
```

---

### Logout

`POST /api/auth/logout/`
No body required. Returns `200 {}`.

---

### Current User

`GET /api/auth/user/`

```json
// Response 200
{
  "pk": 1,
  "username": "jane",
  "email": "jane@example.com",
  "first_name": "Jane",
  "last_name": "Doe",
  "phone": "+254712345678",
  "role": 2,
  "is_staff": false
}
```

`role` is the role ID (integer). Use `GET /api/auth/roles/<pk>/` to resolve the name if needed.

---

### Change Password (authenticated)

`POST /api/auth/password/change/`

```json
{
  "old_password": "currentpass",
  "new_password1": "newpass123",
  "new_password2": "newpass123"
}
```

Returns `200 {}` on success.

---

### Password Reset

`POST /api/auth/password/reset/`

```json
{ "email": "jane@example.com" }
```

`POST /api/auth/password/reset/confirm/`

```json
{
  "uid": "<uid from email link>",
  "token": "<token from email link>",
  "new_password1": "newpass123",
  "new_password2": "newpass123"
}
```

---

## Account Self-Service

### Get / Update Your Account

`GET /api/auth/me/`
`PATCH /api/auth/me/` — send only the fields you want to change

```json
// PATCH request
{ "first_name": "Jane", "phone": "+254712345678" }

// Response 200
{
  "id": 5,
  "username": "jane",
  "email": "jane@example.com",
  "first_name": "Jane",
  "last_name": "Doe",
  "phone": "+254712345678",
  "role": 2
}
```

`role` is read-only.

---

### Lightweight User Profile Lookup (authenticated)

`GET /api/auth/users/<pk>/profile/`

Useful for non-admin UI surfaces that need to resolve a user's display name/phone without calling admin-only dashboard endpoints.

```json
// Response 200
{
  "id": 5,
  "first_name": "Jane",
  "last_name": "Doe",
  "phone": "+254712345678",
  "role": "Tenant"
}
```

Returns `404` when the user does not exist.

---

### Get / Update Your Role Profile

`GET /api/auth/me/profile/`
`PATCH /api/auth/me/profile/` — send only the fields you want to change

Profile fields vary by role. Admin has no profile — returns `404`.

**Tenant:**

```json
{ "national_id": "32145678", "emergency_contact_name": "John", "emergency_contact_phone": "+254700000000" }
```

**Landlord:**

```json
{ "company_name": "Bett Properties Ltd", "tax_id": "A001234567B" }
```

**Agent:**

```json
{ "agency_name": "Prime Realtors", "license_number": "RE-2024-001", "commission_rate": "5.00" }
```

**Artisan:**

```json
{ "trade": "plumbing", "bio": "10 years experience." }
```

**MovingCompany:**

```json
{
  "company_name": "Swift Movers Ltd",
  "description": "Professional moving services across the city",
  "phone": "+254712345678",
  "address": "123 Mover Street",
  "city": "Nairobi",
  "service_areas": ["Nairobi", "Mombasa", "Kisumu"],
  "base_price": "5000.00",
  "price_per_km": "50.00"
}
```

`is_verified` and `is_active` are managed by admin.

Profile is auto-created on first `GET` if it doesn't exist yet.

---

### Notification Preferences

`GET /api/auth/me/notifications/`
`PATCH /api/auth/me/notifications/` — send only the flags you want to change

```json
// Response 200
{
  "email_notifications": true,
  "payment_due_reminder": true,
  "payment_received": true,
  "maintenance_updates": true,
  "new_maintenance_request": true,
  "new_application": true,
  "application_status_change": true,
  "lease_expiry_notice": true,
  "updated_at": "2024-03-01T08:00:00Z"
}
```

All flags default to `true`. Preferences are auto-created on first `GET`.

---

## Roles

### List Roles

`GET /api/auth/roles/`

```json
// Response 200
[
  { "id": 1, "name": "Admin", "description": "" },
  { "id": 2, "name": "Tenant", "description": "" },
  { "id": 3, "name": "Landlord", "description": "" },
  { "id": 4, "name": "Agent", "description": "" },
  { "id": 5, "name": "Artisan", "description": "" },
  { "id": 6, "name": "MovingCompany", "description": "Moving company registered to offer relocation services" }
]
```

---

## Role-Specific Profiles

After registration, users with non-Admin roles should create their profile.

### Tenant Profile

`POST /api/auth/profiles/tenant/`

```json
{
  "user": 5,
  "national_id": "32145678",
  "emergency_contact_name": "John Doe",
  "emergency_contact_phone": "+254700000000"
}
```

### Landlord Profile

`POST /api/auth/profiles/landlord/`

```json
{
  "user": 3,
  "company_name": "Bett Properties Ltd",
  "tax_id": "A001234567B"
}
```

`verified` is read-only (set by admin).

### Agent Profile

`POST /api/auth/profiles/agent/`

```json
{
  "user": 4,
  "agency_name": "Prime Realtors",
  "license_number": "RE-2024-001",
  "commission_rate": "5.00"
}
```

### Artisan Profile

`POST /api/auth/profiles/artisan/`

```json
{
  "user": 6,
  "trade": "plumbing",
  "bio": "10 years experience in residential plumbing."
}
```

Trade choices: `plumbing`, `electrical`, `carpentry`, `painting`, `masonry`, `other`
`rating` and `verified` are read-only (system-managed).

### Moving Company Profile

`POST /api/auth/profiles/moving-company/`

```json
{
  "user": 7,
  "company_name": "Swift Movers Ltd",
  "description": "Professional moving services across the city",
  "phone": "+254712345678",
  "address": "123 Mover Street",
  "city": "Nairobi",
  "service_areas": ["Nairobi", "Mombasa", "Kisumu"],
  "base_price": "5000.00",
  "price_per_km": "50.00"
}
```

`is_verified` is read-only (set by admin).

---

## Properties

### List Properties

`GET /api/property/properties/`
Response is scoped by role automatically:

- **Admin** → all properties
- **Landlord** → their own properties
- **Agent** → properties they are assigned to

```json
// Response 200
[
  {
    "id": 1,
    "name": "Sunset Apartments",
    "description": "12-unit apartment block in Westlands",
    "property_type": "apartment",
    "longitude": 36.8172,
    "latitude": -1.2921,
    "owner": 3,
    "created_at": "2024-01-15T08:00:00Z",
    "updated_at": "2024-01-15T08:00:00Z",
    "created_by": 3,
    "updated_by": null,
    "deleted_by": null
  }
]
```

### Create Property (Landlord only)

`POST /api/property/properties/`

```json
{
  "name": "Sunset Apartments",
  "description": "12-unit apartment block in Westlands",
  "property_type": "apartment",
  "longitude": 36.8172,
  "latitude": -1.2921
}
```

Property type choices: `house`, `apartment`, `commercial`, `land`, `bungalow`, `duplex`, `townhouse`, `studio`, `cottage`, `penthouse`, `other`

### Get / Update Property

`GET /api/property/properties/<pk>/`
`PUT /api/property/properties/<pk>/` — partial update, only send changed fields

### Delete Property (Admin / Owner only)

`DELETE /api/property/properties/<pk>/` → `204 No Content`

---

## Units

### List Units for a Property

`GET /api/property/properties/<pk>/units/`

### Create Unit (Admin / Owner / Agent)

`POST /api/property/properties/<pk>/units/`

```json
{
  "name": "A1",
  "floor": "Ground",
  "description": "Spacious 2-bed unit",
  "bedrooms": 2,
  "bathrooms": 1,
  "price": "25000.00",
  "service_charge": "2000.00",
  "security_deposit": "50000.00",
  "amenities": "WiFi, parking, gym",
  "parking_space": true,
  "parking_slots": 1,
  "is_public": true,
  "tour_url": "https://my3dtours.com/tour/unit-a1"
}
```

`is_occupied` defaults to `false` (set automatically when a lease is created).
`property` is set from the URL — do not include it in the body.
`tour_url` is optional — link to an external 3D/virtual tour.

> When a unit is updated and `is_public` changes from `false` to `true`, the system automatically checks all saved searches and sends `new_listing` notifications to matching users.

### Unit Detail / Update / Delete

`GET /api/property/units/<pk>/`
`PUT /api/property/units/<pk>/` — partial
`DELETE /api/property/units/<pk>/` — Admin / Owner only

---

## Search & Filtering

### Browse Public Units

`GET /api/property/units/public/` — no auth required

All query params are optional and can be combined:


| Param           | Type    | Description                                       |
| --------------- | ------- | ------------------------------------------------- |
| `price_min`     | number  | Minimum price (inclusive)                         |
| `price_max`     | number  | Maximum price (inclusive)                         |
| `bedrooms`      | integer | Minimum number of bedrooms                        |
| `bathrooms`     | integer | Minimum number of bathrooms                       |
| `property_type` | string  | Exact type — `apartment`, `house`, `studio`, etc. |
| `amenities`     | string  | Keyword search within amenities text              |
| `parking`       | `true`  | Only units with parking                           |
| `lat`           | float   | Latitude of search centre                         |
| `lng`           | float   | Longitude of search centre                        |
| `radius_km`     | float   | Search radius in km (requires `lat` + `lng`)      |


```
GET /api/property/units/public/?price_max=50000&bedrooms=2&property_type=apartment&lat=-1.2921&lng=36.8172&radius_km=5
```

---

## Saved Searches

Tenants can save filter criteria and receive `new_listing` notifications when a matching unit is published.

### List Saved Searches

`GET /api/property/saved-searches/`
Returns own searches. Admin sees all.

### Create a Saved Search

`POST /api/property/saved-searches/`

```json
{
  "name": "2-bed apartments under 50k in Westlands",
  "filters": {
    "price_max": 50000,
    "bedrooms": 2,
    "property_type": "apartment",
    "lat": -1.2921,
    "lng": 36.8172,
    "radius_km": 5
  },
  "notify_on_match": true
}
```

All `filters` keys are optional — use only the ones relevant to the search.

```json
// Response 201
{
  "id": 1,
  "name": "2-bed apartments under 50k in Westlands",
  "filters": { "price_max": 50000, "bedrooms": 2, "property_type": "apartment" },
  "notify_on_match": true,
  "created_at": "2024-03-10T09:00:00Z",
  "updated_at": "2024-03-10T09:00:00Z"
}
```

### Get / Update / Delete a Saved Search

`GET /api/property/saved-searches/<pk>/`
`PATCH /api/property/saved-searches/<pk>/` — send only changed fields
`DELETE /api/property/saved-searches/<pk>/` → `204 No Content`

Owner or admin only.

### Batch re-run matching (management command)

```bash
python manage.py match_saved_searches           # units published in last 24h
python manage.py match_saved_searches --days 7  # last 7 days
```

### Unit Lease

`GET /api/property/units/<pk>/lease/` — get active lease
`POST /api/property/units/<pk>/lease/` — create lease

```json
{
  "tenant": 5,
  "start_date": "2024-02-01",
  "end_date": "2025-01-31",
  "rent_amount": "25000.00",
  "is_active": true
}
```

`unit` is set from the URL — do not include it in the body.

---

## Agent Management

### Appoint Agent to Property (Owner / Admin)

`POST /api/property/properties/<pk>/agents/`

```json
{ "agent": 4 }
```

### List Agents on Property

`GET /api/property/properties/<pk>/agents/`

```json
[
  {
    "id": 1,
    "property": 1,
    "agent": 4,
    "appointed_by": 3,
    "appointed_at": "2024-01-20T10:00:00Z"
  }
]
```

### Remove Agent

`DELETE /api/property/properties/<pk>/agents/<id>/` → `204 No Content`

---

## Billing

### Configure Billing

`GET /api/billing/config/<property_id>/` — **read:** platform admin, property owner, or agent **assigned** to the property.

`POST /api/billing/config/<property_id>/` — **write:** platform admin or property owner only (agents get `403`).

#### GET when no config row exists (`200`)

The API does **not** return `404`. You get a stable default payload so the client can render a form without inventing values:

```json
{
  "configured": false,
  "property": 1,
  "rent_due_day": 1,
  "grace_period_days": 0,
  "late_fee_percentage": "0.00",
  "late_fee_max_percentage": null,
  "invoice_lead_days": 0,
  "late_fee_mode": "percentage",
  "late_fee_fixed_amount": null,
  "mpesa_paybill": "",
  "mpesa_account_label": "",
  "bank_name": "",
  "bank_account": "",
  "payment_notes": "",
  "notification_settings": null
}
```

Persist settings with `POST` (same field names as when `configured` is true).

#### GET / POST when configured (`200`)

Response includes `configured: true`, billing fields, `id`, `property`, `updated_at`, `updated_by`, and nested `notification_settings` (see below).

**Core billing fields**


| Field                     | Notes                                                                                                                                                                                                    |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `rent_due_day`            | 1–28 (calendar day of month for rent).                                                                                                                                                                   |
| `grace_period_days`       | Added to the rent anchor date to compute each invoice’s `due_date`.                                                                                                                                      |
| `late_fee_percentage`     | Used when `late_fee_mode` is `percentage` (% of `rent_amount`).                                                                                                                                          |
| `late_fee_max_percentage` | Optional cap on the computed percentage fee; **ignored** when mode is `fixed`.                                                                                                                           |
| `invoice_lead_days`       | 0–27. Invoice generation runs on day `max(1, clamped_rent_due_day − invoice_lead_days)` in the invoice month (see **Cron: `process_billing`**). `0` preserves legacy behavior (generate on the due day). |
| `late_fee_mode`           | `percentage` (default) or `fixed`.                                                                                                                                                                       |
| `late_fee_fixed_amount`   | Required when mode is `fixed`; cleared when mode is `percentage`.                                                                                                                                        |


**Payment instructions** (optional, non-secret copy for tenants)

`mpesa_paybill`, `mpesa_account_label`, `bank_name`, `bank_account`, `payment_notes` — plain strings for display; store secrets elsewhere.

**Nested `notification_settings`** (optional on POST; read on GET when a row exists)

Writable only via the billing config payload:

```json
"notification_settings": {
  "remind_before_due_days": 3,
  "remind_after_overdue_days": 0,
  "send_receipt_on_payment": true
}
```

- `remind_before_due_days` — `null` **disables** pre-due reminders for this property once a settings row exists. If **no** `PropertyBillingNotificationSettings` row exists, the cron uses legacy **3** days before `due_date`.
- `remind_after_overdue_days` — days after `due_date` before the **overdue** reminder is sent (after late fee has been applied). `null` is treated as **0** (as soon as eligible).
- `send_receipt_on_payment` — default `true`. When `false`, completing a payment (Stripe webhook or manual) still creates a receipt but **does not** enqueue a `payment` in-app notification / email for the tenant.

Example POST body:

```json
{
  "rent_due_day": 5,
  "grace_period_days": 3,
  "late_fee_percentage": "5.00",
  "late_fee_max_percentage": "20.00",
  "invoice_lead_days": 2,
  "late_fee_mode": "percentage",
  "late_fee_fixed_amount": null,
  "mpesa_paybill": "123456",
  "mpesa_account_label": "Unit + phone",
  "bank_name": "Example Bank",
  "bank_account": "0123456789",
  "payment_notes": "Reference: invoice number",
  "notification_settings": {
    "remind_before_due_days": 3,
    "remind_after_overdue_days": 0,
    "send_receipt_on_payment": true
  }
}
```

---

### Billing preview (read-only)

`GET /api/billing/properties/<property_pk>/billing-preview/`

**Who:** platform admin, property owner, or assigned agent.

Computed snapshot (no DB table): next generation date, estimated rent roll, and config echo.

When no `BillingConfig` exists:

```json
{
  "configured": false,
  "property": 1,
  "invoice_lead_days": 0,
  "rent_due_day": 1,
  "grace_period_days": 0,
  "next_invoice_generation_date": null,
  "next_rent_due_date": null,
  "active_lease_count": 4,
  "estimated_monthly_rent_total": "180000.00"
}
```

When configured, adds real `invoice_lead_days`, `rent_due_day`, `grace_period_days`, `next_invoice_generation_date`, and `next_rent_due_date` (anchor rent day + `grace_period_days` for the upcoming cycle).

---

### Cron: `process_billing`

Run daily (e.g. cron). **Invoices, late fees, and rent reminders are only driven by this command** — not by API calls.

1. **Invoice generation** — For each active lease with a `BillingConfig`, for the **current calendar month**, let `clamped_due = min(rent_due_day, last_day_of_month)` and `generation_day = max(1, clamped_due - invoice_lead_days)`. When `today.day == generation_day`, create the month’s invoice if missing: `period_start` / `period_end` span the month; **rent anchor** = `(year, month, clamped_due)`; `**due_date` = anchor + `grace_period_days`**.
2. **Late fees** — For `pending` / `partial` invoices with `due_date < today`, mark `overdue` and set `late_fee_amount`: **percentage** mode uses `late_fee_percentage` and optional `late_fee_max_percentage`; **fixed** mode uses `late_fee_fixed_amount` (max fields apply only in percentage mode).
3. **Reminders** — In-app notifications with type `payment_reminder` (email follows `NotificationPreference.payment_due_reminder` when global email notifications are on). At most one log per invoice per kind (`pre_due`, `due_date`, `overdue`) via `ReminderLog`.

---

### List Invoices

`GET /api/billing/invoices/`
Scoped by role:

- **Admin** → all
- **Landlord** → own properties
- **Agent** → assigned properties
- **Tenant** → own invoices

```json
[
  {
    "id": 1,
    "lease": 2,
    "period_start": "2024-02-01",
    "period_end": "2024-02-29",
    "due_date": "2024-02-01",
    "rent_amount": "25000.00",
    "late_fee_amount": "0.00",
    "total_amount": "25000.00",
    "status": "pending",
    "amount_paid": "0",
    "created_at": "2024-02-01T08:00:00Z"
  }
]
```

Invoice status values: `pending`, `paid`, `partial`, `overdue`, `cancelled`

---

### Create invoice manually (Owner / Assigned Agent / Admin)

`POST /api/billing/invoices/`

Use this to issue a rent invoice outside the automatic `process_billing` schedule (e.g. backfill, proration, or an extra period). The property must already have billing configuration (`POST /api/billing/config/<property_id>/`). The lease must be **active**; the billing period must **overlap** the lease dates (`start_date` / optional `end_date`).

**Who can call:** platform admin, the property owner, or an agent appointed to that property. Tenants and other roles get `403`.

**Constraints:**

- At most one invoice per `(lease, period_start)` — duplicate returns `400`.
- Omitting `rent_amount` uses the lease’s `rent_amount`; you may override for prorations.
- New invoices are created with `late_fee_amount = 0`, `status = pending`, `total_amount = rent_amount` (late fees are applied later by `process_billing` when overdue).

```json
// Request
{
  "lease": 2,
  "period_start": "2024-03-01",
  "period_end": "2024-03-31",
  "due_date": "2024-03-06",
  "rent_amount": "25000.00"
}
```

`rent_amount` is optional.

```json
// Response 201 — same shape as GET list/detail (`amount_paid`, `created_at` included)
{
  "id": 15,
  "lease": 2,
  "period_start": "2024-03-01",
  "period_end": "2024-03-31",
  "due_date": "2024-03-06",
  "rent_amount": "25000.00",
  "late_fee_amount": "0.00",
  "total_amount": "25000.00",
  "status": "pending",
  "amount_paid": "0",
  "created_at": "2024-03-01T08:00:00Z"
}
```

**Common errors:**


| Situation                                    | Status                                                               |
| -------------------------------------------- | -------------------------------------------------------------------- |
| Not owner / assigned agent / admin           | `403`                                                                |
| No billing config on the property            | `400` — `No billing config set for this property.`                   |
| Duplicate `period_start` for that lease      | `400` — `An invoice for this lease and period_start already exists.` |
| Lease inactive or period outside lease dates | `400` — field errors from validation                                 |
| `period_end` before `period_start`           | `400`                                                                |


---

### List payments for an invoice

`GET /api/billing/invoices/<pk>/payments/`

Same visibility as invoice detail: **admin**, **property owner**, **assigned agent**, or **tenant on the lease**.

```json
[
  {
    "id": 3,
    "invoice": 1,
    "amount": "25000.00",
    "stripe_payment_intent_id": "pi_xxx",
    "stripe_charge_id": "ch_xxx",
    "status": "completed",
    "paid_at": "2024-02-15T10:30:00Z",
    "created_at": "2024-02-15T10:29:00Z"
  }
]
```

Manual (non-Stripe) payments use a synthetic `stripe_payment_intent_id` starting with `manual-`.

---

### Record manual payment (Owner / Assigned Agent / Admin)

`POST /api/billing/invoices/<pk>/payments/`

Use when rent was collected **outside Stripe** (cash, M-Pesa, bank transfer, etc.). Creates a **completed** `Payment`, generates a **receipt** (same numbering as Stripe flow), and refreshes the invoice status (`partial` or `paid`). Unless `PropertyBillingNotificationSettings.send_receipt_on_payment` is `false` for the property, the tenant also receives a `**payment`** in-app notification (email follows `NotificationPreference.payment_received` when enabled).

**Who can call:** platform admin, property owner, or agent assigned to the property. The tenant must use `**POST .../pay/`** for Stripe instead.

**Rules:**

- `amount` is required (decimal string). It must not exceed the **remaining balance** (`total_amount` minus sum of completed payments).
- Cannot record on a **cancelled** invoice or when the balance is already **zero**.
- Multiple POSTs are allowed for **partial** payments until the invoice is fully paid.

```json
// Request
{ "amount": "25000.00" }
```

```json
// Response 201
{
  "payment": {
    "id": 4,
    "invoice": 1,
    "amount": "25000.00",
    "stripe_payment_intent_id": "manual-abc123...",
    "stripe_charge_id": "",
    "status": "completed",
    "paid_at": "2024-02-15T11:00:00Z",
    "created_at": "2024-02-15T11:00:00Z"
  },
  "receipt": {
    "id": 2,
    "payment": 4,
    "receipt_number": "RCP-202402-0002",
    "issued_at": "2024-02-15T11:00:00Z"
  }
}
```


| Error                         | Status |
| ----------------------------- | ------ |
| Tenant or unrelated user      | `403`  |
| Invoice cancelled             | `400`  |
| Balance already zero          | `400`  |
| Amount over remaining balance | `400`  |


---

### Pay Invoice (Tenant only)

`POST /api/billing/invoices/<pk>/pay/`

```json
// Request — no body needed
{}

// Response 200
{
  "client_secret": "pi_xxx_secret_yyy",
  "payment_id": 3,
  "amount": "25000.00"
}
```

**Stripe payment flow:**

1. Call `/pay/` → get `client_secret`
2. Use Stripe.js `stripe.confirmCardPayment(client_secret, { payment_method: { card: cardElement } })`
3. Stripe calls the webhook → invoice status updated, receipt auto-generated; tenant `**payment`** notification same rules as manual payments (`send_receipt_on_payment`).

---

### Receipts

List and detail return the **same object shape** (detail is one list row). Responses include legacy fields plus **enriched** payment, invoice, lease, and property context for receipts UIs.

**Who can access**

- **GET `/api/billing/receipts/`** — **Admin** (all), **Landlord** (own properties), **Agent** (assigned properties), **Tenant** (own leases).
- **GET `/api/billing/receipts/<pk>/`** — same parties as list, but only if the receipt falls in their scope; otherwise **403**. Unknown id → **404**.
- **GET `/api/billing/receipts/stats/`** — same roles as list; aggregates only over receipts the user could list.

**List:** DRF-style pagination (default page size **20**, max **100**).

```
GET /api/billing/receipts/?page=1&page_size=15&property=1&method=mpesa&month=2026-04&search=RCP
```

**Query parameters (list)**


| Param        | Required | Description |
| ------------ | -------- | ----------- |
| `property`   | no       | Property PK (positive integer). Restricts to receipts for that property. Invalid non-integer → **400** (`property`). |
| `method`     | no       | Payment method filter. Allowed values: **`mpesa`**, **`bank`**, **`card`**, **`cash`**, **`other`** (compared case-insensitively). Anything else → **400** (`method`). |
| `month`      | no       | **`YYYY-MM`** only (e.g. `2026-04`). Filters by calendar month in the **server timezone** on effective time **`Coalesce(payment.paid_at, issued_at)`**. Month must be `01`–`12`. Malformed → **400** (`month`). |
| `search`     | no       | Case-insensitive substring on receipt number, invoice number, unit name, tenant email, transaction reference, or tenant full name. |
| `page`       | no       | 1-based page index (default **1**). |
| `page_size`  | no       | Page size (default **20**). **`max_page_size` = 100** — larger values are **clamped** to 100. |

Filters **combine with AND**. Invalid combinations of params return **400** with field keys mapped to string lists (same pattern as other validated query APIs).

**Stats query parameters**

Optional **`property`** (positive integer) and **`month`** (`YYYY-MM`) with the **same validation rules** as the list endpoint. Scope is the same as list; stats are computed on the filtered receipt set.

**Response: list item / detail (200)**

```json
{
  "id": 42,
  "payment": 99,
  "receipt_number": "RCP-202604-0001",
  "issued_at": "2026-04-16T12:00:00Z",
  "amount": "1500.00",
  "payment_status": "completed",
  "paid_at": "2026-04-16T11:30:00Z",
  "payment_method": "card",
  "transaction_ref": "TXN-001",
  "transaction_reference": "TXN-001",
  "invoice_id": 12,
  "invoice_number": "INV-000012",
  "invoice_status": "paid",
  "invoice_period_start": "2026-04-01",
  "invoice_period_end": "2026-04-28",
  "tenant_id": 5,
  "tenant_name": "Jane Doe",
  "tenant_email": "jane@example.com",
  "unit_id": 3,
  "unit_name": "A1",
  "property_id": 1,
  "property_name": "Sunset Apartments",
  "charge_type": "Rent"
}
```

| Field | Notes |
| ----- | ----- |
| `payment` | PK of the related `Payment`. |
| `transaction_ref` / `transaction_reference` | Same resolved value: `transaction_reference` if set, else `stripe_charge_id`, else `null`. Both keys are returned for frontend compatibility. |
| `charge_type` | **`Rent`** or **`Rent + Service`** if any `AdditionalIncome` exists for the unit on a date within the invoice period. |
| `payment_status` | `pending`, `completed`, or `failed`. |

**Response: list page envelope (200)**

```json
{
  "count": 128,
  "next": "http://localhost:8000/api/billing/receipts/?page=2&page_size=15",
  "previous": null,
  "results": [ { "...": "same shape as detail above" } ]
}
```

**Response: stats (200)**

Exact keys (always present):

```json
{
  "total_count": 48,
  "this_month_count": 6,
  "this_month_total": "125000.50",
  "method_breakdown": {
    "mpesa": 37.5,
    "bank": 12.5,
    "card": 25.0,
    "cash": 12.5,
    "other": 12.5
  },
  "average_amount": "2604.18"
}
```

- `total_count` / averages / breakdown are over the **filtered** receipt set (role scope + optional `property` / `month` on stats).
- `this_month_count` and `this_month_total` use the **current calendar month** in the active timezone and **`Coalesce(paid_at, issued_at)`**.
- `method_breakdown` values are **percentages** (two decimal places) of receipts by payment method; when `total_count > 0`, they **sum to approximately 100** (rounding).
- `this_month_total` and `average_amount` are **decimal strings** with two fractional digits.

OpenAPI: **`/api/docs/`**, **`/api/schema/`** — see operation ids `billing_receipt_list`, `billing_receipt_detail`, `billing_receipt_stats`.

---

## Tenant Applications

Tenants browse public units (`GET /api/property/units/public/`) and submit applications. Landlords review and approve or reject.

### Submit an Application (Tenant only)

`POST /api/property/applications/`

```json
{
  "unit": 2,
  "message": "I am a working professional looking for a quiet 2-bed unit.",
  "documents": [
    "https://storage.example.com/docs/id-copy.pdf",
    "https://storage.example.com/docs/payslip.pdf"
  ]
}
```

`documents` is a list of URLs to supporting files (ID copy, payslips, references, etc.). Optional.

- One application per tenant per unit (`400` on duplicate)
- `400` if unit is already occupied

```json
// Response 201
{
  "id": 7,
  "unit": 2,
  "applicant": 5,
  "status": "pending",
  "message": "I am a working professional...",
  "reviewed_by": null,
  "reviewed_at": null,
  "created_at": "2024-03-10T09:00:00Z"
}
```

### List Applications

`GET /api/property/applications/`

- **Landlord** → all applications on their units
- **Tenant** → their own applications only
- **Admin** → all

### Review an Application (Landlord only)

**Approve** — auto-creates a lease, marks unit occupied, rejects all other pending applications on the same unit:
`PUT /api/property/applications/<pk>/`

```json
{
  "status": "approved",
  "start_date": "2024-04-01",
  "end_date": "2025-03-31",
  "rent_amount": "25000.00"
}
```

`start_date` and `rent_amount` are required. `end_date` is optional (open-ended lease).

**Reject:**

```json
{ "status": "rejected" }
```

### Withdraw an Application (Tenant only)

`PUT /api/property/applications/<pk>/`

```json
{ "status": "withdrawn" }
```

Only works while status is `pending`.

### Application Status Values


| Status      | Set by                                                        |
| ----------- | ------------------------------------------------------------- |
| `pending`   | Initial on submission                                         |
| `approved`  | Landlord/Admin                                                |
| `rejected`  | Landlord/Admin (or auto when another application is approved) |
| `withdrawn` | Applicant                                                     |


---

## Landlord Dashboard

Single endpoint that aggregates the full portfolio view. Scoped automatically — landlord sees their own data, admin sees all.

`GET /api/property/dashboard/`

```json
// Response 200
{
  "properties": {
    "total": 3,
    "total_units": 24,
    "occupied_units": 19,
    "vacant_units": 5,
    "occupancy_rate": "79.2%"
  },
  "adverts": {
    "count": 5,
    "units": [
      { "id": 2, "name": "A1", "property": "Sunset Apartments", "price": "25000.00" }
    ]
  },
  "applications": {
    "pending": 4,
    "approved_this_month": 2
  },
  "leases_ending_soon": [
    {
      "id": 1,
      "unit": "A1",
      "property": "Sunset Apartments",
      "tenant": "jane",
      "end_date": "2024-04-30",
      "days_remaining": 32
    }
  ],
  "billing": {
    "overdue_invoices": 3,
    "collected_this_month": "135000.00",
    "outstanding": "45000.00"
  },
  "maintenance": {
    "submitted": 2,
    "open": 1,
    "in_progress": 3,
    "assigned": 1
  },
  "performance": {
    "period": "2024-03",
    "by_property": [
      {
        "id": 1,
        "name": "Sunset Apartments",
        "net_income": "117500.00",
        "total_units": 8,
        "occupied_units": 7,
        "occupancy_rate": "87.5%"
      },
      {
        "id": 2,
        "name": "Riverside Cottages",
        "net_income": "45000.00",
        "total_units": 4,
        "occupied_units": 2,
        "occupancy_rate": "50.0%"
      }
    ]
  }
}
```

**Field notes:**

- `adverts` — units with `is_public=true` and `is_occupied=false` (currently listed/available)
- `leases_ending_soon` — active leases with `end_date` within 60 days
- `billing.outstanding` — sum of all unpaid invoices (pending + partial + overdue)
- `performance.by_property` — sorted by `net_income` descending (best performer first)
- `performance` period is always the current calendar month

---

## Charge Types

Landlords define the income categories they bill tenants for (water, electricity, service charge, etc.) per property. These are used when recording additional income.

### List Charge Types

`GET /api/billing/properties/<property_pk>/charge-types/`

Query: `?include_inactive=1` (or `true` / `yes`) includes rows with `is_active=false`. By default only **active** types are returned. Ordered by `display_order`, then `id`.

Accessible by: owner, assigned agent, admin.

```json
// Response 200
[
  {
    "id": 1,
    "property": 1,
    "name": "Water",
    "charge_kind": "variable",
    "default_amount": null,
    "description": "",
    "display_order": 0,
    "is_active": true,
    "created_by": 3,
    "created_at": "2024-01-15T08:00:00Z"
  }
]
```

`charge_kind`: `fixed`, `variable`, or `per_unit` (UI/metadata; `default_amount` is optional guidance for forms).

### Create Charge Type (Owner / Admin only)

`POST /api/billing/properties/<property_pk>/charge-types/`

```json
{
  "name": "Water",
  "charge_kind": "variable",
  "default_amount": "1500.00",
  "description": "Metered",
  "display_order": 10,
  "is_active": true
}
```

`name` must be unique per property. Common examples: `Water`, `Electricity`, `Service Charge`, `Garbage Collection`, `Parking`.

### Update / Delete

`PUT /api/billing/properties/<property_pk>/charge-types/<pk>/` — partial update; e.g. `{ "name": "New Name", "is_active": false }`

`DELETE /api/billing/properties/<property_pk>/charge-types/<pk>/` → `204 No Content` when the type has **no** `AdditionalIncome` rows. If income exists, `**400`** — set `is_active` to `false` instead of deleting.

---

## Additional Income

Records income from landlord-defined charges billed to a unit (water meter readings, electricity, etc.).

### List Additional Income

`GET /api/billing/properties/<property_pk>/additional-income/`

```json
// Response 200
[
  {
    "id": 1,
    "unit": 2,
    "charge_type": 1,
    "amount": "1500.00",
    "date": "2024-03-01",
    "description": "March water reading: 12 units",
    "recorded_by": 3,
    "created_at": "2024-03-05T10:00:00Z"
  }
]
```

### Record Additional Income (Owner / Admin only)

`POST /api/billing/properties/<property_pk>/additional-income/`

```json
{
  "unit": 2,
  "charge_type": 1,
  "amount": "1500.00",
  "date": "2024-03-01",
  "description": "March water reading: 12 units"
}
```

Both `unit` and `charge_type` must belong to the same property as the URL.

### Update / Delete

`PUT /api/billing/properties/<property_pk>/additional-income/<pk>/` — partial, e.g. `{ "amount": "1750.00" }`
`DELETE /api/billing/properties/<property_pk>/additional-income/<pk>/` → `204 No Content`

---

## Expenses

Records costs incurred by the landlord for a property or unit (insurance, utilities paid by landlord, taxes, etc.).

> Maintenance expenses are **auto-created** when a maintenance request is marked `completed` — no manual entry needed for those.

### List Expenses

`GET /api/billing/properties/<property_pk>/expenses/`

```json
// Response 200
[
  {
    "id": 1,
    "property": 1,
    "unit": null,
    "maintenance_request": null,
    "category": "insurance",
    "amount": "15000.00",
    "description": "Annual building insurance premium",
    "date": "2024-03-01",
    "recorded_by": 3,
    "created_at": "2024-03-01T09:00:00Z"
  },
  {
    "id": 2,
    "property": 1,
    "unit": 2,
    "maintenance_request": 5,
    "category": "maintenance",
    "amount": "8500.00",
    "description": "Maintenance completed: Leaking kitchen tap",
    "date": "2024-03-15",
    "recorded_by": 5,
    "created_at": "2024-03-15T14:30:00Z"
  }
]
```

Expense category choices: `maintenance`, `utility`, `insurance`, `tax`, `repair`, `management_fee`, `other`

### Record an Expense (Owner / Admin only)

`POST /api/billing/properties/<property_pk>/expenses/`

```json
{
  "category": "insurance",
  "amount": "15000.00",
  "date": "2024-03-01",
  "description": "Annual building insurance premium"
}
```

`unit` is optional (omit for property-wide expenses). `maintenance_request` is optional (auto-set for maintenance completions).

### Update / Delete

`PUT /api/billing/properties/<property_pk>/expenses/<pk>/` — partial, e.g. `{ "amount": "16500.00" }`
`DELETE /api/billing/properties/<property_pk>/expenses/<pk>/` → `204 No Content`

---

## Financial Reports

Computed report aggregating rent income, additional income, and expenses for a property over a period.

### Monthly Report

`GET /api/billing/reports/<property_pk>/?year=2024&month=3`

### Annual Report

`GET /api/billing/reports/<property_pk>/?year=2024`

Accessible by: owner, assigned agent, admin. Tenants do not have access.

```json
// Response 200
{
  "property": 1,
  "period": "2024-03",
  "income": {
    "rent_invoiced": "135000.00",
    "late_fees_invoiced": "6750.00",
    "total_invoiced": "141750.00",
    "total_collected": "135000.00",
    "additional_income": "4500.00",
    "additional_income_by_type": {
      "Water": "1500.00",
      "Electricity": "3000.00"
    },
    "total_income": "139500.00"
  },
  "expenses": {
    "total": "22000.00",
    "by_category": {
      "maintenance": "12000.00",
      "utility": "7000.00",
      "insurance": "3000.00"
    }
  },
  "net_income": "117500.00",
  "invoices": {
    "paid": 3,
    "pending": 0,
    "overdue": 0,
    "partial": 0,
    "cancelled": 0
  },
  "occupancy": {
    "occupied_units": 8,
    "total_units": 10,
    "occupancy_pct": "80.00"
  },
  "occupancy_series": [
    {
      "period": "2024-03",
      "occupied_units": 8,
      "total_units": 10,
      "occupancy_pct": "80.00"
    }
  ],
  "occupancy_avg_pct": "80.00"
}
```

**Field notes:**

- `rent_invoiced` / `late_fees_invoiced` — what was billed in the period (invoices by `period_start`)
- `total_collected` — actual payments received in the period (payments by `paid_at`)
- `additional_income` — sum of additional income entries by `date`
- `total_income` = `total_collected` + `additional_income`
- `net_income` = `total_income` − `expenses.total`
- **Occupancy** — physical units on the property (`deleted_at` is null). A unit counts as occupied for a calendar month if it has a lease whose dates overlap that month (`start_date` ≤ last day of month, and `end_date` is null or ≥ first day of month). `occupancy_pct` is `occupied_units / total_units × 100` with two decimal places, or `null` when `total_units` is 0.
- `**occupancy`** — present for **monthly** reports (`year` + `month`); snapshot for that month only. For **annual** reports (`year` only), this field is `null` (use `occupancy_series` + `occupancy_avg_pct`).
- `**occupancy_series`** — monthly breakdown: one object when `month` is set; twelve objects (`YYYY-01` … `YYYY-12`) when only `year` is set.
- `**occupancy_avg_pct**` — for a monthly request, same as that month’s `occupancy.occupancy_pct`. For an annual request, the simple mean of the twelve monthly percentages (months with `total_units = 0` are skipped); `null` if every month had no units.

---

## Maintenance Requests

### Submit a Request (Tenant or Landlord)

`POST /api/maintenance/requests/`

```json
{
  "property": 1,
  "unit": 2,
  "title": "Leaking kitchen tap",
  "description": "The kitchen tap has been dripping for 3 days.",
  "category": "plumbing",
  "priority": "medium"
}
```

`unit` is optional — omit for common-area requests.
Category choices: `plumbing`, `electrical`, `carpentry`, `painting`, `masonry`, `other`
Priority choices: `low`, `medium`, `high`, `urgent`

---

### List Requests

`GET /api/maintenance/requests/`
Scoped by role:

- **Admin** → all
- **Landlord** → own properties
- **Agent** → assigned properties
- **Artisan** → open requests matching their registered trade
- **Tenant** → own submitted requests

---

### Request Detail

`GET /api/maintenance/requests/<pk>/`

```json
{
  "id": 1,
  "property": 1,
  "unit": 2,
  "submitted_by": 5,
  "title": "Leaking kitchen tap",
  "description": "The kitchen tap has been dripping for 3 days.",
  "category": "plumbing",
  "priority": "medium",
  "status": "submitted",
  "assigned_to": null,
  "resolved_at": null,
  "created_at": "2024-03-01T09:00:00Z",
  "updated_at": "2024-03-01T09:00:00Z"
}
```

---

### Status Transitions

`PUT /api/maintenance/requests/<pk>/`

```json
{ "status": "open" }
```


| Transition                       | Who can trigger                               |
| -------------------------------- | --------------------------------------------- |
| `submitted` → `open`             | Property owner (landlord)                     |
| `open` → `assigned`              | Auto — triggered when submitter accepts a bid |
| `assigned` → `in_progress`       | Assigned artisan                              |
| `in_progress` → `completed`      | Request submitter (tenant or landlord)        |
| `submitted`/`open` → `cancelled` | Request submitter                             |
| any → `rejected`                 | Property owner                                |


---

### Bids

#### Artisan Places a Bid (request must be `open`)

`POST /api/maintenance/requests/<pk>/bids/`

```json
{
  "proposed_price": "8500.00",
  "message": "I can fix this within 2 days using quality materials."
}
```

```json
// Response 201
{
  "id": 3,
  "request": 1,
  "artisan": 6,
  "artisan_name": "Chris Plumber",
  "artisan_rating": "4.80",
  "artisan_trade": "Plumbing",
  "artisan_job_count": 94,
  "proposed_price": "8500.00",
  "message": "I can fix this within 2 days using quality materials.",
  "status": "pending",
  "created_at": "2024-03-02T11:00:00Z"
}
```

#### List Bids

`GET /api/maintenance/requests/<pk>/bids/`
Artisans see only their own bid. Submitter, owner, and admin see all bids.
Each bid response includes artisan metadata:

- `artisan_name`
- `artisan_rating`
- `artisan_trade`
- `artisan_job_count` (completed jobs assigned to that artisan)

#### Accept / Reject a Bid (Submitter only)

`PUT /api/maintenance/requests/<pk>/bids/<bid_id>/`

```json
{ "status": "accepted" }
// or
{ "status": "rejected" }
```

Accepting a bid automatically:

- Sets request status to `assigned`
- Sets `assigned_to` to the winning artisan
- Rejects all other bids on this request

---

### Maintenance Request Timeline

`GET /api/maintenance/requests/<pk>/timeline/`

Returns chronological activity events for the request (request creation, bids, notes, status changes, and related maintenance notifications).

```json
[
  {
    "event_type": "request_submitted",
    "description": "Maintenance request submitted: Leaking kitchen tap.",
    "actor": "Jane Doe",
    "created_at": "2024-03-01T09:00:00Z"
  },
  {
    "event_type": "bid_submitted",
    "description": "Chris Plumber submitted a bid of KES 8500.00.",
    "actor": "Chris Plumber",
    "created_at": "2024-03-02T11:00:00Z"
  },
  {
    "event_type": "notification_sent",
    "description": "Maintenance Update: You were notified via push and email.",
    "actor": "Jane Doe",
    "created_at": "2024-03-02T11:05:00Z"
  }
]
```

---

### Notes

`GET /api/maintenance/requests/<pk>/notes/`
`POST /api/maintenance/requests/<pk>/notes/`

```json
// Request
{ "note": "Artisan confirmed arrival for Tuesday 10am." }

// Response 201
{
  "id": 1,
  "request": 1,
  "author": 5,
  "note": "Artisan confirmed arrival for Tuesday 10am.",
  "created_at": "2024-03-03T08:00:00Z"
}
```

---

### Images on Unit

`GET /api/property/units/<unit_id>/images/` — list all images for a unit
`POST /api/property/units/<unit_id>/images/` — upload a new image (Admin / Owner / Agent)

```json
// POST Request — multipart/form-data
{ "image": <binary_file> }

// Response 201
{
  "id": 1,
  "property": 1,
  "image": "/media/property_images/unit_a1.jpg",
  "uploaded_at": "2024-03-01T09:05:00Z"
}
```

`GET /api/property/units/<unit_id>/images/<image_id>/` — get image detail
`DELETE /api/property/units/<unit_id>/images/<image_id>/` — delete image (Admin / Owner / Agent) → `204 No Content`

> When deleting an image, only the Admin, property owner, or assigned agent can proceed. Similar filenames automatically receive a suffix to prevent overwrites (e.g., `photo.jpg` → `photo_1.jpg`).

---

### Images on Maintenance Request

`GET /api/maintenance/requests/<pk>/images/`
`POST /api/maintenance/requests/<pk>/images/` — `multipart/form-data`


| Field   | Type |
| ------- | ---- |
| `image` | file |


```json
// Response 201
{
  "id": 1,
  "request": 1,
  "image": "/media/maintenance/leak.jpg",
  "uploaded_by": 5,
  "uploaded_at": "2024-03-01T09:05:00Z"
}
```

---

## Lease Documents

Attached to a specific lease. Stores a URL to the document (no file upload — supply a pre-hosted URL).

### List Documents for a Lease (Owner / Agent / Tenant on that lease)

`GET /api/property/leases/<lease_id>/documents/`

```json
// Response 200
[
  {
    "id": 1,
    "lease": 2,
    "document_type": "lease_agreement",
    "title": "Lease Agreement — Unit A1 2024",
    "file_url": "https://storage.example.com/docs/lease-a1-2024.pdf",
    "uploaded_by": 3,
    "signed_by": 5,
    "signed_at": "2024-02-01T10:00:00Z",
    "created_at": "2024-02-01T08:00:00Z"
  }
]
```

### Upload a Document (Owner / Agent)

`POST /api/property/leases/<lease_id>/documents/`

```json
{
  "document_type": "lease_agreement",
  "title": "Lease Agreement — Unit A1 2024",
  "file_url": "https://storage.example.com/docs/lease-a1-2024.pdf"
}
```

Document type choices: `lease_agreement`, `addendum`, `notice`, `inspection_report`, `other`

### Get a Document (Owner / Agent / Tenant on that lease)

`GET /api/property/leases/<lease_id>/documents/<doc_id>/`

```json
// Response 200
{
  "id": 1,
  "lease": 2,
  "document_type": "lease_agreement",
  "title": "Lease Agreement — Unit A1 2024",
  "file_url": "https://storage.example.com/docs/lease-a1-2024.pdf",
  "uploaded_by": 3,
  "signed_by": 5,
  "signed_at": "2024-02-01T10:00:00Z",
  "created_at": "2024-02-01T08:00:00Z"
}
```

### Delete a Document (Owner / Agent only)

`DELETE /api/property/leases/<lease_id>/documents/<doc_id>/` → `204 No Content`

Only the property owner or assigned agent can delete documents. Tenants cannot delete.

### Sign a Document (Tenant on that lease)

`POST /api/property/leases/<lease_id>/documents/<doc_id>/sign/`
No body required. Sets `signed_by` and `signed_at` on the document.
Returns `400` if the document is already signed.

---

## Property Reviews

Tenants and landlords rate a property (1–5 stars). One review per user per property.

### List Reviews for a Property (any authenticated user)

`GET /api/property/properties/<property_id>/reviews/`

```json
[
  {
    "id": 1,
    "reviewer": 5,
    "reviewer_name": "Jane Doe",
    "property": 1,
    "rating": 4,
    "comment": "Great location, responsive landlord.",
    "created_at": "2024-03-01T09:00:00Z"
  }
]
```

### Submit a Review (Tenant or Landlord)

`POST /api/property/properties/<property_id>/reviews/`

```json
{
  "rating": 4,
  "comment": "Great location, responsive landlord."
}
```

- `rating` must be 1–5
- One review per user per property (`400` on duplicate)
- Tenant must have an active or past lease on the property; Landlord must own it

### Update / Delete Your Own Review

`PATCH /api/property/properties/<property_id>/reviews/<review_id>/`

```json
{ "rating": 5, "comment": "Updated review." }
```

`DELETE /api/property/properties/<property_id>/reviews/<review_id>/` → `204 No Content`

Only the reviewer or an admin can edit/delete.

---

## Tenant Reviews

Landlords and agents review tenants (1–5 stars). Per reviewer per tenant per property.

### List Tenant Reviews on a Property (Owner / Agent / Admin)

`GET /api/property/properties/<property_id>/tenant-reviews/`

```json
[
  {
    "id": 1,
    "reviewer": 3,
    "reviewer_name": "Bob Smith",
    "tenant": 5,
    "tenant_name": "Jane Doe",
    "property": 1,
    "rating": 5,
    "comment": "Excellent tenant, always pays on time.",
    "created_at": "2024-03-01T09:00:00Z"
  }
]
```

PII is not exposed — only name is returned for reviewer and tenant.

### Submit a Tenant Review (Landlord / Agent)

`POST /api/property/properties/<property_id>/tenant-reviews/`

```json
{
  "tenant": 5,
  "rating": 5,
  "comment": "Excellent tenant, always pays on time."
}
```

- `rating` must be 1–5
- Tenant must have a lease on the property

### Update / Delete Your Own Tenant Review

`PATCH /api/property/properties/<property_id>/tenant-reviews/<review_id>/`
`DELETE /api/property/properties/<property_id>/tenant-reviews/<review_id>/` → `204 No Content`

---

## Notifications

In-app notifications for the authenticated user. Delivered by the system on key events (payments, applications, maintenance updates, etc.).

### List Notifications

`GET /api/notifications/` — returns all notifications, newest first
`GET /api/notifications/?unread=true` — unread only

```json
[
  {
    "id": 1,
    "notification_type": "payment",
    "title": "Payment received",
    "body": "We recorded a payment of KES 25000.00 toward invoice #12.\nReceipt: RCP-202403-0001\n\nTree House",
    "action_url": "",
    "is_read": false,
    "created_at": "2024-03-15T10:30:00Z"
  }
]
```

API `notification_type` values (see `Notification` model): `message`, `maintenance`, `payment`, `payment_reminder`, `lease`, `dispute`, `application`, `new_listing`, `moving`, `account`. Rent due / overdue reminders from `process_billing` use `**payment_reminder**`; receipt-after-payment uses `**payment**`.

### Mark One Notification as Read

`POST /api/notifications/<pk>/read/`
No body. Returns `200 { "status": "ok" }`.

### Mark All as Read

`POST /api/notifications/read-all/`
No body. Returns `200 { "status": "ok" }`.

---

## Messaging

Polling-based messaging between users. Conversations can optionally be tied to a property.

### List Your Conversations

`GET /api/messaging/conversations/`

```json
[
  {
    "id": 1,
    "property": 1,
    "subject": "Question about Unit A1",
    "created_by": 5,
    "created_at": "2024-03-01T09:00:00Z",
    "participants": [
      { "id": 1, "conversation": 1, "user": 5, "last_read_at": "2024-03-02T08:00:00Z", "joined_at": "2024-03-01T09:00:00Z" },
      { "id": 2, "conversation": 1, "user": 3, "last_read_at": null, "joined_at": "2024-03-01T09:00:00Z" }
    ],
    "unread_count": 2,
    "last_message": {
      "id": 5,
      "sender": 5,
      "sender_name": "Jane Doe",
      "body": "Is the unit still available?",
      "created_at": "2024-03-02T10:00:00Z"
    }
  }
]
```

### Start a Conversation

`POST /api/messaging/conversations/`

```json
{
  "subject": "Question about Unit A1",
  "property": 1,
  "participant_ids": [3, 5]
}
```

`property` is optional. `participant_ids` is a list of user IDs to add (you are added automatically).

### Get a Conversation

`GET /api/messaging/conversations/<pk>/`

### List Messages

`GET /api/messaging/conversations/<pk>/messages/`

```json
[
  {
    "id": 1,
    "sender": 5,
    "sender_name": "Jane Doe",
    "body": "Is the unit still available?",
    "created_at": "2024-03-02T10:00:00Z"
  }
]
```

### Send a Message

`POST /api/messaging/conversations/<pk>/messages/`

```json
{ "body": "Is the unit still available?" }
```

### Mark Conversation as Read

`POST /api/messaging/conversations/<pk>/read/`
No body. Updates `last_read_at` for your participant record.

---

## Disputes

Tenants and landlords can raise disputes linked to a property. Agents can view disputes for their assigned properties.

### List Disputes

`GET /api/disputes/`
Scoped by role:

- **Admin** → all
- **Landlord** → disputes on their properties
- **Agent** → disputes on their assigned properties
- **Tenant** → their own submitted disputes

### Raise a Dispute (Tenant or Landlord)

`POST /api/disputes/`

```json
{
  "property": 1,
  "unit": 2,
  "dispute_type": "rent",
  "title": "Overcharged rent for March",
  "description": "My rent statement shows an amount higher than what was agreed in the lease."
}
```

`unit` is optional. Dispute type choices: `rent`, `maintenance`, `noise`, `damage`, `lease`, `other`

- Tenant must have an active lease on the property
- Landlord must own the property
- Agents and Artisans cannot create disputes

```json
// Response 201
{
  "id": 1,
  "created_by": 5,
  "property": 1,
  "unit": 2,
  "dispute_type": "rent",
  "status": "open",
  "title": "Overcharged rent for March",
  "description": "...",
  "resolved_by": null,
  "resolved_at": null,
  "created_at": "2024-03-10T09:00:00Z"
}
```

### Get a Dispute

`GET /api/disputes/<pk>/`

### Update Dispute Status (PATCH)

`PATCH /api/disputes/<pk>/`

```json
{ "status": "under_review" }
```


| Transition                       | Who                     |
| -------------------------------- | ----------------------- |
| `open` → `under_review`          | Property owner or Admin |
| `under_review` → `resolved`      | Admin only              |
| `open`/`under_review` → `closed` | Dispute creator         |


Resolved and closed disputes cannot be reopened.

### Dispute Messages

#### List Messages

`GET /api/disputes/<pk>/messages/`

```json
[
  {
    "id": 1,
    "dispute": 1,
    "sender": 5,
    "sender_name": "Jane Doe",
    "body": "I have attached the original signed lease for reference.",
    "created_at": "2024-03-10T10:00:00Z"
  }
]
```

#### Post a Message (any dispute participant)

`POST /api/disputes/<pk>/messages/`

```json
{ "body": "I have attached the original signed lease for reference." }
```

---

## Moving Companies

### Browse Moving Companies (any authenticated user)

`GET /api/moving/companies/`
Returns all active companies (`is_active=true`).

```json
// Response 200
[
  {
    "id": 1,
    "user": 7,
    "company_name": "Swift Movers Ltd",
    "description": "Professional moving services across the city",
    "phone": "+254712345678",
    "city": "Nairobi",
    "service_areas": ["Nairobi", "Mombasa"],
    "base_price": "5000.00",
    "price_per_km": "50.00",
    "is_verified": false,
    "is_active": true,
    "average_rating": 4.3,
    "review_count": 12
  }
]
```

### Get Company Detail

`GET /api/moving/companies/<pk>/`

---

### Bookings

#### Create a Booking (any authenticated user)

`POST /api/moving/bookings/`

```json
{
  "company": 1,
  "moving_date": "2026-04-15",
  "moving_time": "08:00:00",
  "pickup_address": "45 Old Town Road, Nairobi",
  "delivery_address": "12 New Estate, Westlands",
  "notes": "Fragile items — please handle with care"
}
```

```json
// Response 201
{
  "id": 1,
  "company": 1,
  "customer": 5,
  "customer_name": "Jane Doe",
  "moving_date": "2026-04-15",
  "moving_time": "08:00:00",
  "pickup_address": "45 Old Town Road, Nairobi",
  "delivery_address": "12 New Estate, Westlands",
  "status": "pending",
  "estimated_price": null,
  "notes": "Fragile items — please handle with care",
  "created_at": "2026-03-30T09:00:00Z"
}
```

#### List Bookings

`GET /api/moving/bookings/`

- **MovingCompany** → all bookings made with their company
- **Others** → their own bookings as customer

#### Update Booking Status

`PUT /api/moving/bookings/<pk>/`


| Transition                  | Who                 |
| --------------------------- | ------------------- |
| `pending` → `confirmed`     | Company             |
| `pending` → `cancelled`     | Customer or Company |
| `confirmed` → `in_progress` | Company             |
| `confirmed` → `cancelled`   | Customer or Company |
| `in_progress` → `completed` | Company             |


```json
// Company confirms and sets price estimate
{ "status": "confirmed", "estimated_price": "8500.00" }

// Customer or company cancels
{ "status": "cancelled" }
```

---

### Moving Company Reviews

#### List Reviews for a Company

`GET /api/moving/companies/<pk>/reviews/`

```json
[
  {
    "id": 1,
    "company": 1,
    "reviewer": 5,
    "reviewer_name": "Jane Doe",
    "booking": 1,
    "rating": 4,
    "comment": "Professional and on time.",
    "created_at": "2026-03-30T10:00:00Z"
  }
]
```

#### Write a Review (any authenticated user)

`POST /api/moving/companies/<pk>/reviews/`

```json
{
  "rating": 4,
  "comment": "Professional and on time.",
  "booking": 1
}
```

- `rating` must be 1–5
- `booking` is optional — link to the actual booking for context
- One review per user per company (`400` on duplicate)

#### Update / Delete Own Review

`PATCH /api/moving/companies/<pk>/reviews/<review_id>/`

```json
{ "rating": 5, "comment": "Even better on reflection." }
```

`DELETE /api/moving/companies/<pk>/reviews/<review_id>/` → `204 No Content`

Reviewer or Admin only.

---

## Neighborhood Insights

Landlords and agents can attach points of interest to a property to help tenants understand the neighborhood.

### List Insights for a Property (any authenticated user)

`GET /api/neighborhood/properties/<property_id>/insights/`

Optional filter: `?type=school` — filter by insight type.

```json
[
  {
    "id": 1,
    "property": 1,
    "insight_type": "school",
    "name": "Westlands Primary School",
    "address": "Westlands Road, Nairobi",
    "distance_km": "0.80",
    "rating": "4.2",
    "lat": "-1.268250",
    "lng": "36.811900",
    "notes": "Government school with good KCPE results",
    "added_by": 3,
    "added_by_name": "Bob Smith",
    "created_at": "2026-03-30T09:00:00Z"
  }
]
```

Insight type choices: `school`, `hospital`, `safety`, `transit`, `restaurant`, `other`

### Add an Insight (Owner / Assigned Agent / Admin)

`POST /api/neighborhood/properties/<property_id>/insights/`

```json
{
  "insight_type": "hospital",
  "name": "Aga Khan University Hospital",
  "address": "3rd Parklands Ave, Nairobi",
  "distance_km": "2.1",
  "rating": "4.7",
  "lat": "-1.261800",
  "lng": "36.816300",
  "notes": "Level 6 hospital with 24/7 A&E"
}
```

All fields except `insight_type` and `name` are optional.

```json
// Response 201
{
  "id": 2,
  "property": 1,
  "insight_type": "hospital",
  "name": "Aga Khan University Hospital",
  ...
}
```

### Get Insight Detail (any authenticated user)

`GET /api/neighborhood/properties/<property_id>/insights/<insight_id>/`

### Update an Insight (Adder or Admin)

`PATCH /api/neighborhood/properties/<property_id>/insights/<insight_id>/`

```json
{ "rating": "4.8", "notes": "Expanded A&E wing in 2025" }
```

### Delete an Insight (Adder or Admin)

`DELETE /api/neighborhood/properties/<property_id>/insights/<insight_id>/` → `204 No Content`

---

## Dashboards

All dashboard endpoints are read-only aggregations computed on the fly. Each is scoped to the caller's role — the wrong role receives `403`.

---

### Admin Dashboard

#### System Overview

`GET /api/dashboard/admin/`

```json
// Response 200
{
  "users": {
    "total": 150,
    "by_role": {
      "Tenant": 80,
      "Landlord": 30,
      "Agent": 20,
      "Artisan": 15,
      "MovingCompany": 5
    },
    "new_last_30_days": 12
  },
  "properties": {
    "total": 45,
    "total_units": 320,
    "occupied": 275,
    "vacant": 45,
    "occupancy_rate": "85.9%"
  },
  "billing": {
    "revenue_this_month": "1250000.00",
    "outstanding": "450000.00",
    "overdue_invoices": 8
  },
  "maintenance": {
    "submitted": 5,
    "open": 12,
    "assigned": 8,
    "in_progress": 6,
    "completed_this_month": 15
  },
  "disputes": {
    "open": 3,
    "under_review": 2
  },
  "moving": {
    "total_companies": 5,
    "pending_bookings": 10,
    "completed_this_month": 8
  }
}
```

---

#### User Management

**List Users**
`GET /api/dashboard/admin/users/`

Optional query params:


| Param       | Description                                   |
| ----------- | --------------------------------------------- |
| `role`      | Filter by role name — e.g. `?role=Tenant`     |
| `search`    | Search username, email, first name, last name |
| `is_active` | `true` or `false`                             |


```json
// Response 200
[
  {
    "id": 5,
    "username": "jane",
    "email": "jane@example.com",
    "first_name": "Jane",
    "last_name": "Doe",
    "phone": "+254712345678",
    "role": 2,
    "role_name": "Tenant",
    "is_active": true,
    "is_staff": false,
    "date_joined": "2024-01-15T08:00:00Z"
  }
]
```

**Get User Detail + Role History**
`GET /api/dashboard/admin/users/<pk>/`

```json
// Response 200
{
  "user": { ...same fields as list... },
  "role_change_history": [
    {
      "id": 1,
      "user": 5,
      "user_username": "jane",
      "changed_by": 1,
      "changed_by_username": "admin",
      "old_role": 2,
      "old_role_name": "Tenant",
      "new_role": 3,
      "new_role_name": "Landlord",
      "changed_at": "2026-03-30T10:00:00Z",
      "reason": "Upgraded by admin"
    }
  ]
}
```

**Update User Role / Active Status**
`PUT /api/dashboard/admin/users/<pk>/`

```json
// Change role (logs the change in RoleChangeLog)
{ "role": 3, "reason": "Upgraded from tenant to landlord" }

// Deactivate user
{ "is_active": false }

// Both at once
{ "role": 3, "is_active": true, "reason": "Account correction" }
```

- `reason` is optional free text stored in the role change log
- Role change is logged only when the new role differs from the current role
- Only the FK is updated — no profile migration is performed

---

#### Content Moderation

**List All Reviews**
`GET /api/dashboard/admin/moderation/reviews/`
`GET /api/dashboard/admin/moderation/reviews/?type=property`
`GET /api/dashboard/admin/moderation/reviews/?type=tenant`

Returns a unified list of both `PropertyReview` and `TenantReview` records sorted by `created_at` descending. Use `?type=` to filter to one kind.

```json
[
  {
    "id": 1,
    "type": "property",
    "reviewer": 5,
    "reviewer_name": "Jane Doe",
    "subject_id": 1,
    "subject_name": "Sunset Apartments",
    "rating": 2,
    "comment": "Mold in the bathroom — unacceptable.",
    "created_at": "2026-03-28T09:00:00Z"
  },
  {
    "id": 3,
    "type": "tenant",
    "reviewer": 3,
    "reviewer_name": "Bob Smith",
    "subject_id": 5,
    "subject_name": "Jane Doe",
    "rating": 1,
    "comment": "Damaged property on departure.",
    "created_at": "2026-03-27T14:00:00Z"
  }
]
```

**Delete a Review**
`DELETE /api/dashboard/admin/moderation/reviews/<pk>/?type=property` → `204 No Content`
`DELETE /api/dashboard/admin/moderation/reviews/<pk>/?type=tenant` → `204 No Content`

`?type` is required — returns `400` if omitted.

---

### Tenant Dashboard

`GET /api/dashboard/tenant/`

```json
// Response 200
{
  "active_lease": {
    "id": 2,
    "unit": "A1",
    "property": "Sunset Apartments",
    "rent_amount": "25000.00",
    "start_date": "2024-02-01",
    "end_date": "2025-01-31",
    "days_remaining": 120
  },
  "invoices": {
    "pending": 1,
    "overdue": 0,
    "next_due": {
      "id": 8,
      "due_date": "2026-04-01",
      "amount": "25000.00",
      "status": "pending"
    }
  },
  "maintenance": {
    "open_requests": 2
  },
  "notifications": {
    "unread": 5
  }
}
```

`active_lease` is `null` if the tenant has no active lease. `next_due` is `null` if no pending/partial invoices exist.

---

### Artisan Dashboard

`GET /api/dashboard/artisan/`

```json
// Response 200
{
  "trade": "plumbing",
  "open_jobs": {
    "count": 3,
    "items": [
      {
        "id": 12,
        "title": "Burst pipe in Unit B3",
        "category": "plumbing",
        "priority": "high",
        "property": 1,
        "created_at": "2026-03-29T08:00:00Z"
      }
    ]
  },
  "active_bids": {
    "count": 1,
    "items": [
      {
        "id": 5,
        "request_id": 10,
        "request_title": "Kitchen tap leaking",
        "proposed_price": "8500.00",
        "status": "pending",
        "created_at": "2026-03-28T11:00:00Z"
      }
    ]
  },
  "completed_this_month": 4
}
```

`open_jobs` returns up to 10 most recent open requests matching the artisan's registered trade.

---

### Agent Dashboard

`GET /api/dashboard/agent/`

```json
// Response 200
{
  "assigned_properties": {
    "count": 3,
    "total_units": 24,
    "occupied_units": 19,
    "occupancy_rate": "79.2%",
    "items": [
      {
        "id": 1,
        "name": "Sunset Apartments",
        "property_type": "apartment",
        "total_units": 8,
        "occupied_units": 7
      }
    ]
  },
  "pending_applications": 4,
  "open_maintenance_requests": 6,
  "active_disputes": 1
}
```

---

### Moving Company Dashboard

`GET /api/dashboard/moving-company/`

Returns `404` if the user has not yet created a company profile via `PATCH /api/auth/me/profile/`.

```json
// Response 200
{
  "company_name": "Swift Movers Ltd",
  "is_verified": false,
  "bookings": {
    "pending": 4,
    "confirmed": 2,
    "in_progress": 1,
    "completed_this_month": 8,
    "cancelled": 3,
    "total": 18
  },
  "reviews": {
    "total": 12,
    "average_rating": 4.25,
    "recent": [
      {
        "id": 7,
        "reviewer_name": "Jane Doe",
        "rating": 5,
        "comment": "Professional and careful with our furniture.",
        "created_at": "2026-03-28T10:00:00Z"
      }
    ]
  }
}
```

---

## Docs & Schema


| URL            | Description                           |
| -------------- | ------------------------------------- |
| `/api/docs/`   | Swagger UI — interactive API explorer |
| `/api/redoc/`  | ReDoc — clean reference docs          |
| `/api/schema/` | Download OpenAPI YAML schema          |


---

## Error Responses

All errors follow this structure:

```json
{ "detail": "Human-readable error message." }
```

Common status codes:


| Code | Meaning                                                      |
| ---- | ------------------------------------------------------------ |
| 400  | Validation error — check field-level detail in response body |
| 401  | Missing or invalid token                                     |
| 403  | Authenticated but not allowed (wrong role or ownership)      |
| 404  | Resource not found                                           |


Validation errors return field-level detail:

```json
{
  "proposed_price": ["This field is required."],
  "category": ["\"xyz\" is not a valid choice."]
}
```

---

## Monitoring *(Admin only)*

All endpoints require `is_staff=True`. Non-admin users receive `403`.

---

### List System Metrics

`GET /api/monitoring/metrics/`

Query params:

- `metric_type` — filter to one metric type
- `hours` — lookback window (default `24`)

**Metric type values:** `overdue_invoice_count`, `monthly_revenue`, `occupancy_rate`, `open_maintenance_count`, `open_dispute_count`, `pending_application_count`, `payment_success_rate`

```json
// Response 200
[
  {
    "id": 1,
    "metric_type": "overdue_invoice_count",
    "value": "7.00",
    "recorded_at": "2026-03-31T10:00:00Z"
  },
  {
    "id": 2,
    "metric_type": "occupancy_rate",
    "value": "82.50",
    "recorded_at": "2026-03-31T10:00:00Z"
  }
]
```

Metrics are written by the `record_metrics` management command. There are no metrics until that command has run at least once.

---

### List Alert Rules

`GET /api/monitoring/alert-rules/`

```json
// Response 200
[
  {
    "id": 1,
    "name": "High overdue invoice count (warning)",
    "description": "More than 10 invoices are overdue across the platform.",
    "metric_type": "overdue_invoice_count",
    "condition": "gte",
    "threshold_value": "10.00",
    "severity": "warning",
    "enabled": true,
    "created_by": null,
    "created_at": "2026-03-31T09:00:00Z"
  }
]
```

Six default rules are seeded on first migration. `created_by` is `null` for seeded rules.

---

### Create Alert Rule

`POST /api/monitoring/alert-rules/`

```json
// Request
{
  "name": "Very high open maintenance",
  "description": "More than 50 maintenance requests are unresolved.",
  "metric_type": "open_maintenance_count",
  "condition": "gte",
  "threshold_value": "50.00",
  "severity": "critical",
  "enabled": true
}

// Response 201
{
  "id": 7,
  "name": "Very high open maintenance",
  "metric_type": "open_maintenance_count",
  "condition": "gte",
  "threshold_value": "50.00",
  "severity": "critical",
  "enabled": true,
  "created_by": 1,
  "created_at": "2026-03-31T11:00:00Z"
}
```

**condition values:** `gt`, `gte`, `lt`, `lte`  
**severity values:** `info`, `warning`, `critical`

---

### Update / Delete Alert Rule

`PATCH /api/monitoring/alert-rules/<pk>/`

```json
// Request — disable a rule
{ "enabled": false }

// Response 200
{ "id": 1, "enabled": false, ... }
```

`DELETE /api/monitoring/alert-rules/<pk>/` → `204 No Content`

---

### List Alert Instances

`GET /api/monitoring/alerts/`

Query params:

- `status` — `triggered` | `acknowledged` | `resolved`
- `severity` — `info` | `warning` | `critical`
- `hours` — lookback window (default `72`)

```json
// Response 200
[
  {
    "id": 1,
    "rule": 1,
    "rule_name": "High overdue invoice count (warning)",
    "rule_severity": "warning",
    "rule_metric_type": "overdue_invoice_count",
    "status": "triggered",
    "triggered_at": "2026-03-31T10:05:00Z",
    "triggered_value": "14.00",
    "acknowledged_by": null,
    "acknowledged_by_username": null,
    "acknowledged_at": null,
    "resolved_at": null,
    "note": ""
  }
]
```

---

### Acknowledge / Resolve an Alert

`PATCH /api/monitoring/alerts/<pk>/`

**Status machine:** `triggered → acknowledged → resolved` (terminal). Cannot transition backwards.

```json
// Acknowledge
{ "status": "acknowledged", "note": "Investigating — contacting landlords with overdue invoices." }

// Resolve
{ "status": "resolved", "note": "All overdue invoices followed up; count back to normal." }

// Response 200
{
  "id": 1,
  "status": "acknowledged",
  "acknowledged_by": 1,
  "acknowledged_by_username": "admin",
  "acknowledged_at": "2026-03-31T10:30:00Z",
  "note": "Investigating — contacting landlords with overdue invoices.",
  ...
}
```

Alerts can also be auto-resolved by the `check_alert_rules` command when the metric returns to the normal range.

---

### Monitoring Dashboard

`GET /api/monitoring/dashboard/`

Single endpoint for an at-a-glance health overview. Suitable for a status page or ops widget.

```json
// Response 200
{
  "health_status": "warning",
  "active_alert_counts": {
    "critical": 0,
    "warning": 1,
    "info": 0
  },
  "latest_metrics": {
    "overdue_invoice_count": { "value": "14.00", "recorded_at": "2026-03-31T10:00:00Z" },
    "monthly_revenue":       { "value": "345000.00", "recorded_at": "2026-03-31T10:00:00Z" },
    "occupancy_rate":        { "value": "82.50", "recorded_at": "2026-03-31T10:00:00Z" },
    "open_maintenance_count":    { "value": "8.00",  "recorded_at": "2026-03-31T10:00:00Z" },
    "open_dispute_count":        { "value": "2.00",  "recorded_at": "2026-03-31T10:00:00Z" },
    "pending_application_count": { "value": "5.00",  "recorded_at": "2026-03-31T10:00:00Z" },
    "payment_success_rate":      { "value": "96.00", "recorded_at": "2026-03-31T10:00:00Z" }
  },
  "top_active_alerts": [
    {
      "id": 1,
      "rule_name": "High overdue invoice count (warning)",
      "rule_severity": "warning",
      "status": "triggered",
      "triggered_at": "2026-03-31T10:05:00Z",
      "triggered_value": "14.00",
      ...
    }
  ],
  "trends": {
    "overdue_invoice_count": [
      { "value": "10.00", "recorded_at": "2026-03-30T22:00:00Z" },
      { "value": "12.00", "recorded_at": "2026-03-31T04:00:00Z" },
      { "value": "14.00", "recorded_at": "2026-03-31T10:00:00Z" }
    ],
    "monthly_revenue": [...],
    "occupancy_rate": [...]
  }
}
```

`**health_status` values:**

- `healthy` — no active (triggered or acknowledged) alerts
- `warning` — at least one active warning-severity alert, no critical
- `critical` — at least one active critical-severity alert

`**latest_metrics`** — only keys with recorded data appear. If `record_metrics` has never run, this object will be empty.

`**trends**` — last 24 hours of data points for `overdue_invoice_count`, `monthly_revenue`, and `occupancy_rate`, in chronological order.

---

### Scheduled Commands

Run on a cron schedule (e.g. every 15 minutes):

```bash
python manage.py record_metrics      # snapshot current platform metrics
python manage.py check_alert_rules   # evaluate rules; fire/auto-resolve alerts
```

`check_alert_rules` fires an in-app notification to all admin users when a new alert is triggered, respecting each admin's `NotificationPreference`.

---

## User Impersonation *(Admin only)*

Admins can act as any non-admin user by adding one header to any API request. Every impersonated request is automatically logged.

### How to impersonate

Add `X-Impersonate-User: <user_pk>` alongside your normal admin token:

```
Authorization: Token <admin-token>
X-Impersonate-User: 42
```

The response will be exactly as if user 42 made the request — scoped data, role-based permissions, everything. Your admin token is still used for authentication; only `request.user` is swapped.

**Rules:**

- Requester must be `is_staff=True`
- Target user must be active (`is_active=True`) and non-admin (`is_staff=False`)
- Attempting to impersonate another admin returns `403`
- Attempting to impersonate a non-existent or inactive user returns `403`
- Omitting the header uses your own identity normally

**Example — view a tenant's invoices as that tenant:**

```
GET /api/billing/invoices/
Authorization: Token <admin-token>
X-Impersonate-User: 42
```

Returns only the invoices that belong to user 42, exactly as that tenant would see them.

---

### View Impersonation Logs

`GET /api/monitoring/impersonation-logs/`

Query params:

- `target_user` — filter by target user PK
- `hours` — lookback window (default `72`)

```json
// Response 200
[
  {
    "id": 1,
    "admin": 1,
    "admin_username": "admin",
    "target_user": 42,
    "target_username": "jane_tenant",
    "target_role": "Tenant",
    "path": "/api/billing/invoices/",
    "method": "GET",
    "timestamp": "2026-03-31T14:22:00Z"
  }
]
```

Each entry represents a single impersonated HTTP request. There is no session concept — every request with the header is a discrete log entry.