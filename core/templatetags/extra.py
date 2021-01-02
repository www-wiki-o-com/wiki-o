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

from django import template
from django.utils.safestring import mark_safe
from django.utils.http import urlencode
from django.utils import timezone
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType
from notifications.models import Notification
from misaka import Markdown, SaferHtmlRenderer

# *******************************************************************************
# Defines
# *******************************************************************************
register = template.Library()

RE_STATS = r'(opinion_all|opinion_supporters|opinion_moderates|opinion_opposers)'
RE_WIKI_O_URL = r'(https?://)?(www\.)?(m\.)?wiki-o\.com/'
RE_WIKI_O_URL += r'(theory/\d+|evidence/\d+|opinion/\d+|opinion/\d+/vs/\d+'
RE_WIKI_O_URL += r'|opinion/\d+/vs/%s' % RE_STATS
RE_WIKI_O_URL += r'|theory/\d+/%s' % RE_STATS
RE_WIKI_O_URL += r'|theory/%s/vs/\d+' % RE_STATS
RE_WIKI_O_URL += r'|theory/\d+/%s/vs/%s)/' % (RE_STATS, RE_STATS)
RE_WIKI_O = re.compile(RE_WIKI_O_URL)

# *******************************************************************************
# Methods
# *******************************************************************************


def get_brace_indices(text):
    """Parenthesized contents in text as pairs (level, contents).

    Args:
        text (str): The text to parse.

    Returns:
        list: A higherarcle list of the text based on the parenthesis.
    """
    stack = []
    result = []
    for i, c in enumerate(text):
        if c in ['[', '<', '{', '«']:
            stack.append((i, c))
        elif c == '>' and stack[-1][-1] == '<':
            start = stack.pop()[0]
            result.append((start, i, len(stack)))
        elif c == ']' and stack[-1][-1] == '[':
            start = stack.pop()[0]
            result.append((start, i, len(stack)))
        elif c == '}' and stack[-1][-1] == '{':
            start = stack.pop()[0]
            result.append((start, i, len(stack)))
        elif c == '»' and stack[-1][-1] == '«':
            start = stack.pop()[0]
            result.append((start, i, len(stack)))
    return result


def interpret_log_text(log, log_text, extra=''):
    """Interpret the variables and links encoded in the log text.

    Args:
        log (Log): The log to use to populate format strings.
        log_text ([type]): The log text to format.
        extra (str, optional): The extra set of params to add to url links. Defaults to ''.

    Returns:
        str: [description]
    """
    # Interpret brackets
    log_text = log_text.replace('{{', '{').replace('}}', '}')
    log_text = log_text.replace('<#', '«').replace('#>', '»')

    # Interpret variables
    result = ''
    prev_index = 0
    for start_index, end_index, _ in get_brace_indices(log_text):
        if log_text[start_index] == '{' and log_text[end_index] == '}':
            result += log_text[prev_index:start_index]
            name = log_text[start_index + 1:end_index].strip()
            if name == 'object' and log.action_object is not None:
                name = log.action_object.__str__()
            elif name == 'target' and log.target is not None:
                name = log.target.__str__()
            elif name == 'target.get_owner' and log.target is not None:
                name = log.target.get_owner()
            result += name
            prev_index = end_index + 1
    result += log_text[prev_index:]

    # Interpret links
    log_text = result
    result = ''
    prev_index = 0
    for start_index, end_index, _ in get_brace_indices(log_text):
        if log_text[start_index] == '«' and log_text[end_index] == '»':
            result += log_text[prev_index:start_index]
            url, name = log_text[start_index + 1:end_index].strip().split(' ', 1)
            name = name.strip()

            # url
            add_date = False
            if url == 'object.url' and log.action_object is not None:
                url = log.action_object.url()
            if url == 'object.a_url' and log.action_object is not None:
                url = log.action_object.activity_url()
                add_date = True
            elif url == 'target.url' and log.target is not None:
                url = log.target.url()
            elif url == 'target.a_url' and log.target is not None:
                url = log.target.activity_url()
                add_date = True
            # date
            if add_date:
                date = log.timestamp - datetime.timedelta(seconds=30)
                date = date.strftime('%Y-%m-%d %X')
                if extra == '':
                    extra += '?' + urlencode({'date': date})
                else:
                    extra += '&' + urlencode({'date': date})
            # add extra
            if len(extra) > 0:
                url += extra
            # redirect to mark notification as read
            if isinstance(log, Notification):
                mark_as_read_url = reverse('notifications:mark_as_read', kwargs={'slug': log.slug})
                url = mark_as_read_url + '?next=' + url

            # link
            result += '<a class="plain" href="%s">%s</a>' % (url, name)
            prev_index = end_index + 1
    result += log_text[prev_index:]
    return result


def make_safe(text):
    """Remove all unsafe http characters from the text.

    Args:
        text (str): Raw text.

    Returns:
        str: Safe text.
    """
    result = text.replace('{', '[[').replace('}', ']]')
    result = result.replace('<', '&lt;').replace('>', '&gt;')
    return result


# *******************************************************************************
# filters
#
#
#
#
#
# *******************************************************************************


@register.filter
def possessive(string):
    """Add the possesive 's or ' to the end of the string.

    Args:
        string (str): The input string to manipulate.

    Returns:
        str: The input string now with possesive qualifier.
    """
    string = str(string)
    if string[-1] == 's':
        return string + "'"
    return string + "'s"


@register.filter
def remove_punctuation(string):
    """Removes the punctuation.

    Args:
        string (str): The input string to manipulate.

    Returns:
        str: The input string now without punctuation.
    """
    string = str(string)
    if re.match(r'.*[.!]', string):
        return string[:-1]
    return string


@register.filter
def float_to_percent(x):
    """[summary]

    Args:
        x ([type]): [description]

    Returns:
        [type]: [description]
    """
    try:
        x = float(x)
    except ValueError:
        x = 0.0
    return str(int(round(x * 100)))


@register.filter
def get_class(obj):
    """Retrieves the object class.

    Args:
        obj (Generic): The input object.

    Returns:
        str: The object class string.
    """
    return obj.__class__.__name__


@register.filter
def follow_url(obj):
    """Retrive the url for subcribing to the object.

    Args:
        obj (Generic): The input object.

    Returns:
        str: The url.
    """
    content_type = ContentType.objects.get_for_model(obj)
    return reverse(
        'activity:follow',
        kwargs={
            'content_type_id': content_type.pk,
            'object_id': obj.pk
        },
    )


@register.filter
def unfollow_url(obj):
    """Retrive the url for unsubcribing from the object.

    Args:
        obj (Generic): The input object.

    Returns:
        str: The url.
    """
    content_type = ContentType.objects.get_for_model(obj)
    return reverse(
        'activity:unfollow',
        kwargs={
            'content_type_id': content_type.pk,
            'object_id': obj.pk
        },
    )


@register.filter
def long_details(detail_text):
    """Formats the detail text.

    Args:
        detail_text (str): The un-rendered detail text.
        autoescape (bool, optional): If true, applies autoescape. Defaults to True.

    Returns:
        str: The rendered output text.
    """
    rendered_text = render_details(detail_text)
    return mark_safe(rendered_text)


@register.filter
def short_details(detail_text, length=500):
    """Formats the detail and cuts it off at length.

    Args:
        detail_text (str): The raw input text.
        length (int, optional): The max length of the output text. Defaults to 500.
        autoescape (bool, optional): If true, applies autoescape. Defaults to True.

    Returns:
        str: The formated output text.
    """
    # Shorten and render.
    if len(detail_text) > length:
        detail_text = detail_text[:length]
        i = detail_text.rfind(' ')
        detail_text = detail_text[:i] + '...'
    rendered_text = render_details(detail_text)
    return mark_safe(rendered_text)


@register.filter
def get_verb(log, extra=''):
    """Retrieves and formats the log's verb text.

    Args:
        log (Log): The log to extract the verb text from.
        extra (str, optional): The extra set of params to add to url links. Defaults to ''.

    Returns:
        str: The formated verb output text.
    """
    extra = str(extra)
    verb = interpret_log_text(log, log.verb, extra)
    if isinstance(log, Notification):
        if log.unread:
            verb = '<strong>' + verb + '</strong>'
        if log.level == 'warning':
            verb = '<font color="red">' + verb + '</font>'
    return mark_safe(verb)


@register.filter
def get_description(log, extra=''):
    """Retrieves and formats the log's description text.

    Args:
        log (Log): The log to extract the description text from.
        extra (str, optional): The extra set of params to add to url links. Defaults to ''.

    Returns:
        str: The formated description output text.
    """
    extra = str(extra)
    description = interpret_log_text(log, log.description, extra)
    return mark_safe(description)


@register.simple_tag
def url_extra(url, *args, extra='', **kwargs):
    """Add extra parameters to the url.

    Args:
        url (str): The input url.
        extra (str, optional): [description]. Defaults to ''.

    Returns:
        str: The url with the additional parameters.
    """
    resolved_url = reverse(url, None, args, kwargs)
    return resolved_url + extra


@register.simple_tag
def url_action(action, extra=''):
    """Retrive the url for the action object's stream.

    Args:
        action (Action): The action to extract the url from.
        extra (str, optional): The extra set of params to add to url links. Defaults to ''.

    Returns:
        str: The url.
    """
    resolved_url = action.action_object.activity_url()
    params = {'date': action.timestamp - datetime.timedelta(seconds=1)}
    extra = str(extra)
    if len(extra) > 0:
        extra += '&' + urlencode(params)
    else:
        extra += '?%s' % urlencode(params)
    return resolved_url + extra


@register.filter
def timepassed(time_then):
    """Construct a human readable string for time passed.

    Args:
        time_then (datetime): The time to compare against.

    Returns:
        str: The output text.
    """
    delta = timezone.now() - time_then
    # seconds
    seconds = delta.total_seconds()
    if seconds <= 90:
        return '%d secs' % seconds
    # minutes
    minutes = 1.0 * seconds / 60
    if minutes <= 3:
        return '%0.1f mins' % minutes
    if minutes <= 90:
        return '%d mins' % round(minutes)
    # hours
    hours = minutes / 60
    if hours <= 3:
        return '%0.1f hours' % hours
    if hours <= 36:
        return '%d hours' % round(hours)
    # days
    days = hours / 24
    if days < 3:
        return '%0.1f days' % days
    if days <= 10:
        return '%d days' % round(days)
    # weeks
    weeks = days / 7
    if weeks <= 3:
        return '%0.1f weeks' % weeks
    if weeks <= 6:
        return '%d weeks' % round(weeks)
    # months
    months = days / 365 * 12
    if months <= 3:
        return '%0.1f months' % months
    if months <= 18:
        return '%d months' % round(months)
    # years
    years = days / 365
    if years <= 3:
        return '%0.1f years' % years
    return '%d years'


# *******************************************************************************
# Helper classes
# *******************************************************************************


class CustomRendererForDetails(SaferHtmlRenderer):
    """A custom markdown renderer.

    Inherits from SaferHtmlRenderer, which adds protection for cross-site scripting
    and filters out html code.

    Attributes:
        bib_labels(dict): A mapping for bib labels to bib numbers.
    """

    bib_labels = {}

    @classmethod
    def header(cls, content, level):
        """[summary]

        Args:
            content ([type]): [description]
            level ([type]): [description]

        Returns:
            [type]: [description]
        """
        level += 4
        return '<h%d>%s</h%d>' % (level, content, level)

    def link(self, content, link, title=''):
        """[summary]

        Args:
            content ([type]): [description]
            link ([type]): [description]
            title (str, optional): [description]. Defaults to ''.

        Returns:
            [type]: [description]
        """
        # Regular links.
        if self.check_url(link):
            link = self.rewrite_url(link)
            if len(title) > 0:
                return '<a href="%s" title="%s">%s</a>' % (link, content, title)
            return '<a href="%s">%s</a>' % (link, content)
        # Bib 'links'.
        if content == '#':
            bib_numbers = ''
            for label in re.findall(r'\w+', link):
                if label not in self.bib_labels:
                    self.bib_labels[label] = len(self.bib_labels) + 1
                bib_numbers += '%d,' % self.bib_labels[label]
            return '[%s]' % bib_numbers.strip(',')
        # Broken links.
        return '[%s](---broken link---)' % content

    def image(self, link, title='', alt=''):
        """Convert image links to regular links.

        Currently, Wiki-O does not allow images to be displayed.

        Args:
            link (str): The image link.
            title (str, optional): The image title. Defaults to ''.
            alt (str, optional): The alternative text. Defaults to ''.

        Returns:
            str: A html redered link to the image (if it is safe).
        """
        if self.check_url(link):
            link = self.rewrite_url(link)
            if len(title) > 0 and len(alt) > 0:
                return '<a href="%s" title="%s" alt="%s">image(%s)</a>' % (link, title, alt, title)
            if len(title) > 0:
                return '<a href="%s">image(%s)</a>' % (link, title)
            return '<a href="%s">image</a>' % link
        return '[%s](---broken image---)' % (title)

    @classmethod
    def table(cls, content):
        """[summary]

        Args:
            content ([type]): [description]

        Returns:
            [type]: [description]
        """
        table_open = '<table class="table table-sm" style="width:90%;" align="center">\n'
        table_close = '\n</table>'
        return table_open + content + table_close


def render_details(raw_content):
    """[summary]

    Args:
        raw_content ([type]): [description]

    Returns:
        [type]: [description]
    """
    bib_content = ''
    if re.search(r'</bib>[\n\s]*$', raw_content):
        i = raw_content.rfind('<bib>')
        if i >= 0:
            bib_content = raw_content[i:]
            raw_content = raw_content[:i]

    md = Markdown(
        CustomRendererForDetails(),
        extensions=(
            'strikethrough',
            'underline',
            'quote',
            'superscript',
            'math',
            'math-explicit',
            'fenced-code',
            'tables',
        ),
    )
    md.renderer.bib_labels = {}
    rendered_content = md(raw_content)
    bib_labels = md.renderer.bib_labels

    if len(bib_content) > 0:
        bib_entries = {}
        for entry in re.findall(r'\[\w*\]:.+', bib_content):
            i = entry.find(':')
            label = entry[1:i - 1]
            content = entry[i + 1:].strip()
            bib_entries[label] = md(content).strip()
        rendered_content += '\n<ol class="bib">\n'
        for label in bib_labels:
            if label in bib_entries:
                rendered_content += '  <li>%s</li>\n' % bib_entries[label]
                del bib_entries[label]
            else:
                rendered_content += ('  <li><p>Missing entry.</p></li>\n')
        for label in bib_entries:
            rendered_content += '  <li>%s</li>\n' % bib_entries[label]
        rendered_content += '</ol>'
    return rendered_content


# *******************************************************************************
# main
#
#
#
#
#
# *******************************************************************************
if __name__ == '__main__':
    pass
