import json
import os
from typing import Dict, Any, Optional

class ConfigManager:
    def __init__(self, config_dir: str = "config"):
        """
        Konfiguráció és állapot kezelő
        
        :param config_dir: Konfiguráció könyvtár elérési útja
        """
        self.config_dir = config_dir
        self.config_file = os.path.join(config_dir, "config.json")
        self.state_file = os.path.join(config_dir, "state.json")
        
        # Konfiguráció betöltése
        self.config = self._load_json(self.config_file)
        self.state = self._load_json(self.state_file)
    
    def _load_json(self, file_path: str) -> Dict[str, Any]:
        """JSON fájl betöltése"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"A {file_path} fájl nem található!")
            return {}
        except json.JSONDecodeError:
            print(f"Hiba a {file_path} fájl olvasása közben!")
            return {}
    
    def _save_json(self, file_path: str, data: Dict[str, Any]) -> bool:
        """JSON fájl mentése"""
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Hiba a {file_path} fájl mentése közben: {e}")
            return False
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Konfiguráció érték lekérése
        
        :param key: Konfiguráció kulcs (pl. "ui.window.default_width")
        :param default: Alapértelmezett érték, ha a kulcs nem található
        :return: Konfiguráció érték
        """
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """
        Állapot érték lekérése
        
        :param key: Állapot kulcs (pl. "window.width")
        :param default: Alapértelmezett érték, ha a kulcs nem található
        :return: Állapot érték
        """
        keys = key.split('.')
        value = self.state
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def set_state(self, key: str, value: Any) -> bool:
        """
        Állapot érték beállítása
        
        :param key: Állapot kulcs (pl. "window.width")
        :param value: Új érték
        :return: True ha sikeres, False ha nem
        """
        keys = key.split('.')
        current = self.state
        
        # Navigálás a megfelelő szintre
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        # Érték beállítása
        current[keys[-1]] = value
        
        # Állapot mentése
        return self._save_json(self.state_file, self.state)
    
    def save_window_state(self, x: int, y: int, width: int, height: int, is_maximized: bool) -> bool:
        """
        Ablak állapotának mentése
        
        :return: True ha sikeres, False ha nem
        """
        self.state['window'] = {
            'x': x,
            'y': y,
            'width': width,
            'height': height,
            'is_maximized': is_maximized
        }
        return self._save_json(self.state_file, self.state)
    
    def save_bookmark(self, page: str, title: str) -> bool:
        """
        Könyvjelző mentése
        
        :return: True ha sikeres, False ha nem
        """
        self.state['bookmark'] = {
            'page': page,
            'title': title
        }
        return self._save_json(self.state_file, self.state)
    
    def get_bookmark(self) -> dict:
        """
        Könyvjelző lekérése
        
        :return: Könyvjelző adatok (page, title)
        """
        return self.state.get('bookmark', {
            'page': "1",
            'title': "VanDoor Test Page"
        })
