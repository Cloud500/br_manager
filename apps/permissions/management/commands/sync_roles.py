from django.core.management.base import BaseCommand

from apps.permissions.models import Role, Permission
from config.rbac.registry import ROLE_REGISTRY
from config.rbac.enums import RoleEnum

from apps.permissions.management.commands import SyncResult


class Command(BaseCommand):
    help = "Synchronisiert Rollen aus der RBAC Registry"

    def handle(self, *args, **kwargs) -> None:
        result = self._sync_all_roles()
        self._write_report(result)

    def _sync_all_roles(self) -> SyncResult:
        result = SyncResult()
        for role in ROLE_REGISTRY.values():
            self._sync_single_role(role, result)
        return result

    def _sync_single_role(self, role_definition: RoleEnum, result: SyncResult) -> None:
        existing = Role.objects.filter(name=role_definition.value).first()

        role, created = Role.objects.update_or_create(
            name=role_definition.value,
            defaults={
                "description": role_definition.description,
                "system": role_definition.system,
            },
        )

        permissions = Permission.objects.filter(
            key__in=[p.key for p in role_definition.permissions]
        )

        if created or role_definition.system:
            role.permissions.set(permissions)

        if created:
            result.created.append(role)
        elif self._is_unchanged(existing, role_definition):
            result.skipped.append(role)
        else:
            result.updated.append(role)

    @staticmethod
    def _is_unchanged(existing: Role | None, role_definition: RoleEnum) -> bool:
        if existing is None:
            return False

        existing_permissions = set(existing.permissions.values_list("key", flat=True))
        new_permissions = {p.key for p in role_definition.permissions}

        return (
                existing.description == role_definition.description
                and existing.system == role_definition.system
                and existing_permissions == new_permissions
        )

    def _write_report(self, result: SyncResult) -> None:
        self._write_section(
            result.created,
            style=self.style.SUCCESS,
            header="✅ Neu erstellt",
            line_fn=lambda r: f"   + {r.name}",
        )
        self._write_section(
            result.updated,
            style=self.style.WARNING,
            header="✏️  Aktualisiert",
            line_fn=lambda r: f"   ~ {r.name}",
        )
        self._write_section(
            result.skipped,
            style=self.style.HTTP_INFO,
            header="⏭️  Unverändert",
            line_fn=lambda r: f"   = {r.name}",
        )
        self._write_summary(result)

    def _write_section(self, items: list, style, header: str, line_fn) -> None:
        if not items:
            return
        self.stdout.write(style(f"\n{header} ({len(items)}):"))
        for item in items:
            self.stdout.write(line_fn(item))

    def _write_summary(self, result: SyncResult) -> None:
        self.stdout.write(
            self.style.SUCCESS(
                f"\nSync abgeschlossen: {result.total} Rollen verarbeitet "
                f"({len(result.created)} neu, {len(result.updated)} aktualisiert, "
                f"{len(result.skipped)} unverändert)"
            )
        )
