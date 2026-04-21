from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'authentication'

    def ready(self):
        from treeHouse.django_compat import patch_base_context_copy_for_python_314

        patch_base_context_copy_for_python_314()
