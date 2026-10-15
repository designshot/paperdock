"""Local document names with a deliberately small, safe template vocabulary."""
from datetime import datetime
import re
import unicodedata
from urllib.parse import quote

DEFAULT_TEMPLATE = 'Scan_{date}_{time}'
PLACEHOLDERS = {'date', 'time', 'counter'}


def validate_title(value):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 200:
        raise ValueError('Bitte einen Dokumentnamen mit 1 bis 200 Zeichen angeben.')
    if any(unicodedata.category(char).startswith('C') for char in value):
        raise ValueError('Der Dokumentname darf keine Steuerzeichen enthalten.')
    return value.strip()


def validate_template(value):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 120:
        raise ValueError('Die Namensvorlage muss 1 bis 120 Zeichen enthalten.')
    value = value.strip()
    remainder = re.sub(r'\{(?:date|time|counter)\}', '', value)
    if any(char in remainder for char in '{}<>:"/\\|?*') or any(unicodedata.category(char).startswith('C') for char in value):
        raise ValueError('Erlaubte Platzhalter sind {date}, {time} und {counter}; Pfade und Steuerzeichen sind nicht erlaubt.')
    if not value.strip(' ._-'):
        raise ValueError('Die Namensvorlage muss einen lesbaren Namen ergeben.')
    return value


def render_template(template, counter, now=None):
    now = now or datetime.now().astimezone()
    values = {'date': now.strftime('%Y-%m-%d'), 'time': now.strftime('%H-%M-%S'), 'counter': f'{counter:03d}'}
    return re.sub(r'\{(date|time|counter)\}', lambda match: values[match.group(1)], template)


def unique_name(title, existing):
    occupied = {value.casefold() for value in existing}
    candidate, suffix = title, 2
    while candidate.casefold() in occupied:
        ending = f'_{suffix}'
        candidate = title[:200 - len(ending)] + ending
        suffix += 1
    return candidate


def pdf_filename(title):
    value = ''.join('_' if char in '<>:"/\\|?*' or unicodedata.category(char).startswith('C') else char for char in title)
    value = re.sub(r'\s+', ' ', value).strip(' .')
    if value.lower().endswith('.pdf'):
        value = value[:-4].rstrip(' .')
    # Bound UTF-8 bytes as well as characters for normal filesystem filename limits.
    value = value.encode('utf-8')[:180].decode('utf-8', 'ignore').rstrip(' .') or 'Scan'
    if re.fullmatch(r'(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', value, re.I):
        value = 'Scan_' + value
    return value + '.pdf'


def pdf_disposition(title):
    filename = pdf_filename(title)
    fallback = unicodedata.normalize('NFKD', filename).encode('ascii', 'ignore').decode()
    fallback = re.sub(r'[^A-Za-z0-9 ._-]', '_', fallback).strip(' .')
    if not fallback or fallback == 'pdf':
        fallback = 'Scan.pdf'
    return f'attachment; filename="{fallback}"; filename*=UTF-8\'\'{quote(filename, safe="")}'
