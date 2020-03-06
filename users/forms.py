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

from users.models import *
from core.utils import get_first_or_none

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
    """Todo

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

    explanation = forms.CharField(max_length=700,
                                  widget=forms.Textarea(attrs={
                                      'rows': 4,
                                      'style': 'width:100%;'
                                  }))
    offences = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        choices=Violation.THEORY_OFFENCES,
        required=False,
        label='',
    )
    intent = forms.ChoiceField(
        choices=Violation.INTENTIONS,
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
        # Populate choices
        self.fields['offender'].choices = [('', '----')]
        if self.content.__class__.__name__ == 'TheoryNode':
            self.fields['offender'].choices += \
                [(x.pk, x.username) for x in self.content.get_collaborators(exclude=self.user)]
            if self.content.is_theory():
                self.fields['offences'].choices = Violation.THEORY_OFFENCES
            else:
                self.fields['offences'].choices = Violation.EVIDENCE_OFFENCES
        elif self.content.__class__.__name__ == 'Violation':
            exclude = [User.get_system_user(), self.user]
            exclude = None
            self.fields['offender'].choices += \
                [(x.pk, x.username) for x in self.content.get_feedback_users(exclude=exclude)]
            self.fields['offences'].choices = Violation.RESOLUTION_OFFENCES
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
            violation.status = Violation.STATUS.POLLING
            violation.content = self.content
            created = True
            if commit:
                violation.save()

        # Feedback
        if violation.id is not None:
            # check for previous report
            feedback = get_first_or_none(
                violation.feedback.all(),
                violation=violation,
                user=self.user,
                action=ViolationFeedback.ACTIONS00.REPORTED,
            )
            # Create new report
            if feedback is None:
                # intent/offences
                offence_list = str([int(x) for x in self.cleaned_data.get('offences')])
                comment = '%s/%s/%s' % (self.cleaned_data.get('intent'), offence_list,
                                        self.cleaned_data.get('explanation'))
                violation.feedback.create(
                    user=self.user,
                    action=ViolationFeedback.ACTIONS00.REPORTED,
                    comment=comment,
                )
            # Create poll
            if created:
                system_user = User.get_system_user()
                violation.feedback.create(
                    user=system_user,
                    action=ViolationFeedback.ACTIONS01.OPEN_POLL,
                )

        # Done
        return violation


class ResolveViolationForm(forms.ModelForm):
    """Todo

    Attributes:
        forms ([type]): [description]
    """
    offences = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        choices=Violation.THEORY_OFFENCES,
        required=False,
        label='',
    )
    intent = forms.ChoiceField(
        choices=Violation.INTENTIONS,
        required=False,
        label='Intent (as interpreted by you)',
    )

    class Meta:
        """Where the form options are defined."""
        model = ViolationFeedback
        fields = ('action', 'comment')
        labels = {
            'action': 'Make a Decision',
            'comment': 'Comment',
        }
        widgets = {
            'comment': forms.Textarea(attrs={
                'max_length': 700,
                'rows': 4,
                'style': 'width:100%;'
            }),
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
        self.instance.user = self.user
        self.instance.violation = self.violation
        # widgets
        self.fields['action'].required = False
        self.fields['comment'].required = False
        if self.user.has_perm('users.can_comment_violation', self.violation):
            self.fields['comment'].widget.attrs['readonly'] = False
        else:
            self.fields['comment'].widget.attrs['readonly'] = True
        # polling
        if self.user.has_perm('users.can_resolve_violation', self.violation):
            self.fields['action'].choices = ViolationFeedback.ACTIONS01
        # intent/offences
        content = self.violation.content
        if content.__class__.__name__ == 'TheoryNode':
            if content.is_theory():
                self.fields['offences'].choices = Violation.THEORY_OFFENCES
            else:
                self.fields['offences'].choices = Violation.EVIDENCE_OFFENCES
        elif content.__class__.__name__ == 'Violation':
            self.fields['offences'].choices = Violation.RESOLUTION_OFFENCES

    def save(self, commit=True):
        """Todo

        Args:
            commit (bool, optional): [description]. Defaults to True.

        Returns:
            [type]: [description]
        """
        # setup
        feedback = super().save(commit=False)
        if not self.user.has_perm('users.can_comment_violation', self.violation) and \
           not self.user.has_perm('users.can_resolve_violation', self.violation):
            return None

        # comment/intent/offences
        offence_list = str([int(x) for x in self.cleaned_data.get('offences')])
        feedback.comment = '%s/%s/%s' % (self.cleaned_data.get('intent'), offence_list,
                                         self.cleaned_data.get('comment'))

        # violation
        if 'action' in self.changed_data and feedback.action > 0:
            action = self.cleaned_data.get('action')
            if self.violation.is_polling() and action >= 110:
                self.violation.feedback.create(
                    user=self.user,
                    action=ViolationFeedback.ACTIONS01.CLOSE_POLL,
                )
            self.violation.status = action
            self.violation.save()

        # save
        if commit:
            feedback.save()
            if feedback.action == ViolationFeedback.ACTIONS01.CLOSE_POLL:
                self.violation.close_poll(user=self.user)
                system_user = User.get_system_user()
                action = self.violation.close_poll()
                self.violation.feedback.create(
                    user=system_user,
                    action=action,
                )

        # done
        return feedback


class VoteForm(forms.ModelForm):
    """Todo

    Attributes:

    """

    class Meta:
        """Where the form options are defined."""
        model = ViolationVote
        fields = ('action',)
        labels = {
            'action': 'Your Vote',
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
            self.fields['action'].choices = Violation.VOTES01

        # widget
        if self.user.has_perm('users.can_vote_violation', self.violation):
            self.fields['action'].widget.attrs['readonly'] = False
        else:
            self.fields['action'].widget.attrs['readonly'] = True

        # blah
        self.fields['action'].required = False

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
