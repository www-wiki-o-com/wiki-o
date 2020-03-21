"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

Copyright (C) 2018 Wiki-O, Frank Imeson

This source code is licensed under the GPL license found in the
LICENSE.md file in the root directory of this source tree.
"""

# *******************************************************************************
# Imports
# *******************************************************************************
from django import forms
from notifications.models import Notification

from users.models import User
from users.models import Violation, ViolationFeedback, ViolationVote

# *******************************************************************************
# Classes
#
#
#
#
#
#
#
#
# *******************************************************************************


class UserForm(forms.ModelForm):
    """A form for creating/updating user info.

    Attributes:
        forms ([type]): [description]
    """

    class Meta:
        """Where the form options are defined."""
        model = User
        fields = (
            'username',
            'email',
            'fullname',
            'sex',
            'location',
            'religion',
            'politics',
            'birth_date',
            'hidden',
            'sex_visible',
            'fullname_visible',
            'location_visible',
            'religion_visible',
            'politics_visible',
            'birth_date_visible',
            'use_wizard',
        )
        labels = {
            'fullname': 'Full Name',
            'politics': 'Political Alignment',
            'sex_visible': 'Sex',
            'fullname_visible': 'Full Name',
            'location_visible': 'Location',
            'religion_visible': 'Religion',
            'politics_visible': 'Political Alignment',
            'birth_date_visible': 'Age',
            'hidden': 'Hide Identity',
            'use_wizard': 'Use Wizard',
        }
        help_texts = {
            'email': 'We do not share your email address with anyone.',
            'location': 'Country, State/Province, City/Town',
            'religion': 'Christian, Muslim, Spiritual, ...',
            'sex': 'Male, Female, trans, ...',
            'politics': 'Liberal/Left, Moderate/Middle, Conservitive/Right, ...',
            'birth_date': 'YYYY-MM-DD',
        }

    def __init__(self, *args, **kwargs):
        """Todo

        Returns:
            [type]: [description]
        """
        super(UserForm, self).__init__(*args, **kwargs)
        self.fields['email'].widget.attrs['readonly'] = True
        self.fields['sex'].required = False
        self.fields['location'].required = False
        self.fields['religion'].required = False
        self.fields['politics'].required = False
        self.fields['fullname'].required = False
        self.fields['birth_date'].required = False


class SelectNotificationForm(forms.ModelForm):
    """A form for slecting notifications."""

    # non-model fields
    select = forms.BooleanField(initial=False)

    class Meta:
        """Where the form options are defined."""
        model = Notification
        fields = ('select',)

    def __init__(self, *args, **kwargs):
        """Create and populate the form."""
        super().__init__(*args, **kwargs)
        self.fields['select'].required = False


class SelectViolationForm(forms.ModelForm):
    """A form for slecting notifications."""

    # non-model fields
    select = forms.BooleanField(initial=False)

    class Meta:
        """Where the form options are defined."""
        model = Violation
        fields = ('select',)

    def __init__(self, *args, **kwargs):
        """Create and populate the form."""
        super().__init__(*args, **kwargs)
        self.fields['select'].required = False


class ReportViolationForm(forms.ModelForm):
    """Report user violation form."""

    # Non-model fields
    explanation = forms.CharField(max_length=700,
                                  widget=forms.Textarea(attrs={
                                      'rows': 4,
                                      'style': 'width:100%;'
                                  }))
    offences = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        choices=ViolationFeedback.THEORY_OFFENCES,
        required=False,
        label='',
    )
    intent = forms.ChoiceField(
        choices=ViolationFeedback.INTENTIONS,
        required=False,
        label='Intent (as interpreted by you)',
    )

    class Meta:
        """Where the form options are defined."""
        model = Violation
        fields = ('offender', 'offences', 'intent', 'explanation')
        widgets = {
            'description': forms.Textarea,
        }

    def __init__(self, *args, **kwargs):
        # setup
        self.user = kwargs.pop('user')
        self.content = kwargs.pop('content')
        super().__init__(*args, **kwargs)
        # Populate reporter
        self.reporter = self.user
        # Populate choices
        self.fields['offender'].choices = [('', '----')]
        exclude = [User.get_system_user(), self.user]
        if self.content.__class__.__name__ == 'Content':
            self.fields['offender'].choices += \
                [(x.pk, x.username) for x in self.content.get_collaborators(exclude=exclude)]
            if self.content.is_theory():
                self.fields['offences'].choices = ViolationFeedback.THEORY_OFFENCES
            else:
                self.fields['offences'].choices = ViolationFeedback.EVIDENCE_OFFENCES
        elif self.content.__class__.__name__ == 'Violation':
            self.fields['offender'].choices += \
                [(x.pk, x.username) for x in self.content.get_feedback_users(exclude=exclude)]
            self.fields['offences'].choices = ViolationFeedback.RESOLUTION_OFFENCES
        # Feedback
        self.fields['explanation'].required = False

    def save(self, commit=True):
        """Todo

        Args:
            commit (bool, optional): [description]. Defaults to True.

        Returns:
            [type]: [description]
        """
        # Violation
        created = False
        violation = None
        offender = self.cleaned_data['offender']
        for x in self.content.violations.filter(offender=offender):
            if x.is_open():
                violation = x
                break
        # Create and save (commit)
        if violation is None:
            violation = super().save(commit=False)
            violation.status = Violation.STATUS.REPORTED
            violation.content = self.content
            violation.reporter = self.reporter
            violation.read = False
            created = True
        if commit:
            violation.save()

        # Create new report
        data = ViolationFeedback.pack_data(ViolationFeedback.ACTION_FEEDBACK.REPORTED,
                                           self.cleaned_data.get('intent'),
                                           self.cleaned_data.get('offences'),
                                           self.cleaned_data.get('explanation'))
        violation.feedback.create(
            user=self.user,
            data=data,
        )
        if created:
            violation.open_poll()

        # Done
        return violation


class ResolveViolationForm(forms.ModelForm):
    """Todo

    Attributes:
        forms ([type]): [description]
    """
    action = forms.ChoiceField(
        choices=ViolationFeedback.OPEN_ACTION_CHOICES,
        required=False,
        label='Make a Decision',
    )
    offences = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        choices=ViolationFeedback.THEORY_OFFENCES,
        required=False,
        label='',
    )
    intent = forms.ChoiceField(
        choices=ViolationFeedback.INTENTIONS,
        required=False,
        label='Intent (as interpreted by you)',
    )
    comment = forms.CharField(
        widget=forms.Textarea(attrs={
            'max_length': 700,
            'rows': 4,
            'style': 'width:100%;',
            'readonly': 'True',
        }),
        required=False,
    )

    class Meta:
        """Where the form options are defined."""
        model = ViolationFeedback
        fields = ()

    def __init__(self, *args, **kwargs):
        """Todo

        Returns:
            [type]: [description]
        """
        # Setup
        self.user = kwargs.pop('user')
        self.violation = kwargs.pop('violation')
        super().__init__(*args, **kwargs)
        # Initialize
        self.instance.user = self.user
        self.instance.violation = self.violation
        # Widgets
        if self.user.has_perm('users.can_comment_violation', self.violation):
            self.fields['comment'].widget.attrs['readonly'] = False
        # Polling
        if self.user.has_perm('users.can_resolve_violation', self.violation):
            self.fields['action'].choices = ViolationFeedback.OPEN_ACTION_CHOICES
        else:
            self.fields['action'].choices = ViolationFeedback.CLOSED_ACTION_CHOICES
        # Offences
        content = self.violation.content
        if content.__class__.__name__ == 'Content':
            if content.is_theory():
                self.fields['offences'].choices = ViolationFeedback.THEORY_OFFENCES
            else:
                self.fields['offences'].choices = ViolationFeedback.EVIDENCE_OFFENCES
        elif content.__class__.__name__ == 'Violation':
            self.fields['offences'].choices = ViolationFeedback.RESOLUTION_OFFENCES

    def save(self, commit=True):
        """Todo

        Args:
            commit (bool, optional): [description]. Defaults to True.

        Returns:
            [type]: [description]
        """
        # Preconditions
        if not self.user.has_perm('users.can_comment_violation', self.violation) and \
           not self.user.has_perm('users.can_resolve_violation', self.violation):
            return None

        # Setup
        feedback = super().save(commit=False)
        feedback.data = ViolationFeedback.pack_data(self.cleaned_data.get('action'),
                                                    self.cleaned_data.get('intent'),
                                                    self.cleaned_data.get('offences'),
                                                    self.cleaned_data.get('comment'))
        action = 0 if self.cleaned_data.get('action') == '' else int(
            self.cleaned_data.get('action'))

        # Close the poll if the action is a judgement.
        if action == ViolationFeedback.OPEN_ACTION_CHOICES.NO_ACTION:
            pass
        elif action == ViolationFeedback.CLOSED_ACTION_CHOICES.OPEN_POLL:
            self.violation.open_poll(user=self.user, log_feedback=False)
        elif action == ViolationFeedback.OPEN_ACTION_CHOICES.CLOSE_POLL:
            self.violation.close_poll(user=self.user, log_feedback=False)
        else:
            self.violation.override_status(action, user=self.user, log_feedback=False)

        # Save
        if commit:
            feedback.save()

        # Done
        return feedback


class VoteForm(forms.ModelForm):
    """Todo

    Attributes:

    """

    class Meta:
        """Where the form options are defined."""
        model = ViolationVote
        fields = ('vote',)
        labels = {
            'vote': 'Your Vote',
        }

    def __init__(self, *args, **kwargs):
        """Todo

        Returns:
            [type]: [description]
        """
        # setup
        self.user = kwargs.pop('user')
        self.violation = kwargs.pop('violation')
        super().__init__(*args, **kwargs)

        # initial
        if self.instance.id is None:
            self.instance.user = self.user
            self.instance.violation = self.violation
        else:
            self.fields['vote'].choices = ViolationVote.VOTE_CHOICES

        # widget
        if self.user.has_perm('users.can_vote_violation', self.violation):
            self.fields['vote'].widget.attrs['readonly'] = False
        else:
            self.fields['vote'].widget.attrs['readonly'] = True

        # blah
        self.fields['vote'].required = False

    def save(self, commit=True):
        """Todo

        Args:
            commit (bool, optional): [description]. Defaults to True.

        Returns:
            [type]: [description]
        """
        # Preconditions
        if not self.user.has_perm('users.can_vote_violation', self.violation):
            return None
        # Save
        vote = super().save(commit=False)
        if commit:
            vote.save()
        return vote
