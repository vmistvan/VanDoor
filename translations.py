import json
import os

class Translator:
    def __init__(self, language='hu'):
        self.language = language
        self.translations = {}
        self.load_translations()
    
    def load_translations(self):
        """Betölti a nyelvi fájlt"""
        try:
            file_path = os.path.join(
                os.path.dirname(__file__),
                'locales',
                f'{self.language}.json'
            )
            with open(file_path, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
        except Exception as e:
            print(f"Hiba a fordítások betöltésekor: {e}")
            # Fallback az angol nyelvre
            if self.language != 'en':
                self.language = 'en'
                self.load_translations()
    
    def get_text(self, key, default=None):
        """Visszaadja a fordítást a megadott kulcshoz"""
        try:
            # Támogatja a nested kulcsokat (pl. "element_types.TITLE")
            value = self.translations
            for k in key.split('.'):
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default or key
    
    def change_language(self, language):
        """Nyelv váltása"""
        self.language = language
        self.load_translations()