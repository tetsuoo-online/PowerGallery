# ============================================================================
# CONFIGURATION MANAGER
# ============================================================================

import json
import os
from pathlib import Path

# Default settings
DEFAULT_SETTINGS = {
    'language': 'fr',  # 'fr' or 'en'
    'current_style': 'dark',  # Current style: 'dark', 'light', or 'custom_stylename'
    'import_mode': 'replace',  # 'add' or 'replace'
    'selected_module': None,  # None or module name (e.g., 'checkpoint_manager')
    'import_in_tabs': False,  # Import images/grids in new tabs
    'auto_load_last': False,  # Auto-load last session on startup
    'last_session': [],  # List of JSON file paths from last session
}

# Path to settings file
SETTINGS_PATH = Path(__file__).parent / 'settings.json'


class Config:
    def __init__(self):
        self.settings = DEFAULT_SETTINGS.copy()
        self.lang = None
        self.load_settings()
        self.load_language()
    
    def load_settings(self):
        """Load settings from JSON file or create with defaults"""
        if SETTINGS_PATH.exists():
            try:
                with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    self.settings.update(loaded)
            except Exception as e:
                print(f"Error loading settings: {e}")
                print("Using default settings")
        else:
            self.save_settings()
    
    def save_settings(self):
        """Save current settings to JSON file"""
        try:
            with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def load_language(self):
        """Load language strings based on current language setting"""
        lang_code = self.settings.get('language', 'fr')
        try:
            if lang_code == 'en':
                from config.lang import en
                self.lang = en.LANG
            else:
                from config.lang import fr
                self.lang = fr.LANG
        except Exception as e:
            print(f"Error loading language {lang_code}: {e}")
            # Fallback to French
            from config.lang import fr
            self.lang = fr.LANG
    
    def set_language(self, lang_code):
        """Change language and reload strings"""
        self.settings['language'] = lang_code
        self.save_settings()
        self.load_language()
    
    def set_theme(self, theme):
        """Set theme (dark/light)"""
        self.settings['theme'] = theme
        self.save_settings()
    
    def set_import_mode(self, mode):
        """Set import mode (add/replace)"""
        self.settings['import_mode'] = mode
        self.save_settings()
    
    def set_selected_module(self, module_name):
        """Set selected module (None or module name)"""
        self.settings['selected_module'] = module_name
        self.save_settings()
    
    def set_import_in_tabs(self, enabled):
        """Set import in tabs mode"""
        self.settings['import_in_tabs'] = enabled
        self.save_settings()
    
    def set_auto_load_last(self, enabled):
        """Set auto-load last session mode"""
        self.settings['auto_load_last'] = enabled
        self.save_settings()
    
    def save_last_session(self, json_paths):
        """Save list of JSON paths for last session"""
        self.settings['last_session'] = json_paths[:26]  # Max 26 tabs
        self.save_settings()
    
    def get_last_session(self):
        """Get last session JSON paths"""
        return self.settings.get('last_session', [])
    
    def get(self, key):
        """Get a setting value"""
        return self.settings.get(key)
    
    def set(self, key, value):
        """Set a generic setting value"""
        self.settings[key] = value
        self.save_settings()
    
    def get_text(self, key):
        """Get a language string"""
        return self.lang.get(key, key)
    
    def get_styles(self):
        """Get the appropriate styles module based on current_style setting"""
        style_name = self.settings.get('current_style', 'dark')
        
        # Handle built-in styles
        if style_name == 'dark':
            from config import styles_dark
            return styles_dark
        elif style_name == 'light':
            from config import styles_light
            return styles_light
        else:
            # Handle custom styles
            try:
                # Custom styles are in config/custom_styles/
                custom_module = __import__(f'config.custom_styles.{style_name}', fromlist=[style_name])
                return custom_module
            except ImportError:
                # Fallback to dark if custom style not found
                from config import styles_dark
                return styles_dark
    
    def set_current_style(self, style_name):
        """Set current style"""
        self.settings['current_style'] = style_name
        # Also update theme for backward compatibility
        if style_name in ['dark', 'light']:
            self.settings['theme'] = style_name
        self.save_settings()


# Global config instance
config = Config()
