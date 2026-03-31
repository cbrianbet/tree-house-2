from django.db import models
from authentication.models import CustomUser, Role


class RoleChangeLog(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='role_change_logs')
    changed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='role_changes_made')
    old_role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    new_role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, related_name='+')
    changed_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True)

    def __str__(self):
        old = self.old_role.name if self.old_role else 'None'
        new = self.new_role.name if self.new_role else 'None'
        return f"RoleChangeLog({self.user.username}: {old} → {new})"
