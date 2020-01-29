# *******************************************************************************
# Wiki-O: A web service for sharing opinions and avoiding arguments.
# Copyright (C) 2018 Frank Imeson
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# *******************************************************************************


# *******************************************************************************
# imports
# *******************************************************************************
import re
import math
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
RE_HASHTAG = r'#\w+'
RE_STATS = r'(opinion_all|opinion_supporters|opinion_moderates|opinion_opposers)'
RE_WIKI_O_URL = r'(https?://)?(www\.)?(m\.)?wiki-o\.com/(theory/\d+|evidence/\d+|opinion/\d+|opinion/\d+/vs/\d+|opinion/\d+/vs/%s|theory/\d+/%s|theory/%s/vs/\d+|theory/\d+/%s/vs/%s)/' % (
    RE_STATS, RE_STATS, RE_STATS, RE_STATS, RE_STATS)
re_wiki_o = re.compile(RE_WIKI_O_URL)


# *******************************************************************************
# methods
#
#
#
#
#
# *******************************************************************************


# ************************************************************
#
# ************************************************************
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


# ************************************************************
#
# ************************************************************
def parse_log(log, value, extra):

    # setup
    value = value.replace('{{', '{').replace('}}', '}')
    value = value.replace('<#', '«').replace('#>', '»')

    # variables
    s = ''
    h = 0
    for i, j, d in get_brace_indices(value):
        if value[i] == '{' and value[j] == '}':
            s += value[h:i]
            name = value[i+1:j].strip()
            if name == 'object' and log.action_object is not None:
                name = log.action_object.__str__()
            elif name == 'target' and log.target is not None:
                name = log.target.__str__()
            elif name == 'target.get_owner' and log.target is not None:
                name = log.target.get_owner()
            s += name
            h = j+1
    s += value[h:]

    # links
    value = s
    s = ''
    h = 0
    for i, j, d in get_brace_indices(value):
        if value[i] == '«' and value[j] == '»':
            s += value[h:i]
            x = value[i+1:j].strip()
            k = x.find(' ')
            url = x[:k].strip()
            name = x[k+1:].strip()

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
            s += '<a class="plain" href="%s">%s</a>' % (url, name)
            h = j+1
    s += value[h:]
    return s


# ************************************************************
#
# ************************************************************
def make_safe(string):
    s = string.replace('{', '[[').replace('}', ']]')
    s = s.replace('<', '&lt;').replace('>', '&gt;')
    return s


# *******************************************************************************
# filters
#
#
#
#
#
# *******************************************************************************


# ************************************************************
#
# ************************************************************
@register.filter
def possessive(value):
    if value[-1] == 's':
        return value + "'"
    else:
        return value + "'s"


# ************************************************************
#
# ************************************************************
@register.filter
def get_class(value):
    return value.__class__.__name__


# ************************************************************
#
# ************************************************************
@register.filter
def follow_url(obj):
    content_type = ContentType.objects.get_for_model(obj)
    return reverse('activity:follow', kwargs={'content_type_id': content_type.pk, 'object_id': obj.pk})


# ************************************************************
#
# ************************************************************
@register.filter
def unfollow_url(obj):
    content_type = ContentType.objects.get_for_model(obj)
    return reverse('activity:unfollow', kwargs={'content_type_id': content_type.pk, 'object_id': obj.pk})


# ************************************************************
#
# ************************************************************
@register.filter
def bibliography(value, inc_links=True, autoescape=True):
    """Formats the detail text to include a linked bibliograpy."""
    autoescape = autoescape and not isinstance(value, SafeData)
    value = normalize_newlines(value)
    if autoescape:
        value = escape(value)

    # create bib and external links
    h = 0
    s = ''
    bib = []
    # make unsafe by replacing brackets
    value = re.sub(r'&lt;!--', '«', value)
    value = re.sub(r'--&gt;\s*', '»', value)
    value = value.replace('[[', '{').replace(']]', '}')
    value = value.replace('&lt;', '<').replace('&gt;', '>')
    for i, j, d in get_brace_indices(value):
        s += make_safe(value[h:i])
        h = j+1
        INLINE = value[i] == '<' and value[j] == '>'
        BIB00 = value[i] == '[' and value[j] == ']'
        BIB01 = value[i] == '{' and value[j] == '}'
        COMMENT = value[i] == '«' and value[j] == '»'
        if COMMENT:
            continue
        url = make_safe(value[i+1:j].strip())
        name = url
        k = url.find(' ')
        if k > 0:
            name = url[k:].strip()
            url = url[:k].strip()
        if URLValidator.regex.search(url):
            # scrub wiki-o links
            if re.search('wiki-o', url):
                x = re_wiki_o.match(url)
                if x:
                    url = x.group()
                else:
                    url = ''
            # regular citation
            if BIB00:
                # don't add duplicates to bib
                if (url, name) not in bib:
                    bib.append((url, name))
                    n = len(bib)
                else:
                    for n, x in enumerate(bib):
                        if x == (url, name):
                            break
                    n += 1
                if s[-1] == ' ':
                    s = s.strip()
                    s += '&nbsp;'
                s += '[%d]' % n
            # add to bib but not inline
            elif BIB01:
                if (url, name) not in bib:
                    bib.append((url, name))
            # inline url, done with () brackets
            elif INLINE:
                if inc_links:
                    s += '<a href="%s" target="_blank">%s</a>' % (url, name)
                else:
                    s += '%s' % (name)
            else:
                assert False
        else:
            s0 = make_safe(value[i+1:j])
            if INLINE:
                s += '&lt;%s&gt;' % s0
            elif BIB00:
                s += '[%s]' % s0
            elif BIB01:
                s += '[[%s]]' % s0
    s += make_safe(value[h:])
    value = s

    # create lists
    s = ''
    UL = 0
    OL = 0
    for line in value.split('\n'):
        if re.match(r'\s*\*+\s+.+$', line):
            bullets = re.findall(r'\*+', line)[0]
            while len(bullets) > UL:
                if UL == 0 and OL == 0:
                    s += '<ul style="width:95%">'
                else:
                    s += '<ul>'
                UL += 1
            while len(bullets) < UL:
                s += '</ul>'
                UL -= 1
            s += '<li> %s </li>' % line.strip().strip('*').strip()
        elif re.match(r'\s*#+\s+.+$', line):
            bullets = re.findall(r'#+', line)[0]
            while len(bullets) > OL:
                if UL == 0 and OL == 0:
                    s += '<ol style="width:95%">'
                else:
                    s += '<ol>'
                OL += 1
            while len(bullets) < OL:
                s += '</ol>'
                OL -= 1
            s += '<li> %s </li>' % line.strip().strip('#').strip()
        else:
            while UL > 0:
                s += '</ul>'
                UL -= 1
            while OL > 0:
                s += '</ol>'
                OL -= 1
            s += line + '\n'
    while UL > 0:
        s += '</ul>'
        UL -= 1
    while OL > 0:
        s += '</ol>'
        OL -= 1
    value = s

    # bib
    if len(bib) > 0:
        s = s.strip()
        s += '<ol class="bib">'
        for i, (url, name) in enumerate(bib):
            if inc_links:
                s += '<li> <a href="%s" target="_blank">%s</a> </li>\n' % (
                    url, name)
            else:
                s += '<li> %s </li>\n' % (name)
        s += '</ol>'
    s = s.replace('][', ',')
    s = s.replace(']&nbsp;[', ',')
    value = s.strip()

    # ship it
    value = value.replace('\n', '<br/>')
    value = value.replace('  ', '&nbsp&nbsp')
    return mark_safe(value)


# ************************************************************
#
# ************************************************************
@register.filter
def short_bib(value, length=500, autoescape=True):
    """Formats the detail text to include a non-linked bibliograpy."""
    value = bibliography(value, inc_links=False, autoescape=autoescape)
    if len(value) > length:
        value = value[:length]
        i = value.rfind(' ')
        value = value[:i] + '...'
    return mark_safe(value)


# ************************************************************
#
# ************************************************************
@register.filter
def get_verb(log, extra='', autoescape=True):
    extra = str(extra)
    verb = parse_log(log, log.verb, extra)
    if isinstance(log, Notification):
        if log.unread:
            verb = '<strong>' + verb + '</strong>'
        if log.level == 'warning':
            verb = '<font color="red">' + verb + '</font>'
    return mark_safe(verb)


# ************************************************************
#
# ************************************************************
@register.filter
def get_description(log, extra='', autoescape=True):
    extra = str(extra)
    description = parse_log(log, log.description, extra)
    return mark_safe(description)


# ************************************************************
#
# ************************************************************
@register.simple_tag
def url_action(action, *args, extra='', **kwargs):
    resolved_url = action.action_object.activity_url()
    parms = {'date': action.timestamp - datetime.timedelta(seconds=1)}
    extra = str(extra)
    if len(extra) > 0:
        extra += '&' + urlencode(parms)
    else:
        extra += '?%s' % urlencode(parms)
    return resolved_url + extra

    h = 0
    s = ''
    verb = log.verb
    for i, j, d in get_brace_indices(verb):
        s += verb[h:i]
        h = j+1
        url = verb[i+1:j].strip()
        name = url
        k = url.find(' ')
        if k > 0:
            name = url[k:].strip()
            url = url[:k].strip()
        if URLValidator.regex.search(url):
            # regular citation
            if BIB00:
                # don't add duplicates to bib
                if (url, name) not in bib:
                    bib.append((url, name))
                    n = len(bib)
                else:
                    for n, x in enumerate(bib):
                        if x == (url, name):
                            break
                    n += 1
                if s[-1] == ' ':
                    s = s.strip()
                    s += '&nbsp;'
                s += '[%d]' % n
            # add to bib but not inline
            elif BIB01:
                if (url, name) not in bib:
                    bib.append((url, name))
            # inline url, done with () brackets
            elif INLINE:
                if inc_links:
                    s += '<a href="%s" target="_blank">%s</a>' % (url, name)
                else:
                    s += '%s' % (name)
            else:
                assert False
        else:
            s0 = make_safe(value[i+1:j])
            if INLINE:
                s += '&lt;%s&gt;' % s0
            elif BIB00:
                s += '[%s]' % s0
            elif BIB01:
                s += '[[%s]]' % s0
    s += make_safe(value[h:])
    # bib
    if len(bib) > 0:
        s = s.strip()
        s += '<ol class="bib">'
        for i, (url, name) in enumerate(bib):
            if inc_links:
                s += '<li> <a href="%s" target="_blank">%s</a> </li>\n' % (
                    url, name)
            else:
                s += '<li> %s </li>\n' % (name)
        s += '</ol>'
    s = s.replace('][', ',')
    s = s.replace(']&nbsp;[', ',')
    value = s.strip()

    value = value.replace('\n', '<br/>')
    value = value.replace('  ', '&nbsp&nbsp')
    return mark_safe(value)


# ************************************************************
#
# ************************************************************
@register.filter
def get_desc(log, autoescape=True):
    pass


# ************************************************************
#
# ************************************************************
@register.simple_tag
def url_extra(url, *args, extra='', **kwargs):
    resolved_url = reverse(url, None, args, kwargs)
    return resolved_url + extra


# ************************************************************
#
# ************************************************************
@register.simple_tag
def url_action(action, *args, extra='', **kwargs):
    resolved_url = action.action_object.activity_url()
    parms = {'date': action.timestamp - datetime.timedelta(seconds=1)}
    extra = str(extra)
    if len(extra) > 0:
        extra += '&' + urlencode(parms)
    else:
        extra += '?%s' % urlencode(parms)
    return resolved_url + extra


# ************************************************************
#
# ************************************************************
@register.filter
def timepassed(value, autoescape=True):
    delta = timezone.now() - value
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
    s = 'Yo, [(https://en.wikipedia.org/wiki/Steven_Avery Wikipedia what)] is [up[?]'
    print(s)
    print(bibliography(s))
