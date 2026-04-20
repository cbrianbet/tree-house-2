"use client";

export { NOTIF_GROUPS } from "../../../../lib/notification-matrix";

import { useCallback, useEffect, useState } from "react";
import type { NotificationPreferences } from "../../../../types/api";
import { NOTIF_GROUPS } from "../../../../lib/notification-matrix";
import {
  getNotificationPreferences,
  updateNotificationPreferences,
} from "../../../../lib/api/auth";

export default function TenantProfilePage() {
  const [prefs, setPrefs] = useState<NotificationPreferences | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getNotificationPreferences();
      setPrefs(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load preferences");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const toggleEmail = async (key: keyof NotificationPreferences, value: boolean) => {
    if (!prefs) return;
    const next = { ...prefs, [key]: value };
    setPrefs(next);
    try {
      const saved = await updateNotificationPreferences({ [key]: value });
      setPrefs(saved);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save");
      void load();
    }
  };

  if (loading || !prefs) {
    return <div>Loading notification preferences…</div>;
  }

  return (
    <div>
      {error ? <p role="alert">{error}</p> : null}
      <section>
        <h2>Email notifications</h2>
        <label>
          <input
            type="checkbox"
            checked={prefs.email_notifications}
            onChange={(e) => void toggleEmail("email_notifications", e.target.checked)}
          />{" "}
          Enable email notifications
        </label>
      </section>
      {NOTIF_GROUPS.map((group) => (
        <section key={group.id}>
          <h3>{group.title}</h3>
          <table>
            <thead>
              <tr>
                <th>Event</th>
                <th>Email</th>
                <th>Push</th>
                <th>SMS</th>
              </tr>
            </thead>
            <tbody>
              {group.rows.map((row) => (
                <tr key={row.id}>
                  <td>{row.label}</td>
                  <td>
                    <input
                      type="checkbox"
                      disabled={!prefs.email_notifications}
                      checked={prefs[row.emailKey]}
                      onChange={(e) => void toggleEmail(row.emailKey, e.target.checked)}
                    />
                  </td>
                  <td>
                    <input type="checkbox" disabled aria-disabled title="Push not available yet" />
                  </td>
                  <td>
                    <input type="checkbox" disabled aria-disabled title="SMS not available yet" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ))}
    </div>
  );
}
