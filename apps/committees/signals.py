"""Signal handlers for committees app."""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from apps.committees.models import Committee, Membership


@receiver(post_save, sender=Membership)
def sync_ba_membership_on_create(sender, instance, created, **kwargs):
    """
    Automatically add member to Betriebsausschuss when they get auto-role in BR.
    
    When a user becomes CHAIR or VICE_CHAIR (or any role with auto_include_in_ba)
    in the main committee, they are automatically added to the Betriebsausschuss.
    
    According to § 27 BetrVG.
    """
    # Only for newly created memberships
    if not created:
        return
    
    # Only for MAIN committee memberships
    if instance.committee.committee_type != 'MAIN':
        return
    
    # Only for roles with auto_include_in_ba
    if not instance.role or not instance.role.auto_include_in_ba:
        return
    
    # Find Betriebsausschuss for this committee
    try:
        ba = Committee.objects.get(
            parent=instance.committee,
            committee_type='COMMITTEE',
            auto_composition_enabled=True,
            deleted_at__isnull=True
        )
    except Committee.DoesNotExist:
        # No BA exists or not auto-composition enabled
        return
    except Committee.MultipleObjectsReturned:
        # Should not happen due to validation, but handle it
        ba = Committee.objects.filter(
            parent=instance.committee,
            committee_type='COMMITTEE',
            auto_composition_enabled=True,
            deleted_at__isnull=True
        ).first()
    
    # Check if user already member of BA
    existing = Membership.objects.filter(
        user=instance.user,
        committee=ba,
        deleted_at__isnull=True
    ).exists()
    
    if not existing:
        # Create BA membership with same role
        Membership.objects.create(
            user=instance.user,
            committee=ba,
            role=instance.role,
            member_type='REGULAR',
            start_date=instance.start_date,
            is_active=True
        )


@receiver(post_delete, sender=Membership)
def sync_ba_membership_on_delete(sender, instance, **kwargs):
    """
    Remove member from BA when they are removed from BR with auto-role.
    
    When a user loses CHAIR or VICE_CHAIR role in main committee,
    they are automatically removed from Betriebsausschuss.
    """
    # Only for MAIN committee memberships
    if instance.committee.committee_type != 'MAIN':
        return
    
    # Only for roles with auto_include_in_ba
    if not instance.role or not instance.role.auto_include_in_ba:
        return
    
    # Find Betriebsausschuss
    try:
        ba = Committee.objects.get(
            parent=instance.committee,
            committee_type='COMMITTEE',
            auto_composition_enabled=True,
            deleted_at__isnull=True
        )
    except (Committee.DoesNotExist, Committee.MultipleObjectsReturned):
        return
    
    # Remove from BA
    Membership.objects.filter(
        user=instance.user,
        committee=ba,
        deleted_at__isnull=True
    ).delete()


@receiver(post_save, sender=Committee)
def auto_enable_ba_composition(sender, instance, created, **kwargs):
    """
    Automatically enable auto_composition for newly created Betriebsausschuss.
    
    When a COMMITTEE is created, automatically set auto_composition_enabled=True.
    """
    if created and instance.committee_type == 'COMMITTEE':
        if not instance.auto_composition_enabled:
            instance.auto_composition_enabled = True
            instance.save(update_fields=['auto_composition_enabled'])


@receiver(post_save, sender=Committee)
def sync_ba_on_creation(sender, instance, created, **kwargs):
    """
    Sync BA members when BA is created.
    
    When a new Betriebsausschuss is created, automatically populate it
    with members from parent BR who have auto_include_in_ba roles.
    """
    if created and instance.committee_type == 'COMMITTEE' and instance.auto_composition_enabled:
        # Sync auto members from parent BR
        instance.sync_auto_ba_members()
