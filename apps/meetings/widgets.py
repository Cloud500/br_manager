"""Custom widgets for meetings app."""

from django import forms
from django.forms.widgets import Select


class MemberSelectWidget(Select):
    """Custom select widget for committee members with card-style dropdown."""
    
    template_name = 'meetings/widgets/member_select.html'
    option_template_name = 'meetings/widgets/member_select_option.html'
    
    def __init__(self, attrs=None, choices=(), committee=None):
        default_attrs = {'class': 'form-select member-select'}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs, choices=choices)
        self.committee = committee
        self.committee_id = None
    
    def optgroups(self, name, value, attrs=None):
        """Return a list of optgroups for this widget with enriched membership data."""
        groups = super().optgroups(name, value, attrs)
        
        # Enrich each option with membership data
        for group in groups:
            group_name, options, group_index = group
            for option in options:
                if option['value']:
                    self._enrich_option_with_membership(option)
        
        return groups
    
    def _enrich_option_with_membership(self, option):
        """Add membership information to option attrs."""
        try:
            from apps.accounts.models import User
            from apps.committees.models import Membership
            
            user_id = option['value']
            if not user_id:
                return
            
            user = User.objects.select_related('profile').get(pk=user_id)
            
            # Update label to only show name (without email)
            option['label'] = f"{user.first_name} {user.last_name}"
            
            # Get membership information if we have a committee context
            if self.committee_id:
                try:
                    membership = Membership.objects.select_related('role').get(
                        user=user,
                        committee_id=self.committee_id,
                        is_active=True
                    )
                    
                    # Add membership data to attrs
                    if membership and membership.role:
                        option['attrs']['data_role'] = membership.role.name
                        option['attrs']['data_member_type'] = membership.get_member_type_display()
                        option['attrs']['data_list'] = membership.election_list_name or ''
                        option['attrs']['data_position'] = str(membership.election_list_position) if membership.election_list_position else ''
                        
                except Membership.DoesNotExist:
                    pass
        
        except Exception as e:
            import sys
            print(f"Error enriching option: {e}", file=sys.stderr)
    
    def set_committee_id(self, committee_id):
        """Set committee ID for membership lookups."""
        self.committee_id = committee_id
