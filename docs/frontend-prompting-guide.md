# Frontend Prompting Guide

A structured guide for using the **Claude frontend-design plugin** to build the Tree House frontend against this API.

> **Plugin in use:** `frontend-design` — generates distinctive, production-grade interfaces. Invoke it with `/frontend-design` followed by your screen description and API context.

---

## How to use this guide

Each section has a **ready-to-paste `/frontend-design` prompt**. The structure is always:

1. What screen to build
2. The API endpoint(s) it calls (exact field names)
3. Business rules and role restrictions
4. Design intent (tone, layout, key interactions)

The plugin handles visual design decisions. Your job is to give it accurate API shapes and clear business rules — it does the rest.

---

## Prime block — include in every prompt

Every `/frontend-design` prompt should open with this so the plugin knows the API contract:

```
Backend: Django REST API at http://localhost:8000
Auth: All protected requests need header → Authorization: Token <token>
Token source: POST /api/auth/login/ returns { "key": "<token>" }
Store token in localStorage under key "treehouse_token"
Roles: Admin, Landlord, Agent, Tenant, Artisan, MovingCompany
Role is a numeric ID on the user object — resolved from GET /api/auth/roles/
On 401 response: clear token and redirect to /login
On 403 response: show an inline "You don't have permission" message — do not redirect
```

Paste this at the top of every prompt. It is short enough to repeat — do not rely on the plugin remembering it across sessions.

---

## Shared Axios instance — build this first

Before any screen, generate the API client once:

```
/frontend-design

Build a shared API client for a Next.js 14 (App Router) + TypeScript project.

[paste prime block above]

Create:
- lib/api.ts — Axios instance, base URL http://localhost:8000, interceptor that
  reads "treehouse_token" from localStorage and injects the Authorization header,
  response interceptor that clears token and redirects to /login on 401
- lib/auth.ts — login(username, password): calls POST /api/auth/login/ → stores key,
  then calls GET /api/auth/user/ → returns user object; logout(): clears token
- store/auth.ts — Zustand store: { user, token, role, setUser, clearUser }
  user shape: { pk, username, email, first_name, last_name, phone, role, is_staff }
- middleware.ts — redirect unauthenticated users to /login for all routes except
  /login, /register, and /search

Design: no UI needed for this step — just the utility files.
```

---

## Session structure — build in this order

Work through features in this sequence. Each section is a ready-to-paste `/frontend-design` prompt.

---

### 1. Role-based routing & login

```
/frontend-design

Backend: Django REST API at http://localhost:8000
Auth: All protected requests need header → Authorization: Token <token>
Token source: POST /api/auth/login/ returns { "key": "<token>" }
Store token in localStorage under key "treehouse_token"
Roles: Admin, Landlord, Agent, Tenant, Artisan, MovingCompany
Role is a numeric ID on the user object — resolved from GET /api/auth/roles/
On 401 response: clear token and redirect to /login
On 403 response: show an inline "You don't have permission" message — do not redirect

Build a login page at /login and role-based post-login routing for a property management app called Tree House.

Login endpoint:
  POST /api/auth/login/
  Body: { username, password }
  Response: { key: "abc123token" }

After login, resolve the user:
  GET /api/auth/user/
  Response: { pk, username, email, first_name, last_name, phone, role (numeric ID), is_staff }

Resolve role name:
  GET /api/auth/roles/
  Response: [{ id, name }]

Route each role to their home page after login:
  Admin        → /admin/dashboard
  Landlord     → /landlord/dashboard
  Agent        → /agent/dashboard
  Tenant       → /tenant/dashboard
  Artisan      → /artisan/dashboard
  MovingCompany → /moving/dashboard

Also create:
- useRole() hook — returns current role name from Zustand
- RoleGuard component — takes allowed=[...role names], renders a 403 message if current role not in list
- middleware.ts — redirect unauthenticated users to /login for all routes except /login, /register, /search

Design: clean, professional login form. Property management tone — trustworthy, not flashy.
Show the Tree House logo/wordmark at the top. Include a "Register" link below the form.
```

---

### 2. Public unit search (no auth required)

```
/frontend-design

Backend: Django REST API at http://localhost:8000
Auth: All protected requests need header → Authorization: Token <token>
Token source: POST /api/auth/login/ returns { "key": "<token>" }
Store token in localStorage under key "treehouse_token"
Roles: Admin, Landlord, Agent, Tenant, Artisan, MovingCompany
Role is a numeric ID on the user object — resolved from GET /api/auth/roles/
On 401 response: clear token and redirect to /login
On 403 response: show an inline "You don't have permission" message — do not redirect

Build a public property search page at /search. No auth required.

Endpoint:
  GET /api/property/units/public/
  Query params: price_min, price_max, bedrooms, bathrooms, property_type,
                amenities (keyword), parking (true/false)
  Response items: { id, unit_number, bedrooms, bathrooms, rent_amount, property_type,
                    amenities, parking, is_occupied, tour_url,
                    images: [{ image_url }],
                    property: { id, name, address, city } }

Build:
- Sticky filter bar: price range slider, bedrooms (1–5+), bathrooms, property type dropdown, amenities text, parking toggle
- Results grid (3 cols desktop, 1 col mobile): unit card with hero image, price/month, beds/baths, address, "Apply" CTA
- "Apply" routes to /register if not authenticated, or /units/[id]/apply if logged in as Tenant
- Pagination: page / page_size=20, "Showing X–Y of Z results", Prev/Next buttons
- Loading: card skeletons matching the grid layout
- Empty state: illustration + "No units match your search — try adjusting the filters"

Design: bright, modern property listing aesthetic. Cards with rounded corners and subtle shadow.
Hero image takes 60% of the card. Price displayed prominently in green.
```

---

### 3. Tenant dashboard

```
/frontend-design

Backend: Django REST API at http://localhost:8000
Auth: All protected requests need header → Authorization: Token <token>
Token source: POST /api/auth/login/ returns { "key": "<token>" }
Store token in localStorage under key "treehouse_token"
Roles: Admin, Landlord, Agent, Tenant, Artisan, MovingCompany
Role is a numeric ID on the user object — resolved from GET /api/auth/roles/
On 401 response: clear token and redirect to /login
On 403 response: show an inline "You don't have permission" message — do not redirect

Build the tenant dashboard at /tenant/dashboard. Wrap with RoleGuard allowed=["Tenant"].

Endpoint:
  GET /api/dashboard/tenant/
  Response:
  {
    "active_lease": {
      "id", "unit": { "unit_number", "property": { "name", "address" } },
      "start_date", "end_date", "rent_amount", "is_active"
    },
    "invoice_summary": { "total_invoices", "paid", "pending", "overdue" },
    "open_maintenance": <count>,
    "unread_notifications": <count>
  }

Build:
- Lease card: property name, unit number, address, monthly rent, lease end date, days remaining
- Warning banner if active_lease is null: "You have no active lease — browse available units"
- Invoice summary: 4 stat tiles (Total, Paid, Pending, Overdue) with colour coding
- Quick-action row: "Pay Rent" → /tenant/invoices, "Report Issue" → /maintenance/new,
  "Messages" → /messages, "Notifications" → /notifications
- Open maintenance count badge on the "Report Issue" button

Design: warm, residential feel. Soft off-white background, teal/green accent colour.
Lease card is the hero element — large and prominent at the top.
```

---

### 4. Tenant — invoices & Stripe payment

```
/frontend-design

Backend: Django REST API at http://localhost:8000
Auth: All protected requests need header → Authorization: Token <token>
Token source: POST /api/auth/login/ returns { "key": "<token>" }
Store token in localStorage under key "treehouse_token"
Roles: Admin, Landlord, Agent, Tenant, Artisan, MovingCompany
Role is a numeric ID on the user object — resolved from GET /api/auth/roles/
On 401 response: clear token and redirect to /login
On 403 response: show an inline "You don't have permission" message — do not redirect

Build the invoice list at /tenant/invoices and a full Stripe payment flow.
Wrap with RoleGuard allowed=["Tenant"].

List endpoint:
  GET /api/billing/invoices/
  Response items: { id, period_start, period_end, rent_amount, late_fee_amount,
                    total_amount, amount_paid, status, due_date }

Status badge colours: paid=green, pending=amber, overdue=red, partial=orange, cancelled=grey

Payment flow (triggered from "Pay Now" on an unpaid invoice):
  Step 1 — get Stripe client_secret:
    POST /api/billing/invoices/<id>/pay/
    Body: { amount: <total_amount> }
    Response: { client_secret: "pi_xxx_secret_xxx" }

  Step 2 — collect card and confirm with Stripe.js:
    const stripe = await loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY)
    await stripe.confirmCardPayment(client_secret, { payment_method: { card } })

  Step 3 — poll until paid:
    GET /api/billing/invoices/<id>/ every 2 seconds until status === "paid" (max 30s)

  Step 4 — show receipt:
    GET /api/billing/receipts/
    Find receipt matching the invoice and display: receipt number, amount, date, property name

Design: invoice list is a clean table on desktop, stacked cards on mobile.
Payment modal is a focused, minimal overlay — card element centred, large "Pay KES X" button.
Receipt screen feels like a confirmation — green checkmark, receipt number, print button.
```

---

### 5. Tenant — apply for a unit

```
/frontend-design

Backend: Django REST API at http://localhost:8000
Auth: All protected requests need header → Authorization: Token <token>
Token source: POST /api/auth/login/ returns { "key": "<token>" }
Store token in localStorage under key "treehouse_token"
Roles: Admin, Landlord, Agent, Tenant, Artisan, MovingCompany
Role is a numeric ID on the user object — resolved from GET /api/auth/roles/
On 401 response: clear token and redirect to /login
On 403 response: show an inline "You don't have permission" message — do not redirect

Build a unit detail page at /units/[id] and an application form at /units/[id]/apply.

Unit detail — fetch:
  GET /api/property/units/public/ and filter by id, OR read from previous search results

Application form — submit:
  POST /api/property/applications/
  Body: { unit: <unit_id>, message: "" }
  Response 201: { id, unit, applicant, status, created_at }
  Error 400: already applied → show "You have already applied for this unit"

Application list at /tenant/applications:
  GET /api/property/applications/
  Response: [{ id, unit: { unit_number, property: { name } }, status, created_at }]

Status badges: pending=amber, approved=green, rejected=red, withdrawn=grey

Rules:
- /units/[id]/apply is protected — RoleGuard allowed=["Tenant"]
- After successful application, redirect to /tenant/applications with success toast
- "Withdraw" button on pending applications:
    PUT /api/property/applications/<id>/
    Body: { status: "withdrawn" }

Design: unit detail is full-width with image gallery, key stats (beds/baths/price), and a sticky
"Apply Now" button. Application form is a simple modal with a message textarea.
```

---

### 6. Landlord dashboard

```
/frontend-design

Backend: Django REST API at http://localhost:8000
Auth: All protected requests need header → Authorization: Token <token>
Token source: POST /api/auth/login/ returns { "key": "<token>" }
Store token in localStorage under key "treehouse_token"
Roles: Admin, Landlord, Agent, Tenant, Artisan, MovingCompany
Role is a numeric ID on the user object — resolved from GET /api/auth/roles/
On 401 response: clear token and redirect to /login
On 403 response: show an inline "You don't have permission" message — do not redirect

Build the landlord dashboard at /landlord/dashboard. Wrap with RoleGuard allowed=["Landlord"].

Endpoint:
  GET /api/property/dashboard/
  Response:
  {
    "properties": <count>, "units": <count>,
    "occupied_units": <count>, "vacant_units": <count>, "occupancy_rate": <float 0-100>,
    "monthly_revenue": <decimal>, "outstanding_invoices": <decimal>, "overdue_invoice_count": <int>,
    "open_maintenance_requests": <int>,
    "almost_ending_leases": [{ "id", "unit": { "unit_number" }, "end_date", "tenant_name" }],
    "top_performing_properties": [{ "id", "name", "net_income" }]
  }

Build:
- KPI row: Properties, Occupancy %, Monthly Revenue (KES), Overdue Invoices
- Occupancy gauge or donut chart (occupied vs vacant)
- "Leases ending soon" table: unit, tenant, end date, days remaining — amber if < 30 days, red if < 7
- "Top performing properties" table: name, net income this month
- Quick-action buttons: Add Property, View Applications, View Maintenance

Design: data-dense, professional. Dark sidebar nav, white content area.
KPI cards use large numbers with subtle trend indicators. Serious financial dashboard aesthetic.
```

---

### 7. Landlord — properties & units

```
/frontend-design

Backend: Django REST API at http://localhost:8000
Auth: All protected requests need header → Authorization: Token <token>
Token source: POST /api/auth/login/ returns { "key": "<token>" }
Store token in localStorage under key "treehouse_token"
Roles: Admin, Landlord, Agent, Tenant, Artisan, MovingCompany
Role is a numeric ID on the user object — resolved from GET /api/auth/roles/
On 401 response: clear token and redirect to /login
On 403 response: show an inline "You don't have permission" message — do not redirect

Build the property management section for Landlords. RoleGuard allowed=["Landlord", "Admin"].

Property list at /landlord/properties:
  GET /api/property/properties/
  Response: [{ id, name, address, city, property_type, unit_count }]

  POST /api/property/properties/
  Body: { name, address, city, property_type, description }
  property_type choices: apartment, house, commercial, land, other

Property detail at /landlord/properties/[id]:
  GET /api/property/properties/<id>/ → full property object
  GET /api/property/properties/<id>/units/ → [{ id, unit_number, bedrooms, bathrooms, rent_amount, is_occupied, is_public }]
  GET /api/property/properties/<id>/agents/ → [{ id, agent: { username, first_name }, appointed_at }]

Unit creation at /landlord/properties/[id]/units/new:
  POST /api/property/properties/<id>/units/
  Body: { unit_number, bedrooms, bathrooms, rent_amount, amenities, parking, description, is_public }

Unit detail at /landlord/properties/[id]/units/[unitId]:
  GET /api/property/units/<id>/
  PATCH /api/property/units/<id>/ — edit fields
  GET /api/property/units/<id>/lease/ — current lease
  GET /api/property/units/<id>/images/ — images

Design: properties list is a card grid. Property detail uses a tabbed layout:
  Overview | Units | Agents | Financial | Reviews
Unit table shows occupancy status as a coloured dot. "Add Unit" is a slide-in drawer form.
```

---

### 8. Landlord — application approval

```
/frontend-design

Backend: Django REST API at http://localhost:8000
Auth: All protected requests need header → Authorization: Token <token>
Token source: POST /api/auth/login/ returns { "key": "<token>" }
Store token in localStorage under key "treehouse_token"
Roles: Admin, Landlord, Agent, Tenant, Artisan, MovingCompany
Role is a numeric ID on the user object — resolved from GET /api/auth/roles/
On 401 response: clear token and redirect to /login
On 403 response: show an inline "You don't have permission" message — do not redirect

Build the application review page at /landlord/applications. RoleGuard allowed=["Landlord", "Admin"].

List:
  GET /api/property/applications/
  Response: [{ id, unit: { unit_number, property: { name } },
               applicant: { username, first_name, last_name },
               status, message, created_at }]

Default filter to status=pending. Allow tab switching: All | Pending | Approved | Rejected.

Approve (auto-creates lease):
  PUT /api/property/applications/<id>/
  Body: { status: "approved", start_date: "2026-04-01", rent_amount: 25000 }

Reject:
  PUT /api/property/applications/<id>/
  Body: { status: "rejected" }

Rules:
- Approving opens a confirmation modal asking for start_date (date picker) and rent_amount (number input)
- After approval, show toast: "Lease created for <first_name last_name>"
- Rejected applications are greyed out and cannot be actioned again

Design: table view with applicant avatar (initials fallback), unit name, application date,
message preview, and action buttons. Approve is green, Reject is outlined red.
Approval modal is focused and clear — date picker and amount field, large confirm button.
```

---

### 9. Maintenance

```
/frontend-design

Backend: Django REST API at http://localhost:8000
Auth: All protected requests need header → Authorization: Token <token>
Token source: POST /api/auth/login/ returns { "key": "<token>" }
Store token in localStorage under key "treehouse_token"
Roles: Admin, Landlord, Agent, Tenant, Artisan, MovingCompany
Role is a numeric ID on the user object — resolved from GET /api/auth/roles/
On 401 response: clear token and redirect to /login
On 403 response: show an inline "You don't have permission" message — do not redirect

Build the maintenance section. Behaviour varies by role — use useRole() to conditionally render.

List at /maintenance:
  GET /api/maintenance/requests/
  Response: [{ id, title, category, priority, status, created_at,
               unit: { unit_number, property: { name } } }]

  Tenant/Landlord see their own. Artisan sees open requests matching their trade. Agent sees assigned property requests.

Submit new request (Tenant or Landlord only):
  POST /api/maintenance/requests/
  Body: { unit: <id>, title, description, category, priority }
  category choices: plumbing, electrical, structural, appliance, other
  priority choices: low, medium, high, emergency

Status badge colours:
  submitted=blue, open=amber, assigned=purple, in_progress=orange, completed=green,
  cancelled=grey, rejected=red

Detail page at /maintenance/[id] — tabbed:
  Info tab: title, description, property, unit, priority, status, submitted by, dates
  Bids tab:
    GET /api/maintenance/requests/<id>/bids/ →
      [{ id, artisan_name, artisan_rating, artisan_trade, artisan_job_count,
         proposed_price, message, status }]
    Artisan: POST bids/ with { proposed_price, message }
    Submitter: PUT bids/<id>/ with { status: "accepted" } or { status: "rejected" }
  Timeline tab:
    GET /api/maintenance/requests/<id>/timeline/
    Response: [{ event_type, description, actor, created_at }]
  Notes tab: GET/POST /api/maintenance/requests/<id>/notes/

Design: list is a Kanban-style board (columns by status) on desktop, list view on mobile.
Emergency priority items have a red left border. Detail page feels like a work ticket (Jira-inspired).
Bids are displayed as cards with the artisan name, price, and accept/reject buttons.
```

---

### 10. Messaging

```
/frontend-design

Backend: Django REST API at http://localhost:8000
Auth: All protected requests need header → Authorization: Token <token>
Token source: POST /api/auth/login/ returns { "key": "<token>" }
Store token in localStorage under key "treehouse_token"
Roles: Admin, Landlord, Agent, Tenant, Artisan, MovingCompany
Role is a numeric ID on the user object — resolved from GET /api/auth/roles/
On 401 response: clear token and redirect to /login
On 403 response: show an inline "You don't have permission" message — do not redirect

Build the messaging section at /messages. Available to all roles.

Participant picker (who can I message — role-scoped; not the admin users list):
  GET /api/messaging/participants/?search=&property=&limit=20
  Response: { results: [{ user_id, full_name, email, phone, role, avatar_url, is_active }] }

Conversation list:
  GET /api/messaging/conversations/
  Response items include: id, property, subject, created_by, created_at,
    participants[] (each has user_id, user [deprecated alias of user_id], is_self, full_name, email, phone, role, …),
    primary_recipient (object or null — first "other" participant summary),
    unread_count,
    last_message (null or { id, sender, sender_id, sender_username, sender_name, body, created_at })

Create conversation:
  POST /api/messaging/conversations/
  Body: { subject, property: <id or null>, participant_ids: [<user_pk>, ...] }

Messages:
  GET /api/messaging/conversations/<id>/messages/
  Response: [{ id, sender, sender_name, body, created_at }]

  POST /api/messaging/conversations/<id>/messages/
  Body: { body: "..." }

Mark read on open:
  POST /api/messaging/conversations/<id>/read/

Polling: fetch new messages every 10 seconds while conversation is open.

Design: two-panel layout (conversations left, thread right) — familiar messaging UI.
Own messages right-aligned with teal bubble, others left-aligned with grey bubble.
Unread conversations bold in the list with a count badge.
Timestamp shown as relative time ("2 min ago") — use date-fns.
```

---

### 11. Notifications bell

```
/frontend-design

Backend: Django REST API at http://localhost:8000
Auth: All protected requests need header → Authorization: Token <token>
Token source: POST /api/auth/login/ returns { "key": "<token>" }
Store token in localStorage under key "treehouse_token"
Roles: Admin, Landlord, Agent, Tenant, Artisan, MovingCompany
Role is a numeric ID on the user object — resolved from GET /api/auth/roles/
On 401 response: clear token and redirect to /login
On 403 response: show an inline "You don't have permission" message — do not redirect

Build a notification bell component for the main navigation. Available to all roles.

Unread count (poll every 30s):
  GET /api/notifications/?unread=true → use array length as badge number

Dropdown (last 10):
  GET /api/notifications/
  Response: [{ id, title, body, action_url, is_read, notification_type, created_at }]

Mark single read:
  POST /api/notifications/<id>/read/

Mark all read:
  POST /api/notifications/read-all/

Type icons:
  payment=💳  maintenance=🔧  lease=📄  dispute=⚖️
  message=💬  application=📋  new_listing=🏠  moving=🚛  account=👤

Full page at /notifications: all notifications, infinite scroll, mark-all-read button.

Design: bell icon in the nav with a red badge count. Dropdown slides down on click,
showing notification rows with icon, title, body snippet, relative time.
Unread rows have a subtle blue-left border. Clicking navigates to action_url.
```

---

### 12. Admin panel

```
/frontend-design

Backend: Django REST API at http://localhost:8000
Auth: All protected requests need header → Authorization: Token <token>
Token source: POST /api/auth/login/ returns { "key": "<token>" }
Store token in localStorage under key "treehouse_token"
Roles: Admin, Landlord, Agent, Tenant, Artisan, MovingCompany
Role is a numeric ID on the user object — resolved from GET /api/auth/roles/
On 401 response: clear token and redirect to /login
On 403 response: show an inline "You don't have permission" message — do not redirect

Build the admin panel at /admin. RoleGuard allowed=["Admin"].

System overview:
  GET /api/dashboard/admin/
  Response:
  {
    "users": { "total", "by_role": { "Landlord": n, "Tenant": n, ... }, "new_last_30_days": n },
    "properties": { "total", "units", "occupied", "occupancy_rate" },
    "billing": { "monthly_revenue", "outstanding", "overdue_count" },
    "maintenance": { "submitted", "open", "assigned", "in_progress", "completed_this_month" },
    "disputes": { "open", "under_review" },
    "moving": { "active_companies", "pending_bookings", "completed_this_month" }
  }

System health:
  GET /api/monitoring/dashboard/
  Response: { health_status: "healthy"|"warning"|"critical", active_alert_counts: { critical, warning, info },
              latest_metrics: { overdue_invoice_count, monthly_revenue, occupancy_rate, ... },
              top_active_alerts: [...] }

User management at /admin/users:
  GET /api/dashboard/admin/users/?role=&search=&is_active=
  Response: [{ pk, username, email, role: { name }, is_active, date_joined }]

  Change role:
    PUT /api/dashboard/admin/users/<pk>/
    Body: { role: <role_id> }

Build:
- KPI grid: total users, properties, monthly revenue, occupancy rate, open disputes, pending bookings
- Users by role: pie or donut chart
- Health banner: green/amber/red based on health_status; lists active alert count per severity
- User table: filterable by role and search; role change dropdown inline; deactivate toggle

Design: dark admin aesthetic — deep navy or charcoal sidebar, white cards.
Health banner spans full width at the top — impossible to miss a critical status.
Dense data tables with hover states. Role badges use distinct colours per role.
```

---

### 13. Admin — user impersonation

```
/frontend-design

Backend: Django REST API at http://localhost:8000
Auth: All protected requests need header → Authorization: Token <token>
Token source: POST /api/auth/login/ returns { "key": "<token>" }
Store token in localStorage under key "treehouse_token"
Roles: Admin, Landlord, Agent, Tenant, Artisan, MovingCompany
Role is a numeric ID on the user object — resolved from GET /api/auth/roles/
On 401 response: clear token and redirect to /login
On 403 response: show an inline "You don't have permission" message — do not redirect

Add impersonation to the admin user detail page at /admin/users/[id].

To impersonate, inject this header on every Axios request:
  X-Impersonate-User: <target_user_pk>

"Impersonate" button on the user detail page:
- Stores target pk in sessionStorage key "impersonating_pk"
- Adds the header to the shared Axios instance interceptor
- Redirects to the target user's role home page

While impersonating:
- Show a persistent orange banner fixed at the top of every page:
  "Impersonating <username> (<role>) — your actions are logged  [Exit impersonation]"
- Exit: remove sessionStorage key, remove Axios header, redirect to /admin/users/[id]

Impersonation log at /admin/impersonation-logs:
  GET /api/monitoring/impersonation-logs/?hours=72
  Response: [{ id, admin_username, target_username, target_role, path, method, timestamp }]

Design: the impersonation banner must be visually unmistakeable — bold orange, fixed position,
never scrolls away. Log is a simple sortable table with method badges (GET=blue, POST=green,
PATCH=amber, DELETE=red).
```

---

## Reusable fragments — append to any prompt

### Error handling

```
Handle all API errors:
- 400 → map field errors to form fields inline; show a summary toast if no field matches
- 401 → clear token, redirect to /login
- 403 → show inline "You don't have permission to do this" — do not redirect
- 404 → show a full-page "Not found" with a back button
- 5xx → show a "Something went wrong — try again" toast with a retry button
```

### Loading & empty states

```
Every data-fetching view must handle:
- Loading → skeleton matching the shape of loaded content (not a spinner)
- Error → error card with message and retry button
- Empty → empty state with a relevant illustration, message, and primary CTA
```

### Forms

```
All forms:
- Inline validation errors under each field (not a summary at the top)
- Submit button disabled and shows a spinner while request is in flight
- Success toast on completion
- Reset form after successful submission
- Map 400 response field errors back to the relevant input
```

### Pagination

```
All list views:
- Query params: page (1-indexed), page_size=20
- Summary text: "Showing 1–20 of 143 results"
- Previous / Next buttons; disabled at boundaries
```

### Dates

```
Use date-fns for all formatting:
- Dates only: "12 Jan 2026"
- Date + time: "12 Jan 2026, 14:32"
- Relative (feeds, messages): "2 hours ago", "yesterday", "just now"
```

---

## Tips for the frontend-design plugin

- **One screen per prompt.** The plugin produces better output on focused prompts. Don't ask for the whole app at once.
- **Paste the exact JSON shape.** Copy the response from `http://localhost:8000/api/docs/` and paste it directly — the plugin uses exact field names, not guesses.
- **Include the prime block every time.** The plugin does not retain context across sessions.
- **Specify what changes per role explicitly.** e.g. "Artisan sees a 'Place Bid' button, Tenant sees 'Accept/Reject' buttons, everyone else sees read-only bids."
- **Add design intent at the end of every prompt.** One or two sentences on tone, colour mood, or layout approach steers the plugin toward a distinctive result rather than a generic one.

