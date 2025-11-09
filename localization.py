# Localization system

import json
import os
from typing import Dict

class Localization:
    def __init__(self, lang_code="en"):
        self.lang_code = lang_code
        self.translations = {}
        self.load_language(lang_code)
    
    def load_language(self, lang_code):
        lang_file = os.path.join("lang", f"{lang_code}.json")
        if os.path.exists(lang_file):
            try:
                with open(lang_file, 'r', encoding='utf-8') as f:
                    self.translations = json.load(f)
            except Exception as e:
                print(f"Error loading language file: {e}")
                self.translations = {}
        else:
            self.translations = {}
    
    def tr(self, key: str, default: str = None) -> str:
        return self.translations.get(key, default or key)
    
    def set_language(self, lang_code):
        self.lang_code = lang_code
        self.load_language(lang_code)