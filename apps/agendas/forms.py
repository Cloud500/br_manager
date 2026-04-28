"""Forms for agendas app."""

from django import forms

from .models import AgendaItemRegular


class AgendaItemRegularForm(forms.ModelForm):
    """
    Form for creating and editing regular agenda items.
    
    Fields:
        title: Item title
        description: Optional detailed description
        parent: Optional parent item for hierarchical structure
    """
    
    class Meta:
        model = AgendaItemRegular
        fields = ['title', 'description', 'parent']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'z.B. Begrüßung und Feststellung der Beschlussfähigkeit'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Optional: Ausführliche Beschreibung des Tagesordnungspunktes'
            }),
            'parent': forms.Select(attrs={
                'class': 'form-select'
            }),
        }
        labels = {
            'title': 'Titel',
            'description': 'Beschreibung',
            'parent': 'Übergeordneter TOP',
        }
        help_texts = {
            'title': 'Kurztitel des Tagesordnungspunktes',
            'description': 'Optional: Ausführliche Beschreibung',
            'parent': 'Optional: Wählen Sie einen übergeordneten TOP für hierarchische Struktur (z.B. TOP 1.1)',
        }
    
    def __init__(self, *args, agenda=None, **kwargs):
        """
        Initialize form with agenda context.
        
        Filters parent dropdown to show only items from the same agenda.
        
        Args:
            agenda: Agenda instance to filter parent choices
            *args: Positional arguments
            **kwargs: Keyword arguments
        """
        super().__init__(*args, **kwargs)
        
        # Store agenda for later use
        self.agenda = agenda
        
        # Filter parent dropdown to only show items from same agenda
        if agenda:
            self.fields['parent'].queryset = AgendaItemRegular.objects.filter(
                agenda=agenda
            ).order_by('sort_order')
        
        # Add empty option for parent
        self.fields['parent'].empty_label = '(Kein übergeordneter TOP - Hauptebene)'
        
        # Make description not required
        self.fields['description'].required = False
    
    def _post_clean(self):
        """
        Set agenda on instance before model validation.
        
        This ensures the agenda is available during clean() validation.
        """
        # Set agenda before calling super()._post_clean() which triggers model validation
        if self.agenda and not self.instance.pk:
            self.instance.agenda = self.agenda
        
        super()._post_clean()
    
    def save(self, commit=True):
        """
        Save the form instance.
        
        Args:
            commit: Whether to save to database
            
        Returns:
            AgendaItemRegular instance
        """
        instance = super().save(commit=False)
        
        # Ensure agenda is set
        if self.agenda:
            instance.agenda = self.agenda
        
        if commit:
            instance.save()
        
        return instance
