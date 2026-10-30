"""Validated local visual settings used by both the controls and live source."""
import math
import re

EFFECTS = {'spectrum', 'rings', 'waveform', 'tunnel', 'impacts', 'waterfall'}
PARTICLES = {'stars', 'sparks', 'embers', 'snow', 'bubbles', 'orbs', 'confetti', 'streaks'}


def validated(value):
    if not isinstance(value, dict):
        return {}
    result = {}
    for key, low, high in (('sensitivity', .4, 2), ('motion', .3, 2), ('density', 0, 600), ('dim', 0, .95)):
        number = value.get(key)
        if isinstance(number, (float, int)) and math.isfinite(number):
            result[key] = min(high, max(low, number))
    result['fps'] = 30 if value.get('fps') == 30 else 60
    for key, options in (('effects', EFFECTS), ('particles', PARTICLES)):
        if isinstance(value.get(key), list):
            result[key] = list(dict.fromkeys(item for item in value[key] if isinstance(item, str) and item in options))
    for key in ('colorA', 'colorB'):
        if isinstance(value.get(key), str) and re.fullmatch(r'#[0-9a-fA-F]{6}', value[key]):
            result[key] = value[key]
    for key, maximum in (('theme', 80), ('name', 30)):
        if isinstance(value.get(key), str):
            result[key] = value[key][:maximum]
    result['showName'] = value.get('showName') is True
    result['overlays'] = {}
    if isinstance(value.get('overlays'), dict):
        for kind in ('name', 'track', 'logo'):
            raw = value['overlays'].get(kind)
            if not isinstance(raw, dict):
                continue
            item = {}
            for key, low, high in (('x', 0, .98), ('y', 0, .98), ('w', .03, 1), ('h', .02, 1), ('size', 8, 260)):
                number = raw.get(key)
                if isinstance(number, (int, float)) and math.isfinite(number):
                    item[key] = min(high, max(low, number))
            for key in ('locked', 'visible', 'italic'):
                item[key] = raw.get(key) is True
            for key in ('text', 'manualArtist', 'manualTitle'):
                if isinstance(raw.get(key), str):
                    item[key] = raw[key][:500]
            if raw.get('font') in ('Segoe UI', 'Arial', 'Verdana', 'Georgia', 'Impact', 'Courier New'):
                item['font'] = raw['font']
            if isinstance(raw.get('color'), str) and re.fullmatch(r'#[0-9a-fA-F]{6}', raw['color']):
                item['color'] = raw['color']
            item['weight'] = 700 if kind == 'track' or raw.get('weight') == 700 else 400
            item['mode'] = 'manual' if raw.get('mode') == 'manual' else 'auto'
            result['overlays'][kind] = item
    result['customThemes'] = []
    if isinstance(value.get('customThemes'), list):
        for item in value['customThemes'][-64:]:
            if not isinstance(item, dict) or not isinstance(item.get('id'), str):
                continue
            theme = validated({key: item[key] for key in ('effects', 'particles', 'colorA', 'colorB', 'name') if key in item})
            theme = {key: theme[key] for key in ('effects', 'particles', 'colorA', 'colorB', 'name') if key in theme}
            theme['id'] = item['id'][:80]
            if 'name' in theme and 'effects' in theme and 'particles' in theme:
                result['customThemes'].append(theme)
    return result
