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

**`health_status` values:**
- `healthy` — no active (triggered or acknowledged) alerts
- `warning` — at least one active warning-severity alert, no critical
- `critical` — at least one active critical-severity alert

**`latest_metrics`** — only keys with recorded data appear. If `record_metrics` has never run, this object will be empty.

**`trends`** — last 24 hours of data points for `overdue_invoice_count`, `monthly_revenue`, and `occupancy_rate`, in chronological order.

---

### Scheduled Commands

Run on a cron schedule (e.g. every 15 minutes):

```bash
python manage.py record_metrics      # snapshot current platform metrics
python manage.py check_alert_rules   # evaluate rules; fire/auto-resolve alerts
```

`check_alert_rules` fires an in-app notification to all admin users when a new alert is triggered, respecting each admin's `NotificationPreference`.
