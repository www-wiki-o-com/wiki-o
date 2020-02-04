"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

A web service for sharing opinions and avoiding arguments

@file       users/models.py
@brief      A collection of models for the app
@copyright  GNU Public License, 2018
@authors    Frank Imeson
"""


# *******************************************************************************
# imports
# *******************************************************************************
import re
import datetime

from django.db import models
from django.urls import reverse
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Sum, F, Q
from django.utils import timezone

#import simplejson as json

from model_utils import Choices
from actstream.models import Action


# *******************************************************************************
# methods
# *******************************************************************************

# ******************************
#
# ******************************
def get_group(level):
    return Group.objects.get(name='user level: %d' % level)


# *******************************************************************************
# classes
#
#
#
#
#
#
#
#
# *******************************************************************************


# ************************************************************
# User
# ************************************************************
class User(AbstractUser):
    """Wiki-O user model."""

    # ******************************
    # Defines
    # ******************************

    # ******************************
    # Model variables
    # ******************************
    sex = models.CharField(max_length=60, blank=True)
    location = models.CharField(max_length=60, blank=True)
    religion = models.CharField(max_length=60, blank=True)
    politics = models.CharField(max_length=60, blank=True)
    fullname = models.CharField(max_length=60, blank=True)
    birth_date = models.DateField(null=True, blank=True)

    sex_visible = models.BooleanField(default=False)
    location_visible = models.BooleanField(default=False)
    religion_visible = models.BooleanField(default=False)
    politics_visible = models.BooleanField(default=False)
    fullname_visible = models.BooleanField(default=False)
    birth_date_visible = models.BooleanField(default=False)

    hidden = models.BooleanField(default=False)
    use_wizard = models.BooleanField(default=True)
    utilized = models.ManyToManyField(
        'theories.TheoryNode', related_name='users', blank=True)
    contributions = models.ManyToManyField(
        'theories.TheoryNode', related_name='collaborators', blank=True)

    SYSTEM_USER_PK = 10

    # ******************************
    # User
    # ******************************
    @classmethod
    def get_system_user(cls, create=True):
        """Creates and returns the system user."""
        # assume intuition_pk is known
        try:
            system_user = cls.objects.get(pk=cls.SYSTEM_USER_PK)
            if system_user.username != 'system':
                system_user = None
        except:
            system_user = None

        # get or create
        if create and system_user is None:
            system_user, created = cls.objects.get_or_create(
                username='system',
            )
            system_user.set_password(User.objects.make_random_password())
            system_user.save()
            cls.SYSTEM_USER_PK = system_user.pk

        # blah
        return system_user

    # ******************************
    # User
    # ******************************
    def __str__(self, print_fullname=False):
        """Output username if not hidden."""
        if print_fullname and self.get_fullname() != 'N/A':
            return self.get_fullname()
        else:
            return self.get_username()

    # ******************************
    # User
    # ******************************
    def is_hidden(self):
        return self.hidden

    # ******************************
    # User
    # ******************************
    def is_visible(self):
        return not self.hidden

    # ******************************
    # User
    # ******************************
    def get_long(self):
        return self.__str__(print_fullname=True)

    # ******************************
    # User
    # ******************************
    def get_username(self):
        """Output username if not hidden."""
        return self.username

    # ******************************
    # User
    # ******************************
    def get_fullname(self):
        """Output username if not hidden."""
        if len(self.fullname) > 0 and self.fullname_visible:
            return self.fullname
        else:
            return 'N/A'

    # ******************************
    # User
    # ******************************
    def get_level(self):
        levels = sorted([int(x['name'].split(' ')[-1])
                         for x in self.groups.values('name')])
        return levels[-1]

    #******************************
    # 
    #******************************
    def get_levels(self):
        return sorted([int(x['name'].split(' ')[-1]) for x in self.groups.values('name')])

    # ******************************
    # User
    # ******************************
    def get_absolute_url(self):
        """Return the url for viewing the user's profile."""
        return reverse('users:profile-detail', args=[], kwargs={'pk': self.id})

    # ******************************
    # User
    # ******************************
    def url(self):
        """Return the url for viewing the user's profile."""
        return self.get_absolute_url()

    # ******************************
    # User
    # ******************************
    def get_age(self):
        """Calculate age if not hidden."""
        if self.birth_date is not None and self.birth_date_visible:
            born = self.birth_date
            today = datetime.date.today()
            return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        else:
            return 'N/A'

    # ******************************
    # User
    # ******************************
    def get_sex(self):
        """Return sex if not hidden."""
        if len(self.sex) > 0 and self.sex_visible:
            return self.sex
        else:
            return 'N/A'

    # ******************************
    # User
    # ******************************
    def get_location(self):
        """Return location if not hidden."""
        if len(self.location) > 0 and self.location_visible:
            return self.location
        else:
            return 'N/A'

    # ******************************
    # User
    # ******************************
    def get_religion(self):
        """Return religion if not hidden."""
        if len(self.religion) > 0 and self.religion_visible:
            return self.religion
        else:
            return 'N/A'

    # ******************************
    # User
    # ******************************
    def get_politics(self):
        """Return political alignment if not hidden."""
        if len(self.politics) > 0 and self.politics_visible:
            return self.politics
        else:
            return 'N/A'

    # ******************************
    # User
    # ******************************
    def num_contributions(self):
        return self.contributions.count()

    # ******************************
    # User
    # ******************************
    def is_using(self, theory_node, recalculate=False):
        if recalculate:
            if self.opinions.filter(theory=self, deleted=False).exists() or self.opinions.filter(nodes__theory_node=self).exists():
                self.utilized.add(theory_node)
                return True
            else:
                self.utilized.remove(theory_node)
                return False
        return self.utilized.filter(id=theory_node.pk).exists()

    # ******************************
    # User
    # ******************************
    def count_warnings(self):
        return self.violations.filter(status=Violation.STATUS.WARNING).count()

    # ******************************
    # User
    # ******************************
    def get_violations(self, soft=True, hard=True, recent=True, expired=False):

        # setup
        assert recent or expired
        violations = Violation.objects.none()

        # filter by type
        if hard:
            violations |= self.violations.filter(
                Q(status=Violation.STATUS.ACCEPTED) |
                Q(status=-Violation.STATUS.ACCEPTED)
            )
        if soft:
            exclude = []
            for violation in self.violations.filter(status__lt=110):
                if violation.get_poll_winner() != Violation.STATUS.ACCEPTED:
                    exclude.append(violation.id)
            violations |= self.violations.filter(
                status__lt=110).exclude(id__in=exclude)

        # filter by date
        if recent and expired:
            pass
        elif recent:
            date00 = datetime.date.today() - datetime.timedelta(days=100)
            violations = violations.filter(pub_date__gte=date00)
        elif expired:
            date00 = datetime.date.today() - datetime.timedelta(days=100)
            violations = violations.filter(pub_date__lt=date00)

        # done
        return violations

    # ******************************
    # User
    # ******************************
    def count_strikes(self, soft=False, hard=True, recent=True, expired=False):
        return self.get_violations(soft=soft, hard=hard, recent=recent, expired=expired).count()

    # ******************************
    # User
    # ******************************
    def is_up_for_promotion(self):
        if self.count_strikes(soft=True) > 0:
            return False
        elif self.get_level() == 1 and self.account_age() >= 10 and self.count_contributions() >= 10:
            return True
        elif self.get_level() == 2 and self.account_age() >= 100 and self.count_contributions() >= 100:
            return True
        else:
            return False

    # ******************************
    # User
    # ******************************
    def promote(self, new_level=None):
        # setup
        user_levels = self.get_levels()
        if new_level is None:
            new_level = max(4, user_levels[-1]+1)
        group_level = get_group(new_level)
        self.groups.add(group_level)

    # ******************************
    # User
    # ******************************
    def is_up_for_demotion(self):
        if self.count_strikes() >= 3:
            return True
        else:
            return False

    # ******************************
    # User
    # ******************************
    def demote(self, new_level=None):
        # setup
        user_levels = self.get_levels()
        if new_level is None:
            new_level = max(0, user_levels[-1]-1)
        group_level = get_group(new_level)
        self.groups.add(group_level)

        # drop level(s)
        for level in user_levels:
            if new_level < level:
                group_level = get_group(level)
                self.groups.remove(group_level)


# ************************************************************
# Violation
  # violation list (string):
    # list of numbers that correlate with enums
    # forum, check all that apply
    # feedback, add to list?
    # remove explanation?
# ************************************************************
class Violation(models.Model):

    # Status (read is negative)
    STATUS = Choices(
        (100, "REPORTED", ("Pending")),
        (101, "POLLING", ("Polling")),
        (102, "PENDING", ("Pending")),
        (110, "IGNORED", ("Ignored")),
        (120, "WARNING", ("Warning")),
        (130, "ACCEPTED", ("Accepted")),
        (140, "REJECTED", ("Rejected")),
    )

    # Votes
    VOTES00 = Choices(
        (0, "NO_VOTE", ("----")),
        (110, 'IGNORE', ('Ignore')),
        (120, 'WARN', ('Warn')),
        (130, 'ACCEPT', ('Accept')),
        (140, 'REJECT', ('Reject')),
    )
    VOTES01 = Choices(
        (110, 'IGNORE', ('Ignore')),
        (120, 'WARN', ('Warn')),
        (130, 'ACCEPT', ('Accept')),
        (140, 'REJECT', ('Reject')),
    )

    # Intent
    INTENTIONS = Choices(
        ("", "----"),
        (10, "Unintentional"),
        (20, "Careless"),
        (30, "Adversarial"),
    )

    # Offences
    OFFENCES = Choices(
        (110, "Provided commentary."),
        (115, "Provided non-Wiki-O content."),
        (120, "Reverted sound content."),
        (125, "Unnecessarily added or removed evidence."),
        (130, "Performed unnecessary action."),
        (135, "Missclassified evidence."),

        (210, "Spamming the comments and/or reports."),
        (215, "Voted with an ulterior agenda."),
        (220, "Unnecessarily overrode the poll."),

        (850, "Acted adversarially."),
    )
    THEORY_OFFENCES = Choices(
        (110, "Provided commentary (leading, etc)."),
        (115, "Provided non-Wiki-O content."),
        (120, "Reverted sound content."),
        (125, "Unnecessarily added or removed evidence."),
        (130, "Performed unnecessary action (swap, convert, merge)."),
    )
    EVIDENCE_OFFENCES = Choices(
        (110, "Provided commentary (leading, etc)."),
        (115, "Provided non-Wiki-O content."),
        (120, "Reverted sound content."),
        (125, "Unnecessarily added or removed evidence."),
        (130, "Performed unnecessary action (convert, merge)."),
        (135, "Missclassified evidence (verifiable field)."),
    )
    RESOLUTION_OFFENCES = Choices(
        (210, "Spamming the comments and/or reports."),
        (215, "Voted with an ulterior agenda."),
        (220, "Unnecessarily overrode the poll (only applies to level 4 users)."),
    )
    FORUM_OFFENCES = Choices(
        (850, "Acted adversarially."),
    )

    offender = models.ForeignKey(
        User, related_name='violations', on_delete=models.CASCADE)
    violations = GenericRelation('Violation')

    object_id = models.PositiveIntegerField()
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    content = GenericForeignKey('content_type', 'object_id')

    status = models.SmallIntegerField(choices=STATUS)
    pub_date = models.DateTimeField()
    modified_date = models.DateTimeField()

    # ******************************
    # Violation
    # ******************************
    class Meta:
        db_table = 'users_violation'
        verbose_name = 'Violation'
        verbose_name_plural = 'Violations'
        ordering = ['-pub_date']
        permissions = (
            ('can_vote_violation', 'Can vote.'),
            ('can_report_violation', 'Can report.'),
            ('can_comment_violation', 'Can comment.'),
            ('can_resolve_violation', 'Can resolve.'),
        )

    # ******************************
    # Violation
    # ******************************
    @classmethod
    def get_violations(cls, opened=True, closed=True):
        violations = cls.objects.none()
        if opened:
            violations |= cls.objects.filter(
                Q(status__lt=110) &
                Q(status__gt=-110)
            )
        if closed:
            violations |= self.violations.filter(
                Q(status__gte=110) |
                Q(status__lte=-110)
            )
        return violations

    # ******************************
    # Violation
    # ******************************
    def save(self, *args, **kwargs):
        self.modified_date = timezone.now()
        if self.pk is None:
            self.pub_date = timezone.now()
        super().save(*args, **kwargs)
        return self

    # ******************************
    # Violation
    # ******************************
    def __str__(self):
        return self.content.__str__()

    # ******************************
    #
    # ******************************
    def get_absolute_url(self):
        return reverse('users:violation-resolve', args=[], kwargs={'pk': self.id})

    # ******************************
    #
    # ******************************
    def url(self):
        return self.get_absolute_url()

    # ******************************
    # Violation
    # ******************************
    def content_url(self):
        if self.content_type.model == 'theorynode':
            return self.content.url()
        return None

    # ******************************
    # Violation
    # ******************************
    def get_status_str(self):
        return self.STATUS[self.get_status()]

    # ******************************
    # Violation
    # ******************************
    def is_unread(self):
        return self.status > 0

    # ******************************
    # Violation
    # ******************************
    def is_read(self):
        return self.status < 0

    # ******************************
    # Violation
    # ******************************
    def get_status(self):
        return abs(self.status)

    # ******************************
    # Violation
    # ******************************
    def mark_as_read(self):
        if self.is_unread():
            self.status = -abs(self.status)
            self.save()

    # ******************************
    # Violation
    # ******************************
    def mark_as_unread(self):
        if self.is_read():
            self.status = abs(self.status)
            self.save()

    # ******************************
    # Violation
    # ******************************
    def get_feedback(self, exclude=None):
        return self.feedback.all()

    # ******************************
    # Violation
    # ******************************
    def get_feedback_users(self, exclude=None):
        users_pk = []
        for x in self.get_feedback():
            users_pk.append(x.user.pk)
        users = User.objects.filter(pk__in=users_pk)
        if exclude is not None:
            exclude_pk = []
            if isinstance(exclude, list):
                exclude_pk = [x.pk for x in exclude]
            elif isinstance(exclude, User):
                exclude_pk = [exclude.pk]
            users = users.exclude(pk__in=exclude_pk)
        return users

    # ******************************
    # Violation
    # ******************************
    def get_type(self):
        return 'Violation'

    # ******************************
    # Violation
    # ******************************
    def get_poll_count(self, cache=True):
        # check cache first cache
        if hasattr(self, 'saved_count'):
            return self.saved_count
        # count
        count = []
        for action_id, action in self.VOTES01:
            count.append(
                [self.votes.filter(action=action_id).count(), action_id, action])
        # cache
        if cache:
            self.saved_count = count
        return count

    # ******************************
    # Violation
    # ******************************
    def poll_is_done(self):
        if self.is_closed():
            return True
        else:
            today = datetime.datetime.today()
            end = self.pub_date + datetime.timedelta(days=10)
            end = datetime.datetime(
                year=end.year, month=end.month, day=end.day, hour=23, minute=59, second=59)
            return today > end

    # ******************************
    # Violation
    # ******************************
    def is_polling(self):
        return not self.poll_is_done()

    # ******************************
    # Violation
    # ******************************
    def get_poll_winner(self):
        votes = self.get_poll_count()
        for x in votes:
            x[0] = -x[0]
        votes = sorted(votes)
        return votes[0][1]

    # ******************************
    # Violation
    # ******************************
    def close_poll(self, user=None):
        # setup
        if user is None:
            user = User.get_system_user()
        # close
        self.status = self.get_poll_winner()
        self.save()
        # document
        self.feedback.create(
            user=user,
            action=ViolationFeedback.ACTIONS01.CLOSE_POLL,
        )
        self.feedback.create(
            user=user,
            action=self.status,
        )
        # offender demotion
        if self.is_strike() and self.offender.is_up_for_demotion():
            self.offender.demote()
        # done
        return self.status

    # ******************************
    # Violation
    # ******************************
    def is_open(self):
        return self.get_status() < 110

    # ******************************
    # Violation
    # ******************************
    def is_closed(self):
        return self.get_status() >= 110

    # ******************************
    # Violation
    # ******************************
    def is_strike(self):
        if self.is_open():
            return False
        else:
            return abs(self.status) == ViolationFeedback.STATUS.ACCEPTED


# ************************************************************
# ViolationFeedback
# ************************************************************
class ViolationFeedback(models.Model):

    ACTIONS00 = Choices(
        (0, "NO_ACTION", ("Comment")),
        (100, "REPORTED", ("Reported Violation")),
        (101, "OPENED_POLL", ("Opened Poll")),
        (102, "CLOSED_POLL", ("Closed Poll")),
        (110, "IGNORED", ("Ignored")),
        (120, "WARNING", ("Warning")),
        (130, "ACCEPTED", ("Accepted")),
        (140, "REJECTED", ("Rejected")),
    )

    ACTIONS01 = Choices(
        (0, "NO_ACTION", ("----")),
        (101, "OPEN_POLL", ("Open Poll")),
        (102, "CLOSE_POLL", ("Close Poll")),
        (110, "IGNORE", ("Ignore")),
        (120, "WARN", ("Warn")),
        (130, "ACCEPT", ("Accept")),
        (140, "REJECT", ("Reject")),
    )

    ACTIONS02 = Choices(
        (0, "NO_ACTION", ("----")),
    )

    user = models.ForeignKey(
        User, related_name='violation_feedback', on_delete=models.SET_NULL, null=True)
    violation = models.ForeignKey(
        Violation, related_name='feedback', on_delete=models.CASCADE)
    action = models.SmallIntegerField(choices=ACTIONS01, default=0)
    comment = models.CharField(max_length=750, blank=True)
    timestamp = models.DateTimeField()

    # ******************************
    # ViolationFeedback
    # ******************************
    class Meta:
        db_table = 'users_violation_feedback'
        verbose_name = 'Violation Feedback'
        verbose_name_plural = 'Violation Feedback'
        ordering = ['timestamp']

    # ******************************
    # ViolationFeedback
    # ******************************
    def __str__(self):
        s = '%s: %s %s (%s)' % (
            self.violation.pub_date,
            self.user,
            self.get_action().lower(),
            self.violation.offender.__str__(),
        )
        s = s.strip().strip(':')
        return s

    # ******************************
    # ViolationFeedback
    # ******************************
    def save(self, *args, **kwargs):
        self.timestamp = timezone.now()
        super().save(*args, **kwargs)
        return self

    # ******************************
    # ViolationFeedback
    # ******************************
    def get_action(self):
        try:
            return self.ACTIONS00[self.action]
        except:
            return 'Error'

    # ******************************
    # ViolationFeedback
    # ******************************
    def get_comment(self, cache=True):
        if cache and hasattr(self, 'saved_comment'):
            return self.saved_comment
        try:
            comment = self.comment.split('/', 2)[2]
        except:
            comment = ''
        if cache:
            self.saved_comment = comment
        return comment

    # ******************************
    # ViolationFeedback
    # ******************************
    def get_intent(self, cache=True):
        if cache and hasattr(self, 'saved_intent'):
            return self.saved_intent
        try:
            intent = int(self.comment.split('/', 2)[0])
            intent = Violation.INTENTIONS[intent]
        except:
            intent = ''
        if cache:
            self.saved_intent = intent
        return intent

    # ******************************
    # ViolationFeedback
    # ******************************
    def get_offences(self, cache=True):
        if hasattr(self, 'saved_offences'):
            return self.saved_offences
        try:
            offences = self.comment.split('/', 2)[1]
            offences = [int(x) for x in re.findall(r'\d+', offences)]
            for i, x in enumerate(offences):
                try:
                    offences[i] = Violation.OFFENCES[x]
                except:
                    offences[i] = 'Error'
        except:
            offences = None
        if cache:
            self.saved_offences = offences
        return offences


# ************************************************************
# ViolationVote
# ************************************************************
class ViolationVote(models.Model):

    user = models.ForeignKey(
        User, related_name='violation_votes', on_delete=models.SET_NULL, null=True)
    violation = models.ForeignKey(
        Violation, related_name='votes', on_delete=models.CASCADE)
    action = models.SmallIntegerField(choices=Violation.VOTES00, default=0)

    # ******************************
    # ViolationVote
    # ******************************
    class Meta:
        db_table = 'users_violation_vote'
        verbose_name = 'Violation Vote'
        verbose_name_plural = 'Violation Votes'

    # ******************************
    # ViolationFeedback
    # ******************************
    def __str__(self):
        s = '%s: %s (%s)' % (
            self.violation.__str__().strip('.'),
            self.user,
            self.violation.offender.__str__(),
        )
        return s

    # ******************************
    # ViolationFeedback
    # ******************************
    def get_vote_str(self):
        return Violation.VOTES00[self.action]
