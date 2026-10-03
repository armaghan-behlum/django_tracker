"""
Create the two data-access groups (idempotent). See DATA_ACCESS.md.

- "Data coordinators": view the de-identified surface only.
- "Follow-up staff": view full records of follow-up-consented
  reports (the admin queryset enforces the consent filter).
"""

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


GROUPS = {
    "Data coordinators": [
        ("tracker", "view_deidentifiedreport"),
    ],
    "Follow-up staff": [
        ("tracker", "view_incidentreport"),
        ("tracker", "view_affectedperson"),
        ("tracker", "view_affectedpersondemographics"),
        ("tracker", "view_californiadetails"),
        ("tracker", "view_schoolincident"),
        ("tracker", "view_formalschoolcomplaint"),
        ("tracker", "view_reportoptionselection"),
        ("tracker", "view_reportreferral"),
        ("tracker", "view_reportattachment"),
        ("tracker", "view_ucpfiling"),
    ],
}


class Command(BaseCommand):
    help = "Create/refresh the data-access groups (idempotent)."

    def handle(self, *args, **options):
        for name, permissions in GROUPS.items():
            group, created = Group.objects.get_or_create(name=name)

            permission_objects = []

            for app_label, codename in permissions:
                try:
                    permission_objects.append(
                        Permission.objects.get(
                            content_type__app_label=app_label,
                            codename=codename,
                        )
                    )
                except Permission.DoesNotExist:
                    self.stderr.write(
                        f"Missing permission {app_label}.{codename} "
                        "(run migrate first)"
                    )

            group.permissions.set(permission_objects)

            self.stdout.write(
                f"{'Created' if created else 'Updated'} group "
                f"\"{name}\" with {len(permission_objects)} "
                "permissions."
            )
