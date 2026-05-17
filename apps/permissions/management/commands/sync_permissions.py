from django.core.management.base import BaseCommand

from apps.permissions.models import Permission
from config.rbac.enums import PermissionEnum
from config.rbac.registry import PERMISSION_REGISTRY

from apps.permissions.management.commands import SyncResult


class Command(BaseCommand):
    help = "Synchronisiert Permissions aus der RBAC-Registry mit der Datenbank"

    def handle(self, *args, **kwargs) -> None:
        result = self._sync_all_permissions()
        self._write_report(result)

    def _sync_all_permissions(self) -> SyncResult:
        result = SyncResult()
        for permission in PERMISSION_REGISTRY.values():
            self._sync_single_permission(permission, result)
        return result

    def _sync_single_permission(self, permission: PermissionEnum, result: SyncResult) -> None:
        existing = Permission.objects.filter(key=permission.value).first()

        obj, created = Permission.objects.update_or_create(
            key=permission.value,
            defaults={
                "description": permission.description,
                "category": permission.category,
            },
        )

        if created:
            result.created.append(obj)
        elif self._is_unchanged(existing, permission):
            result.skipped.append(obj)
        else:
            result.updated.append(obj)

    @staticmethod
    def _is_unchanged(existing: Permission | None, permission: PermissionEnum) -> bool:
        return (
                existing is not None
                and existing.description == permission.description
                and existing.category == permission.category
        )

    def _write_report(self, result: SyncResult) -> None:
        self._write_section(
            result.created,
            style=self.style.SUCCESS,
            header="✅ Neu erstellt",
            line_fn=lambda p: f"   + [{p.category}] {p.key} – {p.description}",
        )
        self._write_section(
            result.updated,
            style=self.style.WARNING,
            header="✏️  Aktualisiert",
            line_fn=lambda p: f"   ~ [{p.category}] {p.key} – {p.description}",
        )
        self._write_section(
            result.skipped,
            style=self.style.HTTP_INFO,
            header="⏭️  Unverändert",
            line_fn=lambda p: f"   = [{p.category}] {p.key}",
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
                f"\nSync abgeschlossen: {result.total} Permissions verarbeitet "
                f"({len(result.created)} neu, {len(result.updated)} aktualisiert, "
                f"{len(result.skipped)} unverändert)"
            )
        )
