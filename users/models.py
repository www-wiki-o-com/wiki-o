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
# Imports
# *******************************************************************************
import re
import datetime

from django.db import models
from django.urls import reverse
from django.contrib.auth.models import AbstractUser
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from model_utils import Choices
from users.utils import get_group
from core.utils import get_or_none


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

class User(AbstractUser):
    """User model.

    Attributes:
        SYSTEM_USER_PK (int): [description]

        sex (CharField):
        location (CharField):
        religion (CharField):
        politics (CharField):
        fullname (CharField):
        birth_date (CharField):

        sex_visible (BooleanField):
        location_visible (BooleanField):
        religion_visible (BooleanField):
        politics_visible (BooleanField):
        fullname_visible (BooleanField):
        birth_date_visible (BooleanField):

        hidden (BooleanField):
        use_wizard (BooleanField):
        utilized (TheoryNode):
        contributions (TheoryNode):
    """

    # Defines
    SYSTEM_USER_PK = 10

    # Model variables
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

    @classmethod
    def get_system_user(cls, create=True):
        """Creates and returns the system user.

        Args:
            create (bool, optional): If true, the system user will be created if it doesn't exist.
                Defaults to True.

        Returns:
            User: The system user or None.
        """
        # Assume cls.SYSTEM_USER_PK is valid.
        try:
            system_user = cls.objects.get(pk=cls.SYSTEM_USER_PK)
            if system_user.username == 'system':
                return system_user
            cls.SYSTEM_USER_PK = -1
        except ObjectDoesNotExist:
            cls.SYSTEM_USER_PK = -1

        # Get or create system user.
        if create:
            system_user, created = cls.objects.get_or_create(username='system')
            system_user.set_password(User.objects.make_random_password())
            system_user.save()
            cls.SYSTEM_USER_PK = system_user.pk
        else:
            system_user = get_or_none(cls.objects, username='system')
            cls.SYSTEM_USER_PK = system_user.pk
        return system_user

    def __str__(self, print_fullname=False):
        """Output the user's handle/name.

        Args:
            print_fullname (bool, optional): If true, the user's fullname is returned,
                otherwise the short name is returned. Defaults to False.

        Returns:
            str: The user's handle or fullname.
        """
        if print_fullname and self.get_fullname() != 'N/A':
            return self.get_fullname()
        return self.get_username()

    def is_hidden(self):
        """A getter for the hidden attribute.

        Returns:
            bool: True if the user is hidden.
        """
        return self.hidden

    def is_visible(self):
        """A getter for the hidden attribute.

        Returns:
            bool: True if the user is not hidden.
        """
        return not self.hidden

    def get_long(self):
        """A getter for the user's fullname if visible, otherwise the user's handle.

        Returns:
            str: The user's fullname.
        """
        return self.__str__(print_fullname=True)

    def get_username(self):
        """Output user's handle.

        Returns:
            str: The user's handle.
        """
        return self.username

    def get_fullname(self):
        """Output user's fullname if not hidden.

        Returns:
            str: The user's fullname if not hidden, 'N/A' otherwise.
        """
        if len(self.fullname) > 0 and self.fullname_visible:
            return self.fullname
        return 'N/A'

    def get_level(self):
        """A getter for the user's level.

        Returns:
            int: The user's level.
        """
        levels = sorted([int(x['name'].split(' ')[-1]) for x in self.groups.values('name')])
        return levels[-1]

    def get_levels(self):
        """A getter for the user's permission levels.

        Returns:
            list: An ordered list the user's levels.
        """
        return sorted([int(x['name'].split(' ')[-1]) for x in self.groups.values('name')])

    def get_absolute_url(self):
        """Return the url for viewing the user's profile.

        Returns:
            str: The url.
        """
        return reverse('users:profile-detail', args=[], kwargs={'pk': self.pk})

    def url(self):
        """Return the url for viewing the user's profile.

        Returns:
            str: The url.
        """
        return self.get_absolute_url()

    def get_age(self):
        """Calculate age if not hidden.

        Returns:
            str: The user's age if not hidden, 'N/A' otherwise.
        """
        if self.birth_date is not None and self.birth_date_visible:
            born = self.birth_date
            today = datetime.date.today()
            return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        return 'N/A'

    def get_sex(self):
        """Return sex if not hidden.

        Returns:
            str: The user's sex if not hidden, 'N/A' otherwise.
        """
        if len(self.sex) > 0 and self.sex_visible:
            return self.sex
        return 'N/A'

    def get_location(self):
        """Return location if not hidden.

        Returns:
            str: The user's location if not hidden, 'N/A' otherwise.
        """
        if len(self.location) > 0 and self.location_visible:
            return self.location
        return 'N/A'

    def get_religion(self):
        """Return religion if not hidden.

        Returns:
            str: The user's religion if not hidden, 'N/A' otherwise.
        """
        if len(self.religion) > 0 and self.religion_visible:
            return self.religion
        return 'N/A'

    def get_politics(self):
        """Return political alignment if not hidden.

        Returns:
            str: The user's political alignment if not hidden, 'N/A' otherwise.
        """
        if len(self.politics) > 0 and self.politics_visible:
            return self.politics
        return 'N/A'

    def num_contributions(self):
        """A getter for the number of contributions by the user.

        Returns:
            int: The count.
        """
        return self.contributions.count()

    def is_using(self, theory_node, recalculate=False):
        """Todo

        Args:
            theory_node ([type]): [description]
            recalculate (bool, optional): [description]. Defaults to False.

        Returns:
            [type]: [description]
        """
        if recalculate:
            if (self.opinions.filter(theory=self, deleted=False).exists() or
                    self.opinions.filter(nodes__theory_node=self).exists()):
                self.utilized.add(theory_node)
                return True
            self.utilized.remove(theory_node)
            return False
        return self.utilized.filter(id=theory_node.pk).exists()

    def count_warnings(self):
        """Todo

        Returns:
            [type]: [description]
        """
        return self.violations.filter(status=Violation.STATUS.WARNING).count()

    def get_violations(self, soft=True, hard=True, recent=True, expired=False):
        """Todo

        Args:
            soft (bool, optional): [description]. Defaults to True.
            hard (bool, optional): [description]. Defaults to True.
            recent (bool, optional): [description]. Defaults to True.
            expired (bool, optional): [description]. Defaults to False.

        Returns:
            [type]: [description]
        """
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

    def count_strikes(self, soft=False, hard=True, recent=True, expired=False):
        """Todo

        Args:
            soft (bool, optional): [description]. Defaults to False.
            hard (bool, optional): [description]. Defaults to True.
            recent (bool, optional): [description]. Defaults to True.
            expired (bool, optional): [description]. Defaults to False.

        Returns:
            [type]: [description]
        """
        return self.get_violations(soft=soft, hard=hard, recent=recent, expired=expired).count()

    def is_up_for_promotion(self):
        """Todo

        Returns:
            [type]: [description]

        Todo:
            * Define get_account_age and get_num_contributions.
        """
        if self.count_strikes(soft=True) > 0:
            return False
        if self.get_level() == 1 and self.get_account_age() >= 10 and self.get_num_contributions() >= 10:
            return True
        if self.get_level() == 2 and self.get_account_age() >= 100 and self.get_num_contributions() >= 100:
            return True
        return False

    def promote(self, new_level=None):
        """Todo

        Args:
            new_level ([type], optional): [description]. Defaults to None.

        Returns:
            [type]: [description]
        """
        # setup
        user_levels = self.get_levels()
        if new_level is None:
            new_level = max(4, user_levels[-1]+1)
        group_level = get_group(new_level)
        self.groups.add(group_level)

    def is_up_for_demotion(self):
        """Todo

        Returns:
            [type]: [description]
        """
        if self.count_strikes() >= 3:
            return True
        return False

    def demote(self, new_level=None):
        """Todo

        Args:
            new_level ([type], optional): [description]. Defaults to None.

        Returns:
            [type]: [description]
        """
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


class Violation(models.Model):
    """Todo

    Attributes:
        models ([type]): [description]
    """

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

    # Django database attributes
    offender = models.ForeignKey(User, related_name='violations', on_delete=models.CASCADE)
    violations = GenericRelation('Violation')

    object_id = models.PositiveIntegerField()
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    content = GenericForeignKey('content_type', 'object_id')

    status = models.SmallIntegerField(choices=STATUS)
    pub_date = models.DateTimeField()
    modified_date = models.DateTimeField()

    # Cache attributes
    saved_count = None
    saved_intent = None
    saved_comment = None
    saved_offences = None

    class Meta:
        """Where the model options are defined.

        Model metadata is “anything that’s not a field”, such as ordering options (ordering),
        database table name (db_table), or human-readable singular and plural names
        (verbose_name and verbose_name_plural). None are required, and adding class Meta to a
        model is completely optional.

        For more, see: https://docs.djangoproject.com/en/3.0/ref/models/options/
        """
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

    @classmethod
    def get_violations(cls, opened=True, closed=True):
        """Todo

        Args:
            opened (bool, optional): [description]. Defaults to True.
            closed (bool, optional): [description]. Defaults to True.

        Returns:
            [type]: [description]

        Todo:
            * Is not finished.
        """
        violations = cls.objects.none()
        if opened:
            violations |= cls.objects.filter(
                Q(status__lt=110) &
                Q(status__gt=-110)
            )
        if closed:
            violations |= violations.filter(
                Q(status__gte=110) |
                Q(status__lte=-110)
            )
        return violations

    def save(self, *args, **kwargs):
        """Todo

        Returns:
            [type]: [description]
        """
        self.modified_date = timezone.now()
        if self.pk is None:
            self.pub_date = timezone.now()
        super().save(*args, **kwargs)
        return self

    def __str__(self):
        """Returns the violoation's content.

        Returns:
            str: The violation's content.
        """
        return self.content.__str__()

    def get_absolute_url(self):
        """Todo

        Returns:
            [type]: [description]
        """
        return reverse('users:violation-resolve', args=[], kwargs={'pk': self.pk})

    def url(self):
        """Todo

        Returns:
            [type]: [description]
        """
        return self.get_absolute_url()

    def content_url(self):
        """Todo

        Returns:
            [type]: [description]
        """
        if self.content_type.model == 'theorynode':
            return self.content.url()
        return None

    def get_status_str(self):
        """Todo

        Returns:
            [type]: [description]
        """
        return self.STATUS[self.get_status()]

    def is_unread(self):
        """Todo

        Returns:
            [type]: [description]
        """
        return self.status > 0

    def is_read(self):
        """Todo

        Returns:
            [type]: [description]
        """
        return self.status < 0

    def get_status(self):
        """Todo

        Returns:
            [type]: [description]
        """
        return abs(self.status)

    def mark_as_read(self):
        """Todo

        Returns:
            [type]: [description]
        """
        if self.is_unread():
            self.status = -abs(self.status)
            self.save()

    def mark_as_unread(self):
        """Todo

        Returns:
            [type]: [description]
        """
        if self.is_read():
            self.status = abs(self.status)
            self.save()

    def get_feedback(self):
        """Todo

        Args:
            exclude ([type], optional): [description]. Defaults to None.

        Returns:
            [type]: [description]
        """
        return self.feedback.all()

    def get_feedback_users(self, exclude=None):
        """Todo

        Args:
            exclude ([type], optional): [description]. Defaults to None.

        Returns:
            [type]: [description]
        """
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

    def get_type(self):
        """Todo

        Returns:
            [type]: [description]
        """
        return 'Violation'

    def get_poll_count(self, cache=True):
        """Todo

        Args:
            cache (bool, optional): [description]. Defaults to True.

        Returns:
            [type]: [description]
        """
        # check cache first cache
        if self.saved_count is not None:
            return self.saved_count
        # count
        count = []
        for action_id, action in self.VOTES01:
            count.append([self.votes.filter(action=action_id).count(), action_id, action])
        # cache
        if cache:
            self.saved_count = count
        return count

    def poll_is_done(self):
        """Todo

        Returns:
            [type]: [description]
        """
        if self.is_closed():
            return True
        else:
            today = datetime.datetime.today()
            end = self.pub_date + datetime.timedelta(days=10)
            end = datetime.datetime(
                year=end.year, month=end.month, day=end.day, hour=23, minute=59, second=59)
            return today > end

    def is_polling(self):
        """Todo

        Returns:
            [type]: [description]
        """
        return not self.poll_is_done()

    def get_poll_winner(self):
        """Todo

        Returns:
            [type]: [description]
        """
        votes = self.get_poll_count()
        for x in votes:
            x[0] = -x[0]
        votes = sorted(votes)
        return votes[0][1]

    def close_poll(self, user=None):
        """Todo

        Args:
            user ([type], optional): [description]. Defaults to None.

        Returns:
            [type]: [description]

        Todo:
            * Not finished.
            * Write is_up_for_demotion().
            * Write demote()
        """
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

    def is_open(self):
        """Todo

        Returns:
            [type]: [description]
        """
        return self.get_status() < 110

    def is_closed(self):
        """Todo

        Returns:
            [type]: [description]
        """
        return self.get_status() >= 110

    def is_strike(self):
        """Todo

        Returns:
            [type]: [description]
        """
        if self.is_open():
            return False
        return abs(self.status) == Violation.STATUS.ACCEPTED


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

    # Django model attributes
    user = models.ForeignKey(
        User, related_name='violation_feedback', on_delete=models.SET_NULL, null=True)
    violation = models.ForeignKey(
        Violation, related_name='feedback', on_delete=models.CASCADE)
    action = models.SmallIntegerField(choices=ACTIONS01, default=0)
    comment = models.CharField(max_length=750, blank=True)
    timestamp = models.DateTimeField()

    class Meta:
        """Where the model options are defined.

        Model metadata is “anything that’s not a field”, such as ordering options (ordering),
        database table name (db_table), or human-readable singular and plural names
        (verbose_name and verbose_name_plural). None are required, and adding class Meta to a
        model is completely optional.

        For more, see: https://docs.djangoproject.com/en/3.0/ref/models/options/
        """
        db_table = 'users_violation_feedback'
        verbose_name = 'Violation Feedback'
        verbose_name_plural = 'Violation Feedback'
        ordering = ['timestamp']

    def __str__(self):
        """Returns violation's offender.

        Returns:
            str: The violation's offender.
        """
        s = '%s: %s %s (%s)' % (
            self.violation.pub_date,
            self.user,
            self.get_action().lower(),
            self.violation.offender.__str__(),
        )
        s = s.strip().strip(':')
        return s

    def save(self, *args, **kwargs):
        """Todo

        Returns:
            [type]: [description]
        """
        self.timestamp = timezone.now()
        super().save(*args, **kwargs)
        return self

    def get_action(self):
        """Todo

        Returns:
            [type]: [description]
        """
        try:
            return self.ACTIONS00[self.action]
        except KeyError:
            return 'Error'

    def get_comment(self, cache=True):
        """Todo

        Args:
            cache (bool, optional): [description]. Defaults to True.

        Returns:
            [type]: [description]
        """
        if cache and self.saved_comment is not None:
            return self.saved_comment
        try:
            comment = self.comment.split('/', 2)[2]
        except IndexError:
            comment = ''
        if cache:
            self.saved_comment = comment
        return comment

    def get_intent(self, cache=True):
        """Todo

        Args:
            cache (bool, optional): [description]. Defaults to True.

        Returns:
            [type]: [description]
        """
        if cache and self.saved_intent is not None:
            return self.saved_intent
        try:
            intent = int(self.comment.split('/', 2)[0])
            intent = Violation.INTENTIONS[intent]
        except IndexError:
            intent = ''
        if cache:
            self.saved_intent = intent
        return intent

    def get_offences(self, cache=True):
        """Todo

        Args:
            cache (bool, optional): [description]. Defaults to True.

        Returns:
            [type]: [description]
        """
        if self.saved_offences is not None:
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


class ViolationVote(models.Model):
    """Todo

    Attributes:
        user (User):
        violation (Violation):
        action (Violation.VOTES00):
    """

    # Django model attributes
    user = models.ForeignKey(
        User, related_name='violation_votes', on_delete=models.SET_NULL, null=True)
    violation = models.ForeignKey(
        Violation, related_name='votes', on_delete=models.CASCADE)
    action = models.SmallIntegerField(choices=Violation.VOTES00, default=0)

    class Meta:
        """Where the model options are defined.

        Model metadata is “anything that’s not a field”, such as ordering options (ordering),
        database table name (db_table), or human-readable singular and plural names
        (verbose_name and verbose_name_plural). None are required, and adding class Meta to a
        model is completely optional.

        For more, see: https://docs.djangoproject.com/en/3.0/ref/models/options/
        """
        db_table = 'users_violation_vote'
        verbose_name = 'Violation Vote'
        verbose_name_plural = 'Violation Votes'

    def __str__(self):
        """Returns violation's offender.

        Returns:
            str: The violation's offender.
        """
        result = '%s: %s (%s)' % (
            self.violation.__str__().strip('.'),
            self.user,
            self.violation.offender.__str__(),
        )
        return result

    def get_vote_str(self):
        """Todo

        Returns:
            [type]: [description]
        """
        return Violation.VOTES00[self.action]
