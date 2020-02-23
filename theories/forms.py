"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

A web service for sharing opinions and avoiding arguments

@file       theories/forms.py
@brief      A collection of app specific forms
@copyright  GNU Public License, 2018
@authors    Frank Imeson
"""


# *******************************************************************************
# Imports
# *******************************************************************************
import copy

from django import forms
from django.forms import TextInput
from django.contrib.auth.models import AnonymousUser
from reversion.models import Version

from .models import *


# *******************************************************************************
# Defines
# *******************************************************************************

INT_VALUES = {
    "initial":    0,
    "min_value":  0,
    "max_value":  100,
}
TRUE_INPUT_WIDGET = TextInput(attrs={
    "size":         "3",
    "class":        "text-center",
    "style":        "border:1.25px solid gray;",
    "autocomplete": "off",
})
FALSE_INPUT_WIDGET = TextInput(attrs={
    "size":         "3",
    "class":        "text-center",
    "style":        "color:red; border:1.25px solid red;",
    "autocomplete": "off",
})

DETAILS_CHARFEILD = {
    'widget':     forms.Textarea,
    'help_text':  'Information pertaining to the theory that does not make assumptions about its correctness.',
}


# *******************************************************************************
# Forms
# *******************************************************************************

class TheoryForm(forms.ModelForm):
    """Theory form."""

    class Meta:
        """Where the form options are defined."""
        placeholder_text = 'Use this area to provide details of the theory.\n\n'
        placeholder_text += '  - Feel free to dump raw ideas here with the intention of cleaning them up later.\n'
        placeholder_text += '  - Evidence or theories that go towards proving or disproving the theory should\n'
        placeholder_text += '    be provided as evidence, not details.'

        model = TheoryNode
        fields = ('title01', 'title00', 'details')
        labels = {
            'title01': 'True Statement',
            'title00': 'False Statement',
        }
        help_texts = {
            'details': 'Information pertaining to the theory that does not make assumptions about its correctness.',
        }
        widgets = {
            'details': forms.Textarea(attrs={
                'placeholder': placeholder_text,
            }),
            'title01': forms.TextInput(attrs={
                'placeholder': 'New',
            }),
        }

    def __init__(self, *args, **kwargs):
        """Create and populate the theory form. Fields that the user does not
           have permission to change are set as readonly."""

        # setup
        if 'user' in kwargs.keys():
            self.user = kwargs.pop('user')
        else:
            self.user = AnonymousUser
        super().__init__(*args, **kwargs)

        # autosave
        self.old_instance = None
        if self.instance.pk is not None:
            self.old_instance = copy.copy(self.instance)

        # config
        if self.instance.pk is not None:
            self.fields['title01'].required = False
        self.fields['title00'].required = False
        self.fields['details'].required = False

        # permissions
        if self.instance.pk is not None:
            self.fields['title01'].widget.attrs['readonly'] = True
            self.fields['title00'].widget.attrs['readonly'] = True
            self.fields['details'].widget.attrs['readonly'] = True
            if self.user.is_authenticated and not self.instance.is_deleted():
                if self.user.has_perm('theories.change_title', self.instance):
                    self.fields['title01'].widget.attrs['readonly'] = False
                    self.fields['title00'].widget.attrs['readonly'] = False
                if self.user.has_perm('theories.change_details', self.instance):
                    self.fields['details'].widget.attrs['readonly'] = False

    def clean_title01(self):
        """Remove changes done by users without proper permission."""
        if self.instance.pk is None:
            return self.cleaned_data.get('title01')
        elif self.user.has_perm('theories.change_title', self.instance):
            return self.cleaned_data.get('title01')
        else:
            return self.instance.title01

    def clean_title00(self):
        """Remove changes done by users without proper permission."""
        if self.instance.pk is None:
            return self.cleaned_data.get('title00')
        elif self.user.has_perm('theories.change_title', self.instance):
            return self.cleaned_data.get('title00')
        else:
            return self.instance.title00

    def clean_details(self):
        """Remove changes done by users without proper permission."""
        if self.instance.pk is None:
            return self.cleaned_data.get('details')
        elif self.user.has_perm('theories.change_details', self.instance):
            return self.cleaned_data.get('details')
        else:
            return self.instance.details

    def get_verb(self):
        if hasattr(self, 'action_verb'):
            return self.action_verb
        else:
            return None

    def save(self, commit=True):
        """Sets node_type to THEORY."""
        created = self.instance.pk is None
        theory = super().save(commit=False)

        # populate data
        theory.node_type = TheoryNode.TYPE.THEORY
        if created and self.user is not None:
            self.created_by = self.user

        # action verb
        if created:
            self.action_verb = 'Created'
        else:
            self.action_verb = ''
            if ('title00' in self.changed_data or 'title01' in self.changed_data):
                self.action_verb += 'Title & '
            if 'details' in self.changed_data:
                self.action_verb += 'Details'
            self.action_verb = self.action_verb.strip(' & ')

        # save
        if commit:
            if self.old_instance is not None:
                self.old_instance.autosave(self.user)
            theory.save(self.user)
        return theory


class EvidenceForm(forms.ModelForm):
    verifiable = forms.BooleanField(initial=False)

    class Meta:
        """Where the form options are defined."""
        placeholder_text = 'Use this area to provide details of the evidence.\n\n'
        placeholder_text += '  - Feel free to dump raw ideas here with the intention of cleaning them up later.\n'
        placeholder_text += '  - Evidence that could be interpreted as incorrect should either be:\n'
        placeholder_text += '      a) non-verifiable or\n'
        placeholder_text += '      b) a sub-theory.'

        model = TheoryNode
        fields = ('title01', 'details', 'verifiable')
        labels = {
            'title01':    'Statement',
            'verifiable': 'Is this verifiable?',
        }
        help_texts = {
            'details':    'Information pertaining to the theory that does not make assumptions about its correctness.',
        }
        widgets = {
            'details': forms.Textarea(attrs={
                'placeholder': placeholder_text,
            }),
            'title01': forms.TextInput(attrs={
                'placeholder': 'New',
            }),
        }

    def __init__(self, *args, **kwargs):
        """Create and populate the theory form. Fields that the user does not
           have permission to change are set as readonly. Additionally, evidence
           nodes do not utilize the title00 field."""

        # setup
        if 'user' in kwargs.keys():
            # Needs to come before the call to super.
            self.user = kwargs.pop('user')
        else:
            # Needs to come before self.fields.
            self.user = AnonymousUser
        super().__init__(*args, **kwargs)

        # autosave
        self.old_instance = None
        if self.instance.pk is not None:
            self.old_instance = copy.copy(self.instance)

        # config
        self.fields['details'].required = False
        self.fields['verifiable'].required = False

        # intial data
        if self.instance.pk and self.instance.node_type == TheoryNode.TYPE.FACT:
            self.fields['verifiable'].initial = True

        # permissions
        if self.instance.pk is not None:
            self.fields['title01'].widget.attrs['readonly'] = True
            self.fields['details'].widget.attrs['readonly'] = True
            self.fields['verifiable'].widget.attrs['readonly'] = True
            if self.user.is_authenticated and not self.instance.is_deleted():
                if self.user.has_perm('theories.change_title', self.instance):
                    self.fields['title01'].widget.attrs['readonly'] = False
                    self.fields['verifiable'].widget.attrs['readonly'] = False
                if self.user.has_perm('theories.change_details', self.instance):
                    self.fields['details'].widget.attrs['readonly'] = False

    def clean_title01(self):
        """Remove changes done by users without proper permission."""
        if self.instance.pk is None:
            return self.cleaned_data.get('title01')
        elif self.user.has_perm('theories.change_title', self.instance):
            return self.cleaned_data.get('title01')
        else:
            return self.instance.title01

    def clean_details(self):
        """Remove changes done by users without proper permission."""
        if self.instance.pk is None:
            return self.cleaned_data.get('details')
        elif self.user.has_perm('theories.change_details', self.instance):
            return self.cleaned_data.get('details')
        else:
            return self.instance.details

    def clean_verifiable(self):
        """Remove changes done by users without proper permission."""
        if self.instance.pk is None:
            return self.cleaned_data.get('verifiable')
        elif self.user.has_perm('theories.change_title', self.instance):
            return self.cleaned_data.get('verifiable')
        else:
            return self.instance.node_type == TheoryNode.TYPE.FACT

    def get_verb(self):
        if hasattr(self, 'action_verb'):
            return self.action_verb
        else:
            return None

    def save(self, commit=True):
        """Sets node_type to EVIDENCE (optinally, verifiable)."""
        # setup
        created = self.instance.pk is None
        evidence = super().save(commit=False)

        # populate data
        if self.cleaned_data['verifiable']:
            evidence.node_type = TheoryNode.TYPE.FACT
        else:
            evidence.node_type = TheoryNode.TYPE.EVIDENCE
        if created and self.user is not None:
            self.created_by = self.user

        # action verb
        if created:
            self.action_verb = 'Created'
        else:
            self.action_verb = ''
            if 'title01' in self.changed_data:
                self.action_verb += 'Title & '
            if 'details' in self.changed_data:
                self.action_verb += 'Details'
            self.action_verb = self.action_verb.strip(' & ')

        # save
        if commit:
            if self.old_instance is not None:
                self.old_instance.autosave(self.user)
            evidence.save(self.user)
        return evidence


class CategoryForm(forms.ModelForm):
    """A form for choosing membership, not creating a category."""

    # non-model fields
    member = forms.BooleanField(initial=False)

    class Meta:
        """Where the form options are defined."""
        model = Category
        fields = ('member', 'title')
        labels = {
            'title':    '',
            'member':   '',
        }

    def __init__(self, *args, **kwargs):
        """Create and populate the form."""
        super().__init__(*args, **kwargs)
        self.fields['member'].required = False
        self.fields['title'].required = False


class SelectTheoryNodeForm(forms.ModelForm):
    """A form for slecting theory nodes."""

    # non-model fields
    select = forms.BooleanField(initial=False)

    class Meta:
        """Where the form options are defined."""
        model = TheoryNode
        fields = ('select',)

    def __init__(self, *args, **kwargs):
        # setup
        if 'user' in kwargs.keys():
            self.user = kwargs.pop('user')
        else:
            self.user = AnonymousUser
        """Create and populate the form."""
        super().__init__(*args, **kwargs)
        self.fields['select'].required = False


class OpinionForm(forms.ModelForm):
    """A form for user's opinions (the root opinion)."""
    WIZARD_RESOLUTION = 10
    WIZARD_POINTS = []
    for x in range(WIZARD_RESOLUTION+1):
        true_points = 100 - 100//WIZARD_RESOLUTION*x
        false_points = 100 - true_points
        WIZARD_POINTS.append(
            ('%d' % true_points, '%d/<font color="red">%d</font>' % (true_points, false_points)))
    wizard_points = forms.ChoiceField(
        choices=WIZARD_POINTS, widget=forms.RadioSelect)

    class Meta:
        """Where the form options are defined."""
        model = Opinion
        fields = ('true_input', 'false_input', 'force')
        labels = {
            'true_input':  'True Points',
            'false_input': 'False Points',
        }
        widgets = {
            'true_input':   TRUE_INPUT_WIDGET,
            'false_input':  TRUE_INPUT_WIDGET,
        }

    def __init__(self, *args, **kwargs):
        """Create and populate the form."""
        # setup
        if 'user' in kwargs.keys():
            self.user = kwargs.pop('user')
        else:
            self.user = AnonymousUser
        if 'wizard' in kwargs.keys():
            self.wizard = kwargs.pop('wizard')
        else:
            self.wizard = False
        super().__init__(*args, **kwargs)

        # widget config
        self.fields['force'].required = False
        self.fields['true_input'].required = False
        self.fields['false_input'].required = False

        # generate initial data
        if self.instance.id is not None:
            x = round(self.instance.true_points() *
                      self.WIZARD_RESOLUTION) * 100//self.WIZARD_RESOLUTION
            self.fields['wizard_points'].initial = str(x)

        # hidden inputs
        if self.wizard:
            self.fields['force'].widget = forms.HiddenInput()
            self.fields['true_input'].widget = forms.HiddenInput()
            self.fields['false_input'].widget = forms.HiddenInput()
        else:
            self.fields['wizard_points'].required = False
            self.fields['wizard_points'].widget = forms.HiddenInput()

    def save(self, commit=True):
        # setup
        opinion = super().save(commit=False)

        # translate wizard data
        if 'wizard_points' in self.changed_data:
            data = self.cleaned_data['wizard_points']
            initial = self.fields['wizard_points'].initial
            if len(data) > 0 and int(data) != initial:
                opinion.true_input = int(data)
                opinion.false_input = 100 - opinion.true_input
                opinion.force = True

        # save
        if commit:
            opinion.save()
        return opinion


class OpinionNodeForm(forms.ModelForm):
    """A form for user opinion node points."""

    # non-model fields
    CHOICES = [
        (True, 'true'),
        (False, 'false'),
    ]
    select_collaborate = forms.ChoiceField(
        choices=CHOICES, widget=forms.RadioSelect())
    select_contradict = forms.ChoiceField(
        choices=CHOICES, widget=forms.RadioSelect())

    class Meta:
        """Where the form options are defined."""
        model = OpinionNode
        fields = ('tt_input', 'tf_input', 'ft_input', 'ff_input',
                  'select_collaborate', 'select_contradict')
        labels = {
            'tt_input': 'True Points',
            'tf_input': 'False Points',
            'ft_input': 'True Points',
            'ff_input': 'False Points',
        }
        widgets = {
            'tt_input':     TRUE_INPUT_WIDGET,
            'tf_input':     TRUE_INPUT_WIDGET,
            'ft_input':     FALSE_INPUT_WIDGET,
            'ff_input':     FALSE_INPUT_WIDGET,
        }

    def __init__(self, *args, **kwargs):
        """Create and populate the form."""

        # setup
        if 'user' in kwargs.keys():
            self.user = kwargs.pop('user')
        if 'wizard' in kwargs.keys():
            self.wizard = kwargs.pop('wizard')
        else:
            self.wizard = False
        super().__init__(*args, **kwargs)

        # initial data
        self.refresh_parent = False
        if self.instance.id is None and 'initial' in kwargs.keys():
            self.instance.theory_node = kwargs['initial']['theory_node']
            self.instance.parent = kwargs['initial']['parent']
            if self.instance.parent.id is None:
                self.refresh_parent = True
        theory_node = self.instance.theory_node

        # url
        if theory_node.is_theory():
            self.url = reverse('theories:get_my_opinion',
                               kwargs={'pk': theory_node.pk})
        else:
            self.url = None

        # widget config
        self.fields['tt_input'].required = False
        self.fields['tf_input'].required = False
        self.fields['ft_input'].required = False
        self.fields['ff_input'].required = False
        self.fields['select_collaborate'].required = False
        self.fields['select_contradict'].required = False

        # wizard
        if self.wizard:
            # widget config
            self.fields['tt_input'].widget = forms.HiddenInput()
            self.fields['tf_input'].widget = forms.HiddenInput()
            self.fields['ft_input'].widget = forms.HiddenInput()
            self.fields['ff_input'].widget = forms.HiddenInput()
            # generate initial data
            if self.instance.id is not None:
                opinion_is_true = self.instance.parent.true_points(
                ) > self.instance.parent.false_points()
                opinion_is_false = not opinion_is_true

                if opinion_is_true and self.instance.tt_input > 0:
                    self.fields['select_collaborate'].initial = str(True)
                elif opinion_is_true and self.instance.ft_input > 0:
                    self.fields['select_collaborate'].initial = str(False)
                elif opinion_is_false and self.instance.tf_input > 0:
                    self.fields['select_collaborate'].initial = str(True)
                elif opinion_is_false and self.instance.ff_input > 0:
                    self.fields['select_collaborate'].initial = str(False)

                if opinion_is_true and self.instance.tf_input > 0:
                    self.fields['select_contradict'].initial = str(True)
                elif opinion_is_true and self.instance.ff_input > 0:
                    self.fields['select_contradict'].initial = str(False)
                elif opinion_is_false and self.instance.tt_input > 0:
                    self.fields['select_contradict'].initial = str(True)
                elif opinion_is_false and self.instance.ft_input > 0:
                    self.fields['select_contradict'].initial = str(False)

        # advanced
        else:
            self.fields['select_collaborate'].widget = forms.HiddenInput()
            self.fields['select_contradict'].widget = forms.HiddenInput()

        # setup initial display
        if theory_node.is_subtheory():
            if self.instance.id is not None:
                if self.instance.ft_input + self.instance.ff_input > 0:
                    self.display_true = False
                else:
                    self.display_true = True
            else:
                opinion_root = get_or_none(
                    theory_node.opinions.all(), user=self.user)
                if opinion_root is None or opinion_root.is_true():
                    self.display_true = True
                else:
                    self.dispaly_true = False

    def save(self, commit=True):
        # setup
        opinion_node = super().save(commit=False)
        # hack for refreshing parent
        if self.refresh_parent:
            opinion_node.parent = opinion_node.parent

        # collaborate
        if 'select_collaborate' in self.changed_data:
            data = self.cleaned_data.get('select_collaborate')
            initial = self.fields['select_collaborate'].initial
            if len(data) > 0 and bool(data) != initial:
                opinion_is_true = opinion_node.parent.true_input >= opinion_node.parent.false_input
                if data == 'True' and opinion_is_true:
                    opinion_node.tt_input = 10
                elif data == 'True' and not opinion_is_true:
                    opinion_node.tf_input = 10
                elif data == 'False' and opinion_is_true:
                    opinion_node.ft_input = 10
                elif data == 'False' and not opinion_is_true:
                    opinion_node.ff_input = 10

        # contradict
        if 'select_contradict' in self.changed_data:
            data = self.cleaned_data.get('select_contradict')
            initial = self.fields['select_contradict'].initial
            if len(data) > 0 and bool(data) != initial:
                opinion_is_true = opinion_node.parent.true_input >= opinion_node.parent.false_input
                if data == 'True' and opinion_is_true:
                    opinion_node.tf_input = 10
                elif data == 'True' and not opinion_is_true:
                    opinion_node.tt_input = 10
                elif data == 'False' and opinion_is_true:
                    opinion_node.ff_input = 10
                elif data == 'False' and not opinion_is_true:
                    opinion_node.ft_input = 10

        # save
        if commit:
            opinion_node.save()
        return opinion_node


class TheoryRevisionForm(forms.ModelForm):
    """Theory Revision form.
    
    Todo:
        * Merge with Evidence revision form.
    """

    # non-model fields
    title01 = forms.CharField(label='True Statement')
    title00 = forms.CharField(label='False Statement')
    details = forms.CharField(**DETAILS_CHARFEILD)
    delete = forms.BooleanField(initial=False)

    class Meta:
        """Where the form options are defined."""
        model = Version
        fields = ('title01', 'title00', 'details', 'delete')

    def __init__(self, *args, **kwargs):
        """Create and populate the theory form."""

        # setup
        if 'user' in kwargs.keys():
            self.user = kwargs.pop('user')
        else:
            self.user = AnonymousUser
        if 'hide_delete' in kwargs.keys():
            hide_delete = kwargs.pop('hide_delete')
        else:
            hide_delete = False
        super().__init__(*args, **kwargs)

        # populate data
        self.fields['title00'].initial = self.instance.field_dict['title00']
        self.fields['title01'].initial = self.instance.field_dict['title01']
        self.fields['details'].initial = self.instance.field_dict['details']

        # config
        self.fields['delete'].required = False
        self.fields['title00'].required = False
        self.fields['title01'].required = False
        self.fields['details'].required = False
        self.fields['title00'].widget.attrs['readonly'] = True
        self.fields['title01'].widget.attrs['readonly'] = True
        self.fields['details'].widget.attrs['readonly'] = True

        # blah
        if hide_delete:
            self.fields['delete'].widget = forms.HiddenInput()


class EvidenceRevisionForm(forms.ModelForm):
    """Theory Revision form."""

    # non-model fields
    title01 = forms.CharField(label='Statement')
    details = forms.CharField(**DETAILS_CHARFEILD)
    verifiable = forms.BooleanField(label='Is this verifiable?')
    delete = forms.BooleanField(initial=False)

    class Meta:
        """Where the form options are defined."""
        model = Version
        fields = ('title01', 'details', 'verifiable', 'delete',)

    def __init__(self, *args, **kwargs):
        """Create and populate the theory form."""

        # setup
        if 'user' in kwargs.keys():
            self.user = kwargs.pop('user')
        else:
            self.user = AnonymousUser
        super().__init__(*args, **kwargs)

        # populate data
        self.fields['title01'].initial = self.instance.field_dict['title01']
        self.fields['details'].initial = self.instance.field_dict['details']
        self.fields['verifiable'].initial = self.instance.field_dict['node_type'] == TheoryNode.TYPE.FACT

        # config
        self.fields['delete'].required = False
        self.fields['title01'].required = False
        self.fields['details'].required = False
        self.fields['verifiable'].required = False
        self.fields['title01'].widget.attrs['readonly'] = True
        self.fields['details'].widget.attrs['readonly'] = True
        self.fields['verifiable'].widget.attrs['readonly'] = True
