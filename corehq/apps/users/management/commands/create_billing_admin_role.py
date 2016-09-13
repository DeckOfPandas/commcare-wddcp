from django.core.management.base import BaseCommand
from corehq.apps.domain.models import Domain
from corehq.apps.users.models import UserRole, UserRolePresets


class Command(BaseCommand):
    args = ""
    help = ("Adds the billing admin preset role to all existing domains")

    def handle(self, *args, **options):
        for domain in Domain.get_all():
            UserRole.get_or_create_with_permissions(
                domain.name,
                UserRolePresets.get_permissions(UserRolePresets.BILLING_ADMIN),
                UserRolePresets.BILLING_ADMIN
            )
