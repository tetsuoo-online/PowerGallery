"""
Settings module — dynamic language discovery.
Languages are auto-detected from config/lang/*.py files that expose:
  - lang_name  (str)  : display name, e.g. "Français"
  - lang_icon  (str, optional) : relative path to flag gif, e.g. "flags/fr.gif"
  - LANG       (dict) : translation strings
"""

import json
import importlib
import importlib.util
from pathlib import Path

_SETTINGS_FILE = Path(__file__).parent / 'settings.json'
_LANG_DIR = Path(__file__).parent / 'lang'

_DEFAULTS = {
    'language': 'en',
    'import_mode': 'replace',
    'import_in_tabs': False,
    'auto_load_last': True,
    'auto_save_session': True,
    'selected_module': None,
    'current_style': 'dark',
    'dataset_clear_if_empty': False,
    'show_title': False,
    'show_description': False,
    'fullscreen_opacity': 100,
}


# ── Language registry ─────────────────────────────────────────────────────────

def _discover_languages():
    langs = {}
    if not _LANG_DIR.exists():
        return langs
    for path in sorted(_LANG_DIR.glob('*.py')):
        if path.stem == '__init__':
            continue
        key = path.stem
        spec = importlib.util.spec_from_file_location(f'config.lang.{key}', path)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception as e:
            print(f"[settings] Failed to load lang '{key}': {e}")
            continue
        if not hasattr(mod, 'LANG'):
            continue
        langs[key] = {
            'name': getattr(mod, 'lang_name', key),
            'icon': getattr(mod, 'lang_icon', None),
            'module': mod,
        }
    return langs


# ── Config class ──────────────────────────────────────────────────────────────

class Config:
    def __init__(self):
        self._data = dict(_DEFAULTS)
        self._load()
        self._languages = _discover_languages()
        lang_key = self._data.get('language', 'en')
        if lang_key not in self._languages and self._languages:
            lang_key = next(iter(self._languages))
            self._data['language'] = lang_key
        self._current_lang = self._languages.get(lang_key, {}).get('module', None)
        self._styles = None

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self):
        try:
            if _SETTINGS_FILE.exists():
                data = json.loads(_SETTINGS_FILE.read_text(encoding='utf-8'))
                self._data.update(data)
        except Exception as e:
            print(f"[settings] Load error: {e}")

    def _save(self):
        try:
            _SETTINGS_FILE.write_text(
                json.dumps(self._data, indent=2, ensure_ascii=False), encoding='utf-8')
        except Exception as e:
            print(f"[settings] Save error: {e}")

    # ── Generic get/set ───────────────────────────────────────────────────────

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value
        self._save()

    # ── Language ──────────────────────────────────────────────────────────────

    def get_languages(self):
        return self._languages

    def set_language(self, lang_key):
        if lang_key in self._languages:
            self._data['language'] = lang_key
            self._current_lang = self._languages[lang_key]['module']
            self._save()

    def get_text(self, key):
        if self._current_lang and hasattr(self._current_lang, 'LANG'):
            return self._current_lang.LANG.get(key, key)
        return key

    # ── Style ─────────────────────────────────────────────────────────────────

    def get_styles(self):
        if self._styles is None:
            self._reload_styles()
        return self._styles

    def _reload_styles(self):
        style_name = self._data.get('current_style', 'dark')
        try:
            if style_name == 'dark':
                import config.styles_dark as mod
            elif style_name == 'light':
                import config.styles_light as mod
            else:
                mod = importlib.import_module(f'config.custom_styles.{style_name}')
            self._styles = mod
        except Exception as e:
            print(f"[settings] Style load error '{style_name}': {e}")
            import config.styles_dark as mod
            self._styles = mod

    def set_current_style(self, style_name):
        self._data['current_style'] = style_name
        self._styles = None
        self._save()

    # ── Convenience setters ───────────────────────────────────────────────────

    def set_import_mode(self, mode):
        self.set('import_mode', mode)

    def set_import_in_tabs(self, value):
        self.set('import_in_tabs', value)

    def set_auto_load_last(self, value):
        self.set('auto_load_last', value)

    def set_auto_save_session(self, value):
        self.set('auto_save_session', value)

    def set_selected_module(self, module_key):
        self.set('selected_module', module_key)

    # ── Last session ──────────────────────────────────────────────────────────

    def save_last_session(self, paths):
        self.set('last_session', paths)

    def get_last_session(self):
        return self._data.get('last_session', [])


config = Config()
