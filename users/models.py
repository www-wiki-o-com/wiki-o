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
import re
import datetime
import logging

from django.db import models
from django.urls import reverse
from django.contrib.auth.models import AbstractUser
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from users.utils import level_to_group
from core.utils import Choices, timezone_today, get_or_none

# *******************************************************************************
# Defines
# *******************************************************************************
POLL_LENGTH = 10
WARNING_EXPIRE_LENGTH = 10
STRIKE_EXPIRE_LENGTH = 100
LEVEL02_AGE_REQUIREMENT = 10
LEVEL03_AGE_REQUIREMENT = 100
LEVEL02_CONTRIBUTIONS_REQUIREMENT = 10
LEVEL03_CONTRIBUTIONS_REQUIREMENT = 100

LOGGER = logging.getLogger('django')

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
    """Wiki-O's extended user model.

    Class attributes:
        SYSTEM_USER_PK (int): A constant that keeps track of the system user's primary key. When
            the system is brought up, the value is initialized to -1. On the first call to
            get_system_user(), the "constant" is updated.

    Inheritied model attributes:
        username (CharField): The user's handle.
        date_joined (DateField): The date the user joined.

    Model attributes:
        sex (CharField): An optional field for describing the user's sex.
        location (CharField): An optional field for describing the user's location.
        religion (CharField): An optional field for describing the user's religion.
        politics (CharField): An optional field for describing the user's political alignment.
        fullname (CharField): An optional field for describing the user's fullname.
        birth_date (DateField): An optional datefield used to capture the user's birthdate.

        hidden (BooleanField): A field for hiding or revealing the user's handle (username).
        sex_visible (BooleanField): A field for hiding or revealing the user's sex.
        location_visible (BooleanField): A field for hiding or revealing the user's location.
        religion_visible (BooleanField): A field for hiding or revealing the user's religion.
        politics_visible (BooleanField): A field for hiding or revealing the user's political
            alignment.
        fullname_visible (BooleanField): A field for hiding or revealing the user's fullname.
        birth_date_visible (BooleanField): A field for hiding or revealing the user's birthdate.
        use_wizard (BooleanField): A prefence field for the user's opinion editor.

        utilized (QuerySet:Content): The set of theories that the user has formed an opinion on.
        contributions (QuerySet:Content): The set of content that the user created or
            collaborated on.

    Related model attributes:
        groups (Group): The set of permission groups the user belongs to (used for user level
            access).
        violations (QuerySet:Violation): The set of violations the user has been flagged for.
    """

    # Class attributes
    SYSTEM_USER_PK = -1

    # Model attributes
    sex = models.CharField(max_length=60, blank=True)
    location = models.CharField(max_length=60, blank=True)
    religion = models.CharField(max_length=60, blank=True)
    politics = models.CharField(max_length=60, blank=True)
    fullname = models.CharField(max_length=60, blank=True)
    birth_date = models.DateField(null=True, blank=True)

    hidden = models.BooleanField(default=False)
    sex_visible = models.BooleanField(default=False)
    location_visible = models.BooleanField(default=False)
    religion_visible = models.BooleanField(default=False)
    politics_visible = models.BooleanField(default=False)
    fullname_visible = models.BooleanField(default=False)
    birth_date_visible = models.BooleanField(default=False)

    use_wizard = models.BooleanField(default=True)
    utilized = models.ManyToManyField('theories.Content', related_name='users', blank=True)
    contributions = models.ManyToManyField('theories.Content',
                                           related_name='collaborators',
                                           blank=True)

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

    def get_long(self):
        """A getter for the user's fullname if visible, otherwise the user's handle.

        Returns:
            str: The user's fullname.
        """
        return self.__str__(print_fullname=True)

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

    def get_age(self):
        """Calculate age if not hidden.

        Returns:
            str: The user's age if not hidden, 'N/A' otherwise.
        """
        if self.birth_date is not None and self.birth_date_visible:
            born = self.birth_date
            today = timezone_today()
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

    def is_using(self, content, refresh=False):
        """A query to see if the user has an opinion on the provided theory.

        Args:
            content (Content): A reference to the theory in question.
            refresh (bool, optional): If true, refresh the database's cache. Defaults to False.

        Returns:
            Bool: True, if the user has an opinion on the theory.
        """
        if refresh:
            if (self.opinions.filter(content=self, deleted=False).exists() or
                    self.opinions.filter(dependencies__content=self).exists()):
                self.utilized.add(content)
                return True
            self.utilized.remove(content)
            return False
        return self.utilized.filter(id=content.pk).exists()

    def get_violations(self, warnings=True, strikes=True, recent=True, expired=False):
        """A getter for the user's violations.

        This method cannot be called without at least recent=True or expired=True.

        Args:
            warnings (bool, optional): If true, include warnings. Defaults to True.
            strikes (bool, optional): If true, include strikes. Defaults to True.
            recent (bool, optional): If true, include matching violations within the last
                STRIKE_EXPIRE_LENGTH days. Defaults to True.
            expired (bool, optional): If true, include matching violations that have expired
                (older than STRIKE_EXPIRE_LENGTH days). Defaults to False.

        Returns:
            QuerySet:Violatoin: The set of violations.
        """
        return Violation.get_violations(content=self,
                                        warnings=warnings,
                                        strikes=strikes,
                                        recent=recent,
                                        expired=expired)

    def count_reported(self,
                       ignored=False,
                       is_open=True,
                       is_closed=True,
                       recent=True,
                       expired=False):
        """A getter for the number of violations the user reported.

        Args:
            ignored (bool, optional): If true, count the set of ignored violations.
                Defautls to False.
            recent (bool, optional): If true, include the set of recent violations.
                Defaults to True.
            expired (bool, optional): If true, include the expired set of violations.
                Defaults to True.

        Returns:
            int: The count.
        """
        query_set = self.reported_violations.all()
        if is_open and not is_closed:
            query_set = query_set.filter(status__in=Violation.STATUS_OPEN.get_values())
        elif is_closed and not is_open:
            query_set = query_set.filter(status__in=Violation.STATUS_CLOSED.get_values())
        if ignored:
            query_set = self.reported_violations.filter(status=Violation.STATUS.IGNORED)
        if recent and not expired:
            expiry_date = timezone.now() - datetime.timedelta(days=STRIKE_EXPIRE_LENGTH)
            query_set = query_set.filter(close_date__gte=expiry_date)
        elif expired and not recent:
            expiry_date = timezone.now() - datetime.timedelta(days=STRIKE_EXPIRE_LENGTH)
            query_set = query_set.filter(close_date__lt=expiry_date)
        return query_set.count()

    def count_open_reports(self):
        """A getter for the number of violations the user reported that are still open.

        Returns:
            int: The count.
        """
        return self.count_reported(is_open=True, is_closed=False)

    def count_ignored_reports(self, recent=True, expired=False):
        """A getter for the number of violations the user reported and that have been ignored.

        Args:
            recent (bool, optional): If true, include the set of recent violations.
                Defaults to True.
            expired (bool, optional): If true, include the expired set of violations.
                Defaults to True.

        Returns:
            int: The count.
        """
        return self.count_reported(ignored=True, recent=recent, expired=expired)

    def count_warnings(self, recent=True, expired=False):
        """A getter for the number of warnings the user recieved.

        Args:
            recent (bool, optional): If true, include the set of recent violations.
                Defaults to True.
            expired (bool, optional): If true, include the expired set of violations.
                Defaults to True.

        Returns:
            int: The count.
        """
        return self.get_violations(warnings=True, strikes=False, recent=recent,
                                   expired=expired).count()

    def count_strikes(self, recent=True, expired=False):
        """A getter for the number of strikes the user has recieved.

        Args:
            recent (bool, optional): If true, include the set of recent violations.
                Defaults to True.
            expired (bool, optional): If true, include the expired set of violations.
                Defaults to True.

        Returns:
            int: The count.
        """
        return self.get_violations(warnings=False, strikes=True, recent=recent,
                                   expired=expired).count()

    def get_account_age(self):
        """A getter for the account's age.

        Returns:
            int: The account age in days.
        """
        age = timezone.now() - self.date_joined()
        return age.days

    def get_num_contributions(self):
        """A getter for the number of contributions by the user.

        Returns:
            int: The count.
        """
        return self.contributions.count()

    def get_level(self):
        """A getter for the user's level.

        Returns:
            int: The user's level.
        """
        if len(self.get_levels()) > 0:
            return self.get_levels()[-1]
        else:
            return -1

    def get_levels(self):
        """A getter for the user's permission levels.

        The user groups are named "user level: #".

        Returns:
            list: An ordered list of the user's levels.
        """
        levels = []
        for group in self.groups.values('name'):
            group_name = group['name']
            if re.match(r'^user level: \d+$', group_name):
                levels.append(int(re.search(r'\d+', group_name).group()))
        return sorted(levels)

    def is_up_for_promotion(self):
        """A getter for the user's promotion status.

        Returns:
            bool: True, if the user is up for promotion.
        """
        if self.count_warnings(recent=True, expired=False) > 0 or \
            self.count_strikes(recent=True, expired=False) > 0:
            return False
        if self.get_level() == 1 and self.get_account_age() >= LEVEL02_AGE_REQUIREMENT \
           and self.get_num_contributions() >= LEVEL02_CONTRIBUTIONS_REQUIREMENT:
            return True
        if self.get_level() == 2 and self.get_account_age() >= LEVEL03_AGE_REQUIREMENT \
           and self.get_num_contributions() >= LEVEL03_CONTRIBUTIONS_REQUIREMENT:
            return True
        return False

    def promote(self, new_level=None):
        """Add the user to the next level group.

        User permissions are handeled by user groups.
        Note, there are actually 5 levels (0,1,2,3,4) but level 4 is only applied through the
        admin interface.

        Args:
            new_level (int, optional): If provided, the user is promoted the provided level
                (primarily used for testing). Defaults to None.

        Returns:
            int: The user's new level.
        """
        if new_level is None:
            new_level = min(3, self.get_level() + 1)
        group = level_to_group(new_level)
        self.groups.add(group)

    def is_up_for_demotion(self):
        """A getter for the user's demotion status.

        Returns:
            bool: True, if the user is up for demotion.
        """
        if self.count_strikes(recent=True, expired=False) >= 3:
            return True
        return False

    def demote(self, new_level=None):
        """Demote the user.

        Args:
            new_level (int, optional): If provided, the user will be demoted to the provided level
                (primarily used for testing). Defaults to None.
        """
        current_level = self.get_level()
        if new_level is None:
            new_level = max(0, current_level - 1)
        while current_level > new_level:
            group = level_to_group(current_level)
            self.groups.remove(group)
            current_level = self.get_level()
        if current_level < new_level:
            group = level_to_group(new_level)
            self.groups.add(group)


class Violation(models.Model):
    """A user violation.

    This class is the container for the violation report, all viloation feedback from the users,
    and the finial decision.

    Attributes:
        saved_count (int or None): Cached count.

    Class constants:
        The class constants are used map predefined actions, intents, and offences to integers.
        In the case that there are two Choices containers for the same field, one is for choosing
        an action and the other for displaying the choice.

    Model attributes:
        offender (User): The user that was reported for the violation.
        pub_date (DateTimeField): The date the user was reported.
        modified_date (DateTimeField): The last time the violation was updated.
        close_date (DateTimeField): The close/closed date of the poll.

        content(GenericModel): The conent that the violoation was reported on.
        object_id(int): The primary key/id of the content that the violation was reported for
            (used by GenericModel).
        content_type(ContentType): The type of the violated content (used by GenericModel).

        status (STATUS): The status of the violation. A negative value indicates that the user
            has not acknowledged the update.
        read (Bool):

    Related model attributes:
        votes (ViolationVote): The set of user votes on the violation.
        feedback (ViolationFeedback): The set of feedback on the violation.
        violations (Violation): The set of resolution violations commited by the committee in
            charge of this resolution.
    """

    # Class constants
    STATUS_OPEN = Choices(
        (100, "REPORTED", ("Pending")),
        (101, "POLLING", ("Polling")),
        (102, "PENDING", ("Pending")),
    )
    STATUS_WARNINGS = Choices((120, "WARNING", ("Warning")),)
    STATUS_STRIKES = Choices((130, "STRIKE", ("Strike")),)
    STATUS_VIOLATIONS = STATUS_WARNINGS + STATUS_STRIKES
    STATUS_CLOSED = Choices((110, "IGNORED", ("Ignored")),) + STATUS_VIOLATIONS
    STATUS = STATUS_OPEN + STATUS_CLOSED

    # ********************************
    # Model attributes
    # ********************************

    # The user that was reported for the violation.
    offender = models.ForeignKey(User, related_name='violations', on_delete=models.CASCADE)
    reporter = models.ForeignKey(User, related_name='reported_violations', on_delete=models.CASCADE)
    pub_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(models.SET_NULL, blank=True, null=True)
    close_date = models.DateTimeField(models.SET_NULL, blank=True, null=True)

    # The violated content.
    object_id = models.PositiveIntegerField()
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    content = GenericForeignKey('content_type', 'object_id')

    # The current status of the violation.
    status = models.SmallIntegerField(choices=STATUS, default=STATUS.REPORTED)
    read = models.BooleanField(default=False)

    # The set of violations against this violation/resolution.
    violations = GenericRelation('Violation')

    # Cache attributes.
    saved_count = None

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

        # The set of permissions to enter into the permissions table when creating this object.
        # Add, change, delete, and view permissions are automatically created for each model.
        permissions = (
            ('can_vote_violation', 'Can vote.'),
            ('can_report_violation', 'Can report.'),
            ('can_comment_violation', 'Can comment.'),
            ('can_resolve_violation', 'Can resolve.'),
        )

    @classmethod
    def get_violations(cls,
                       content=None,
                       is_open=True,
                       is_closed=True,
                       warnings=True,
                       strikes=True,
                       recent=True,
                       expired=True):
        """A getter for violations.

        This method cannot be called without at least is_open=True or is_closed=True, at least
        warnings or strikes, and at least recent=True or expired=True.

        Args:
            is_open (bool, optional): If true, the result will include all open violations.
                Defaults to True.
            is_closed (bool, optional): If true, the result will include all closed violations.
                Defaults to True.
            warnings (bool, optional): If true, include the set of user warnings. Defaults to True.
            strikes (bool, optional): If true, include the set of user stikes. Defaults to True.
            recent (bool, optional): If true, include the set of recent violations.
                Defaults to True.
            expired (bool, optional): If true, include the expired set of violations.
                Defaults to True.

        Returns:
            QuerySet:Violation: The set of violatoins.
        """
        # Preconditions.
        assert is_open or is_closed
        assert recent or expired

        # Find all violations for the provided content.
        if content is None:
            query_set = cls.objects.all()
        else:
            content_type = ContentType.objects.get_for_model(content.__class__)
            query_set = cls.objects.filter(object_id=content.id, content_type=content_type)

        # Filter by status.
        if is_open and not is_closed:
            query_set &= query_set.filter(status__in=cls.STATUS_OPEN.get_values())
        if is_closed and not is_open:
            query_set &= query_set.filter(status__in=cls.STATUS_CLOSED.get_values())

        # Filter by type.
        if warnings:
            warning_query_set = query_set.filter(status=Violation.STATUS.WARNING)
            # Filter by date.
            if recent and not expired:
                expiry_date = timezone.now() - datetime.timedelta(days=WARNING_EXPIRE_LENGTH)
                warning_query_set = warning_query_set.filter(close_date__gte=expiry_date)
            elif expired and not recent:
                expiry_date = timezone.now() - datetime.timedelta(days=WARNING_EXPIRE_LENGTH)
                warning_query_set = warning_query_set.filter(close_date__lt=expiry_date)
            query_set |= warning_query_set
        if strikes:
            stike_query_set = query_set.filter(status=Violation.STATUS.STRIKE)
            # Filter by date.
            if recent and not expired:
                expiry_date = timezone.now() - datetime.timedelta(days=STRIKE_EXPIRE_LENGTH)
                stike_query_set = stike_query_set.filter(close_date__gte=expiry_date)
            elif expired and not recent:
                expiry_date = timezone.now() - datetime.timedelta(days=STRIKE_EXPIRE_LENGTH)
                stike_query_set = stike_query_set.filter(close_date__lt=expiry_date)
            query_set |= stike_query_set

        # Return
        return query_set

    def save(self, *args, **kwargs):
        """Updates the modified_date.

        Returns:
            Violation: A reference to the object (self).
        """
        self.modified_date = timezone.now()
        super().save(*args, **kwargs)
        return self

    def __str__(self):
        """Returns the violoation's content.

        Returns:
            str: The violation's content.
        """
        return "Violation #%d (%s)" % (self.id, self.get_status_str())

    def get_absolute_url(self):
        """A getter for the violation's url.

        Returns:
            str: The url.
        """
        return reverse('users:violation-resolve', kwargs={'pk': self.pk})

    def url(self):
        """A getter for the violation's url.

        Returns:
            str: The url.
        """
        return self.get_absolute_url()

    def get_status_str(self):
        """A getter for the violation's status.

        Returns:
            str: The status.
        """
        return self.STATUS[self.status]

    def is_read(self):
        """A getter for the read status.

        Returns:
            bool: True if the status is read.
        """
        return self.read

    def is_unread(self):
        """A getter for the unread status.

        Returns:
            bool: True the status is unread.
        """
        return not self.read

    def mark_as_read(self):
        """Transition the status to read."""
        if not self.read:
            self.read = True
            self.save()

    def mark_as_unread(self):
        """Transition the status to unread."""
        if self.read:
            self.read = False
            self.save()

    def get_feedback_users(self, exclude=None):
        """A getter for the set of users that provided feedback.

        Args:
            exclude (list[User] or User, optional): If provided, the user(s) in exclude will not
            have their feedback returned. Defaults to None.

        Returns:
            QuerySet:User: The feedack.
        """
        users_pk = []
        for x in self.feedback.all():
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

    def get_poll_votes(self, cache=True):
        """A getter for the poll's votes.

        Args:
            cache (bool, optional): If true, store the count in cache. Defaults to True.

        Returns:
            VOTE_OUTCOMES: The set of votes.
        """
        # Return the cached result if present.
        if self.saved_count is not None:
            return self.saved_count
        # Get the count.
        count = []
        for vote_id, vote in ViolationVote.VOTE_OUTCOMES:
            count.append([self.votes.filter(vote=vote_id).count(), vote_id, vote])
        # Save to cache.
        if cache:
            self.saved_count = count
        return count

    def poll_is_done(self):
        """A getter for the poll's status.

        Returns:
            bool: True, if the poll is done.
        """
        if self.is_closed():
            return True
        return timezone.now() > self.close_date

    def get_poll_outcome(self):
        """A getter for the poll's tally.

        Returns:
            STATUS: The vote with the most backing and if there is a tie, the vote with the most
                severe outcome.
        """
        votes = sorted(self.get_poll_votes(), key=lambda x: [-x[0], x[1]])
        return votes[0][1]

    def open_poll(self, user=None, log_feedback=True):
        """A method for updating the poll.

        Args:
            user (User, optional): If provided, the user will be applied to the feedback log.
                Defaults to None.
            log_feedback (bool, optional): If true, a feedback log will be created.
                Defaults to True.
        """
        # Setup
        if user is None:
            user = User.get_system_user()
        # Update close date
        end = timezone.now() + datetime.timedelta(days=POLL_LENGTH)
        end = datetime.datetime(year=end.year,
                                month=end.month,
                                day=end.day,
                                hour=23,
                                minute=59,
                                second=59,
                                tzinfo=datetime.timezone.utc)
        self.close_date = end
        self.save()
        # Log feedback.
        if log_feedback:
            data = ViolationFeedback.pack_data(ViolationFeedback.OPEN_ACTION_CHOICES.OPEN_POLL)
            self.feedback.create(
                user=user,
                data=data,
            )

    def close_poll(self, user=None, log_feedback=True):
        """A method for updating the poll.

        Args:
            user (User, optional): If provided, the user will be applied to the feedback log.
                Defaults to None.
            log_feedback (bool, optional): If true, a feedback log will be created.
                Defaults to True.

        Returns:
            STATUS: The result of the poll.
        """
        # Setup
        if user is None:
            user = User.get_system_user()
        # Close
        if self.is_open():
            self.close_date = timezone.now()
        self.status = self.get_poll_outcome()
        LOGGER.info('Violation[%d].close_poll: poll_outcome %s', self.id, self.get_status_str())
        self.save()
        # Log feedback.
        if log_feedback:
            data = ViolationFeedback.pack_data(
                action_key=ViolationFeedback.OPEN_ACTION_CHOICES.CLOSE_POLL,
                comment='Outcome, %s' % self.get_status_str())
            self.feedback.create(
                user=user,
                data=data,
            )
        # Demote
        if self.status == Violation.STATUS.STRIKE and self.offender.is_up_for_demotion():
            self.offender.demote()
            LOGGER.info('Violation[%d].close_poll: demoted', self.id)
        # Done
        return self.status

    def override_status(self, status, user=None, log_feedback=False):
        """A method for updating the poll.

        Args:
            status (STATUS): The status used to update the violation.
            user (User, optional): If provided, the user will be applied to the feedback log.
                Defaults to None.
            log_feedback (bool, optional): If true, a feedback log will be created.
                Defaults to True.
        """
        # Setup
        if user is None:
            user = User.get_system_user()
        # Close
        if self.is_open():
            self.close_date = timezone.now()
            data = ViolationFeedback.pack_data(
                action_key=ViolationFeedback.OPEN_ACTION_CHOICES.CLOSE_POLL)
            self.feedback.create(
                user=user,
                data=data,
            )
        self.status = status
        LOGGER.info('Violation[%d].override_status: %s', self.id, self.get_status_str())
        self.save()
        # Log feedback.
        if log_feedback:
            data = ViolationFeedback.pack_data(action_key=status)
            self.feedback.create(
                user=user,
                data=data,
            )
        # Demote
        if self.status == Violation.STATUS.STRIKE and self.offender.is_up_for_demotion():
            self.offender.demote()
            LOGGER.info('Violation[%d].override_status: demoted', self.id)

    def is_open(self):
        """A getter fot the poll's status.

        Returns:
            Bool: True if the poll is still open.
        """
        return self.status in self.STATUS_OPEN

    def is_closed(self):
        """A getter fot the poll's status.

        Returns:
            Bool: True if the poll is closed.
        """
        return not self.is_open()


class ViolationFeedback(models.Model):
    """A container for feedback on user violations.

    Class constants:
        The class constants are used map predefined actions, intents, and offences to integers.
        In the case that there are two Choices containers for the same field, one is for choosing
        an action and the other for displaying the choice.

    Model attributes:
        user (User): The user providing the feedback.
        violation (Violation): A pointer to the violation.
        pub_date (Datetime): The publication date of the feedback.
        data (str): The container's feedback. The data contains feedback about the user's action,
            the offender's intent, a list of the offender's offences, and the user's justfication.
            The four fields are seperated by /'s characters.
    """

    # Class constants
    ACTION_FEEDBACK = Choices(
        (0, "NO_ACTION", ("Comment")),
        (100, "REPORTED", ("Reported Violation")),
        (101, "OPENED_POLL", ("Opened Poll")),
        (102, "CLOSED_POLL", ("Closed Poll")),
        (110, "IGNORED", ("Veto - Ignored")),
        (120, "WARNING", ("Veto - Warning")),
        (130, "STRIKE", ("Veto - Strike")),
    )

    VETO_ACTION_CHOICES = Choices(
        (0, "NO_ACTION", ("----")),
        (110, "IGNORE", ("Veto - Ignore")),
        (120, "WARN", ("Veto - Warn")),
        (130, "STRIKE", ("Veto - Strike")),
    )

    OPEN_ACTION_CHOICES = VETO_ACTION_CHOICES + Choices(
        (102, "CLOSE_POLL", ("Close the poll and tally the vote")),)

    CLOSED_ACTION_CHOICES = VETO_ACTION_CHOICES + Choices((101, "OPEN_POLL", ("Reopen the poll")),)

    INTENTIONS = Choices(
        ("", "----"),
        (10, "Unintentional"),
        (20, "Careless"),
        (30, "Adversarial"),
    )

    THEORY_OFFENCES = Choices(
        (110, "Provided commentary (leading, etc)."),
        (115, "Provided non-Wiki-O content."),
        (120, "Reverted sound content."),
        (125, "Unnecessarily added or removed evidence."),
        (130, "Performed unnecessary action (swap, convert, merge)."),
    )

    EVIDENCE_OFFENCES = THEORY_OFFENCES + Choices(
        (135, "Missclassified evidence (verifiable field)."),)

    RESOLUTION_OFFENCES = Choices(
        (210, "Filed a violation without proper cause."),
        (215, "Spamming the comments and/or reports."),
        (220, "Voted with an ulterior agenda."),
        (225, "Unnecessarily overrode the poll (only applies to level 4 users)."),
    )

    OFFENCE_CHOICES = THEORY_OFFENCES + EVIDENCE_OFFENCES + RESOLUTION_OFFENCES

    # Model attributes
    user = models.ForeignKey(User,
                             related_name='violation_feedback',
                             on_delete=models.SET_NULL,
                             null=True)
    violation = models.ForeignKey(Violation, related_name='feedback', on_delete=models.CASCADE)
    data = models.CharField(max_length=750, blank=True)
    pub_date = models.DateTimeField()

    # Cache attributes
    saved_action_key = None
    saved_intent_key = None
    saved_comment = None
    saved_offence_keys = None

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
        ordering = ['pub_date']

    @classmethod
    def pack_data(cls, action_key=0, intent_key=0, offence_keys=None, comment=''):
        """Pack the input data into a string.

        Args:
            action_key (OPEN_ACTION_CHOICES, optional): The user's action (e.g. comment, close poll,
                ...). Defaults to 0.
            intent_key (INTENTIONS, optional): The intention as precieved by the user.
                Defaults to 0.
            offence_keys (OFFENCE_CHOICES, optional): A list of offences. Defaults to None.
            comment (str, optional): The user's comment. Defaults to ''.

        Returns:
            str: The packed string.
        """
        action_key = str(action_key)
        intent_key = str(intent_key)
        if offence_keys is None:
            offence_keys = ''
        offence_keys = str(offence_keys).strip('[').strip(']').replace("'", '').replace(' ', '')
        return '%s/%s/%s/%s' % (action_key, intent_key, offence_keys, comment)

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
        """Updates the pub_date.

        Returns:
            ViolationFeedback: A reference to the object (self).
        """
        self.pub_date = timezone.now()
        super().save(*args, **kwargs)
        return self

    def unpack_data(self):
        """A method for unpacking self.data.

        The data string contains the feedback action, intent, offences, and a comment. The data
        is separated by /'s.

        Returns:
            Bool: True if the data was properly unpacked.
        """
        # Setup
        self.saved_action_key = 0
        self.saved_intent_key = 0
        self.saved_offence_keys = []
        self.saved_comment = ''
        x = self.data.split('/')
        # Preconditions
        if len(x) != 4:
            return False
        # Action
        if re.match(r'^\d+$', x[0]):
            self.saved_action_key = int(x[0])
        # Intent
        if re.match(r'^\d+$', x[1]):
            self.saved_intent_key = int(x[1])
        # Offences
        self.saved_offence_keys = [int(x) for x in re.findall(r'\d+', x[2])]
        # Comment
        self.saved_comment = x[3]
        # Done
        return True

    def get_action(self):
        """A getter for the feedback action (comment, veto, ...).

        Returns:
            str: The action.
        """
        if self.saved_action_key is None:
            self.unpack_data()
        try:
            return self.ACTION_FEEDBACK[self.saved_action_key]
        except KeyError:
            return None

    def get_intent(self):
        """A getter for the percieved intent.

        Returns:
            [str]: The intent.
        """
        if self.saved_intent_key is None:
            self.unpack_data()
        try:
            return self.INTENTIONS[self.saved_intent_key]
        except KeyError:
            return None

    def get_offences(self):
        """A getter for the list of offences.

        Returns:
            [str]: A list of offences.
        """
        offences = []
        if self.saved_offence_keys is None:
            self.unpack_data()
        for offcence_key in self.saved_offence_keys:
            try:
                offences.append(ViolationFeedback.OFFENCE_CHOICES[offcence_key])
            except KeyError:
                offences.append('Error')
        return offences

    def get_comment(self):
        """A getter for the comment.

        Returns:
            str: The comment.
        """
        if self.saved_comment is None:
            self.unpack_data()
        return self.saved_comment


class ViolationVote(models.Model):
    """A container for keeping track of user votes.

    Class constants:
        The class constants are used map predefined actions, intents, and offences to integers.
        In the case that there are two Choices containers for the same field, one is for choosing
        an action and the other for displaying the choice.

    Attributes:
        user (User): The user making a vote on the violation.
        violation (Violation): The violation linked to the vote.
        vote (Violation.VOTES_CHOICES): The user's vote.
    """

    # Class constants
    VOTE_OUTCOMES = Choices(
        (110, 'IGNORE', ('Ignore')),
        (120, 'WARN', ('Warn')),
        (130, 'STRIKE', ('Strike')),
    )
    VOTE_CHOICES = Choices((0, "NO_VOTE", ("----")),) + VOTE_OUTCOMES

    # Model attributes
    user = models.ForeignKey(User,
                             related_name='violation_votes',
                             on_delete=models.SET_NULL,
                             null=True)
    violation = models.ForeignKey(Violation, related_name='votes', on_delete=models.CASCADE)
    vote = models.SmallIntegerField(choices=VOTE_CHOICES, default=0)

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
        """Converts the vote value to a human readable string.

        Returns:
            string: The string.
        """
        return self.VOTE_CHOICES[self.vote]
