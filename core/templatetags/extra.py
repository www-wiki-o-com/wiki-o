"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

A web service for sharing opinions and avoiding arguments

@file       core/templatetags/extra.py
@brief      A collection of template tags
@copyright  GNU Public License, 2018
@authors    Frank Imeson
"""


# *******************************************************************************
# imports
# *******************************************************************************
import re
import datetime

from django import template
from django.utils.html import escape
from django.utils.text import normalize_newlines
from django.core.validators import URLValidator
from django.utils.safestring import mark_safe, SafeData
from django.utils.http import urlencode
from django.utils import timezone
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType
from notifications.models import Notification


# *******************************************************************************
# defs
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

RE_HASHTAG = r'#\w+'


# *******************************************************************************
# methods
#
#
#
#
#
# *******************************************************************************


def get_brace_indices(string):
    """Parenthesized contents in string as pairs (level, contents)."""
    stack = []
    result = []
    for i, c in enumerate(string):
        if c == '[' or c == '<' or c == '{' or c == '«':
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


def interpret_log_text(log, log_text, extra):
    """Interpret the variables and links encoded in the log text."""

    # Interpret brackets
    log_text = log_text.replace('{{', '{').replace('}}', '}')
    log_text = log_text.replace('<#', '«').replace('#>', '»')

    # Interpret variables
    result = ''
    prev_index = 0
    for start_index, end_index, nested_depth in get_brace_indices(log_text):
        if log_text[start_index] == '{' and log_text[end_index] == '}':
            result += log_text[prev_index:start_index]
            name = log_text[start_index+1:end_index].strip()
            if name == 'object' and log.action_object is not None:
                name = log.action_object.__str__()
            elif name == 'target' and log.target is not None:
                name = log.target.__str__()
            elif name == 'target.get_owner' and log.target is not None:
                name = log.target.get_owner()
            result += name
            prev_index = end_index+1
    result += log_text[prev_index:]

    # Interpret links
    log_text = result
    result = ''
    prev_index = 0
    for start_index, end_index, nested_depth in get_brace_indices(log_text):
        if log_text[start_index] == '«' and log_text[end_index] == '»':
            result += log_text[prev_index:start_index]
            url, name = log_text[start_index+1:end_index].strip().split(' ', 1)
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
                date = date.strftime("%Y-%m-%d %X")
                if extra == '':
                    extra += '?' + urlencode({'date': date})
                else:
                    extra += '&' + urlencode({'date': date})
            # add extra
            if len(extra) > 0:
                url += extra
            # redirect to mark notification as read
            if isinstance(log, Notification):
                mark_as_read_url = reverse(
                    'notifications:mark_as_read', kwargs={'slug': log.slug})
                url = mark_as_read_url + '?next=' + url

            # link
            result += '<a class="plain" href="%s">%s</a>' % (url, name)
            prev_index = end_index + 1
    result += log_text[prev_index:]
    return result


def make_safe(text):
    """Remove all unsafe http characters from the text."""
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
def possessive(text):
    """Add the possesive 's or ' to the end of the text."""
    if text[-1] == 's':
        return text + "'"
    else:
        return text + "'s"


@register.filter
def get_class(obj):
    """Return the object's name."""
    return obj.__class__.__name__


@register.filter
def follow_url(obj):
    """Retrive the url for subcribing to the object."""
    content_type = ContentType.objects.get_for_model(obj)
    return reverse('activity:follow',
                   kwargs={'content_type_id': content_type.pk, 'object_id': obj.pk})


@register.filter
def unfollow_url(obj):
    """Retrive the url for unsubcribing from the object."""
    content_type = ContentType.objects.get_for_model(obj)
    return reverse('activity:unfollow',
                   kwargs={'content_type_id': content_type.pk, 'object_id': obj.pk})


@register.filter
def bibliography(detail_text, inc_links=True, autoescape=True):
    """Formats the detail text to include a linked bibliograpy."""
    autoescape = autoescape and not isinstance(detail_text, SafeData)
    detail_text = normalize_newlines(detail_text)
    if autoescape:
        detail_text = escape(detail_text)

    # create bib and external links
    prev_index = 0
    bib = []
    result = ''
    # make unsafe by replacing brackets
    detail_text = re.sub(r'&lt;!--', '«', detail_text)
    detail_text = re.sub(r'--&gt;\s*', '»', detail_text)
    detail_text = detail_text.replace('[[', '{').replace(']]', '}')
    detail_text = detail_text.replace('&lt;', '<').replace('&gt;', '>')
    for start_index, end_index, nested_depth in get_brace_indices(detail_text):
        result += make_safe(detail_text[prev_index:start_index])
        prev_index = end_index + 1
        inline = detail_text[start_index] == '<' and detail_text[end_index] == '>'
        bib00 = detail_text[start_index] == '[' and detail_text[end_index] == ']'
        bib01 = detail_text[start_index] == '{' and detail_text[end_index] == '}'
        comment = detail_text[start_index] == '«' and detail_text[end_index] == '»'
        if comment:
            continue
        url = make_safe(detail_text[start_index+1:end_index].strip())
        name = url
        k = url.find(' ')
        if k > 0:
            name = url[k:].strip()
            url = url[:k].strip()
        if URLValidator.regex.search(url):
            # scrub wiki-o links
            if re.search('wiki-o', url):
                x = RE_WIKI_O.match(url)
                if x:
                    url = x.group()
                else:
                    url = ''
            # regular citation
            if bib00:
                # don't add duplicates to bib
                if (url, name) in bib:
                    for bib_index, x in enumerate(bib):
                        if x == (url, name):
                            break
                else:
                    bib.append((url, name))
                    bib_index = len(bib) - 1
                if result[-1] == ' ':
                    result = result.strip()
                    result += '&nbsp;'
                result += '[%d]' % bib_index + 1
            # add to bib but not inline
            elif bib01:
                if (url, name) not in bib:
                    bib.append((url, name))
            # inline url, done with () brackets
            elif inline:
                if inc_links:
                    result += '<a href="%s" target="_blank">%s</a>' % (url, name)
                else:
                    result += '%s' % (name)
            else:
                assert False
        else:
            s = make_safe(detail_text[start_index+1:end_index])
            if inline:
                result += '&lt;%s&gt;' % s
            elif bib00:
                result += '[%s]' % s
            elif bib01:
                result += '[[%s]]' % s
    result += make_safe(detail_text[prev_index:])
    detail_text = result

    # create lists
    result = ''
    ul_depth = 0
    ol_depth = 0
    for line in detail_text.split('\n'):
        if re.match(r'\s*\*+\s+.+$', line):
            bullets = re.findall(r'\*+', line)[0]
            while len(bullets) > ul_depth:
                if ul_depth == 0 and ol_depth == 0:
                    result += '<ul style="width:95%">'
                else:
                    result += '<ul>'
                ul_depth += 1
            while len(bullets) < ul_depth:
                result += '</ul>'
                ul_depth -= 1
            result += '<li> %s </li>' % line.strip().strip('*').strip()
        elif re.match(r'\s*#+\s+.+$', line):
            bullets = re.findall(r'#+', line)[0]
            while len(bullets) > ol_depth:
                if ul_depth == 0 and ol_depth == 0:
                    result += '<ol style="width:95%">'
                else:
                    result += '<ol>'
                ol_depth += 1
            while len(bullets) < ol_depth:
                result += '</ol>'
                ol_depth -= 1
            result += '<li> %s </li>' % line.strip().strip('#').strip()
        else:
            while ul_depth > 0:
                result += '</ul>'
                ul_depth -= 1
            while ol_depth > 0:
                result += '</ol>'
                ol_depth -= 1
            result += line + '\n'
    while ul_depth > 0:
        result += '</ul>'
        ul_depth -= 1
    while ol_depth > 0:
        result += '</ol>'
        ol_depth -= 1
    detail_text = s

    # bib
    if len(bib) > 0:
        result = result.strip()
        result += '<ol class="bib">'
        for i, (url, name) in enumerate(bib):
            if inc_links:
                result += '<li> <a href="%s" target="_blank">%s</a> </li>\n' % (
                    url, name)
            else:
                result += '<li> %s </li>\n' % (name)
        result += '</ol>'
    result = result.replace('][', ',')
    result = result.replace(']&nbsp;[', ',')
    detail_text = result.strip()

    # ship it
    detail_text = detail_text.replace('\n', '<br/>')
    detail_text = detail_text.replace('  ', '&nbsp&nbsp')
    return mark_safe(detail_text)


@register.filter
def short_bib(detail_text, length=500, autoescape=True):
    """Formats the detail text to include a non-linked bibliograpy."""
    detail_text = bibliography(detail_text, inc_links=False, autoescape=autoescape)
    if len(detail_text) > length:
        detail_text = detail_text[:length]
        i = detail_text.rfind(' ')
        detail_text = detail_text[:i] + '...'
    return mark_safe(detail_text)


@register.filter
def get_verb(log, extra=''):
    """"Retrieves and formats the log's verb text."""
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
    """Retrieves and formats the log's description text."""
    extra = str(extra)
    description = interpret_log_text(log, log.description, extra)
    return mark_safe(description)


@register.simple_tag
def url_extra(url, *args, extra='', **kwargs):
    """Add extra parameters to the url."""
    resolved_url = reverse(url, None, args, kwargs)
    return resolved_url + extra


@register.simple_tag
def url_action(action, extra=''):
    """Retrive the url for the action object's stream."""
    resolved_url = action.action_object.activity_url()
    parms = {'date': action.timestamp - datetime.timedelta(seconds=1)}
    extra = str(extra)
    if len(extra) > 0:
        extra += '&' + urlencode(parms)
    else:
        extra += '?%s' % urlencode(parms)
    return resolved_url + extra


@register.filter
def timepassed(time_then):
    """Construct a human readable string for the """
    delta = timezone.now() - time_then
    # seconds
    seconds = delta.total_seconds()
    if seconds <= 90:
        return '%d secs' % seconds
    # minutes
    minutes = 1.0 * seconds / 60
    if minutes <= 3:
        return '%0.1f mins' % minutes
    elif minutes <= 90:
        return '%d mins' % round(minutes)
    # hours
    hours = minutes / 60
    if hours <= 3:
        return '%0.1f hours' % hours
    elif hours <= 36:
        return '%d hours' % round(hours)
    # days
    days = hours / 24
    if days < 3:
        return '%0.1f days' % days
    elif days <= 10:
        return '%d days' % round(days)
    # weeks
    weeks = days / 7
    if weeks <= 3:
        return '%0.1f weeks' % weeks
    elif weeks <= 6:
        return '%d weeks' % round(weeks)
    # months
    months = days / 365 * 12
    if months <= 3:
        return '%0.1f months' % months
    elif months <= 18:
        return '%d months' % round(months)
    # years
    years = days / 365
    if years <= 3:
        return '%0.1f years' % years
    else:
        return '%d years'


# *******************************************************************************
# main
#
#
#
#
#
# *******************************************************************************
if __name__ == "__main__":
    test = 'Yo, [(https://en.wikipedia.org/wiki/Steven_Avery Wikipedia what)] is [up[?]'
    print(bibliography(test))
