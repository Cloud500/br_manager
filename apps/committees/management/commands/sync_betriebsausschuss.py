"""Management command to synchronize Betriebsausschuss memberships."""

from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.committees.models import Committee
from apps.committees.validators import BetriebsausschussValidator


class Command(BaseCommand):
    """
    Synchronize Betriebsausschuss memberships according to § 27 BetrVG.
    
    This command:
    1. Finds all main committees (BR) with ≥9 members
    2. Ensures a Betriebsausschuss exists for each
    3. Syncs automatic members (CHAIR, VICE_CHAIR, auto-roles)
    4. Reports on BA composition status
    """
    
    help = 'Synchronisiert Betriebsausschuss-Mitgliedschaften gemäß § 27 BetrVG'
    
    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            '--create-missing',
            action='store_true',
            help='Automatisch fehlende Betriebsausschüsse erstellen'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Änderungen nicht durchführen, nur anzeigen'
        )
    
    def handle(self, *args, **options):
        """Execute command."""
        self.stdout.write(self.style.HTTP_INFO('=' * 70))
        self.stdout.write(self.style.HTTP_INFO('  BETRIEBSAUSSCHUSS-SYNCHRONISATION (§ 27 BetrVG)'))
        self.stdout.write(self.style.HTTP_INFO('=' * 70))
        
        dry_run = options.get('dry_run', False)
        create_missing = options.get('create_missing', False)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('  [DRY RUN] Keine Änderungen werden durchgeführt\n'))
        
        # Find all main committees
        main_committees = Committee.objects.filter(
            committee_type='MAIN',
            is_active=True,
            deleted_at__isnull=True
        )
        
        total_br = main_committees.count()
        requires_ba_count = 0
        has_ba_count = 0
        missing_ba_count = 0
        synced_count = 0
        valid_count = 0
        invalid_count = 0
        
        self.stdout.write(f'\n[INFO] Gefundene Betriebsraete: {total_br}\n')
        
        for br in main_committees:
            br_member_count = br.get_active_members().count()
            requires_ba = BetriebsausschussValidator.requires_betriebsausschuss(br_member_count)
            
            self.stdout.write(f'\n[BR] {br.name}')
            self.stdout.write(f'   BR-Mitglieder: {br_member_count}')
            
            if not requires_ba:
                self.stdout.write(self.style.WARNING(f'   Kein BA erforderlich (< 9 Mitglieder)'))
                continue
            
            requires_ba_count += 1
            
            # Check if BA exists
            ba = Committee.objects.filter(
                parent=br,
                committee_type='COMMITTEE',
                deleted_at__isnull=True
            ).first()
            
            if not ba:
                missing_ba_count += 1
                self.stdout.write(self.style.ERROR(f'   [FEHLT] Betriebsausschuss FEHLT!'))
                
                if create_missing and not dry_run:
                    # Create BA
                    required_size = BetriebsausschussValidator.get_total_ba_size(br_member_count)
                    ba = Committee.objects.create(
                        name=f'Betriebsausschuss {br.name}',
                        committee_type='COMMITTEE',
                        parent=br,
                        total_seats=required_size,
                        is_active=True,
                        auto_composition_enabled=True,
                        quorum_type=br.quorum_type
                    )
                    self.stdout.write(self.style.SUCCESS(f'      [OK] Betriebsausschuss erstellt ({required_size} Sitze)'))
                    has_ba_count += 1
                elif create_missing and dry_run:
                    required_size = BetriebsausschussValidator.get_total_ba_size(br_member_count)
                    self.stdout.write(self.style.WARNING(f'      [DRY RUN] Wuerde BA erstellen ({required_size} Sitze)'))
                continue
            
            has_ba_count += 1
            
            # BA exists - check composition
            ba_info = ba.get_ba_size_info()
            is_valid, message = ba.get_ba_composition_status()
            
            self.stdout.write(f'   [OK] Betriebsausschuss: {ba.name}')
            self.stdout.write(f'      Erforderlich: {ba_info["total_size"]} Mitglieder')
            self.stdout.write(f'      Aktuell: {ba_info["current_size"]} Mitglieder')
            self.stdout.write(f'      Automatisch: {ba_info["auto_members"]} (Vorsitz + auto-Rollen)')
            self.stdout.write(f'      Manuell erforderlich: {ba_info["manual_members_required"]}')
            
            if is_valid:
                valid_count += 1
                self.stdout.write(self.style.SUCCESS(f'      [OK] Status: {message}'))
            else:
                invalid_count += 1
                self.stdout.write(self.style.ERROR(f'      [FEHLER] Status: {message}'))
            
            # Sync automatic members
            if ba.auto_composition_enabled:
                if not dry_run:
                    added, skipped = ba.sync_auto_ba_members()
                    if added > 0:
                        synced_count += 1
                        self.stdout.write(self.style.SUCCESS(f'         [SYNC] {added} Mitglied(er) automatisch hinzugefuegt'))
                    if skipped > 0:
                        self.stdout.write(f'         [INFO] {skipped} bereits vorhanden')
                else:
                    self.stdout.write(self.style.WARNING(f'         [DRY RUN] Wuerde Auto-Mitglieder synchronisieren'))
        
        # Summary
        self.stdout.write(f'\n' + '=' * 70)
        self.stdout.write(self.style.HTTP_INFO('  ZUSAMMENFASSUNG'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'  Betriebsraete gesamt: {total_br}')
        self.stdout.write(f'  BA-pflichtig (>=9 Mitglieder): {requires_ba_count}')
        self.stdout.write(f'  BA vorhanden: {has_ba_count}')
        
        if missing_ba_count > 0:
            self.stdout.write(self.style.ERROR(f'  BA FEHLEND: {missing_ba_count}'))
            if not create_missing:
                self.stdout.write(self.style.WARNING('  Verwenden Sie --create-missing zum automatischen Erstellen'))
        
        self.stdout.write(f'  BA korrekt besetzt: {valid_count}')
        
        if invalid_count > 0:
            self.stdout.write(self.style.ERROR(f'  BA NICHT korrekt besetzt: {invalid_count}'))
        
        if synced_count > 0 and not dry_run:
            self.stdout.write(self.style.SUCCESS(f'  Synchronisiert: {synced_count} BA(s)'))
        
        self.stdout.write('')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('  [DRY RUN] Keine Aenderungen durchgefuehrt'))
            self.stdout.write(self.style.WARNING('  Zum Ausfuehren: python manage.py sync_betriebsausschuss'))
        else:
            self.stdout.write(self.style.SUCCESS('  [OK] Synchronisation abgeschlossen'))
