import uuid
from typing import List, Dict, Any, Optional
from enum import Enum, auto
import pandas as pd
import os
import shutil
import zipfile
from datetime import datetime
from PyQt5.QtWidgets import QLabel, QWidget, QSizePolicy
from PyQt5.QtCore import Qt

class DocumentElementType:
    """Dokumentum elem típusok.
    Az értékek az elementtypes.csv fájlból töltődnek be."""
    _instances = {}  # Tárolja az összes létrehozott példányt
    _initialized = False  # Jelzi, hogy megtörtént-e már az inicializálás
    
    def __init__(self, type_id: str):
        self.type_id = type_id
        self.name = type_id  # Alapértelmezett név a type_id
        DocumentElementType._instances[type_id] = self
    
    def __str__(self) -> str:
        return self.type_id
    
    def __repr__(self) -> str:
        return f"DocumentElementType.{self.type_id}"
    
    def __eq__(self, other) -> bool:
        if isinstance(other, str):
            return self.type_id == other
        if isinstance(other, DocumentElementType):
            return self.type_id == other.type_id
        return False
    
    def __hash__(self) -> int:
        return hash(self.type_id)
    
    @classmethod
    def initialize(cls) -> None:
        """Betölti az összes típust a CSV fájlból"""
        if cls._initialized:
            return
            
        try:
            csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "elementtypes.csv")
            df = pd.read_csv(csv_path)
            for _, row in df.iterrows():
                type_id = row['type_id']
                # Ha még nem létezik ilyen típus, létrehozzuk
                if type_id not in cls._instances:
                    instance = cls(type_id)
                    instance.name = row['type_name']  # Beállítjuk a nevet a CSV-ből
                else:
                    # Ha már létezik, frissítjük a nevet
                    cls._instances[type_id].name = row['type_name']
            cls._initialized = True
        except Exception as e:
            print(f"Hiba a típusok betöltése során: {e}")
            # Alapértelmezett típusok hiba esetén
            for type_id in ['TITLE', 'TEXT', 'PAGE', 'PATH', 'LINK', 'SUBTITLE', 'SYNOPSIS', 'BOLDTEXT', 'PICTURE', 'POSITION', 'TABLE']:
                cls(type_id)
            cls._initialized = True
    
    @classmethod
    def get(cls, type_id: str) -> Optional['DocumentElementType']:
        """Visszaad egy típust az ID alapján"""
        if not cls._initialized:
            cls.initialize()
        return cls._instances.get(type_id)
    
    @classmethod
    def values(cls) -> List['DocumentElementType']:
        """Visszaadja az összes létező típust"""
        if not cls._initialized:
            cls.initialize()
        return list(cls._instances.values())

# Inicializáljuk a típusokat azonnal a modul betöltésekor
DocumentElementType.initialize()

class SlotType(Enum):
    TEXT = auto()
    HPOSITION = auto()
    VPOSITION = auto()
    SIZE = auto()
    COLOR = auto()
    HIDDEN = auto()
    FILE = auto()
    INTEGER = auto()
    PAGEID = auto()

class DocumentElementStatus(Enum):
    NEW = auto()
    EDIT = auto()
    PRE = auto()
    PUBLIC = auto()
    DEL = auto()

class TypeGeometry:
    def __init__(
        self, 
        type_id: str, 
        type_name: str,
        body_type: str,
        wrap: str, 
        slot_ids: str, 
        slot_names: str, 
        slot_types: str,
        slot_defaults: str,
        isactive: str = "0"
    ):
        self.type_id = type_id
        self.type_name = type_name
        self.body_type = body_type
        self.wrap = wrap
        self.slot_ids = slot_ids
        self.slot_names = slot_names
        self.slot_types = slot_types
        self.slot_defaults = slot_defaults
        self.isactive = isactive

class DocumentElement:
    def __init__(
        self, 
        name: str, 
        content: str, 
        element_type: DocumentElementType,
        status: DocumentElementStatus = DocumentElementStatus.NEW,
        pid: str = None,
        position: int = 0
    ):
        self.oid = str(uuid.uuid4())  # Egyedi azonosító
        self.name = name
        self.content = content
        self.type = element_type
        self.status = status
        self.pid = pid  # Szülő dokumentum azonosítója
        self.position = position
        self.type_geometry = None  # Inicializáljuk None értékkel

        # Képek kezelése
        if element_type.type_id == "PICTURE":
            self.handle_picture(content)

    def handle_picture(self, picture_path: str):
        """Képek kezelése a pictures könyvtárban"""
        allowed_extensions = ['.png', '.jpg', '.gif']
        if not os.path.exists(picture_path):
            raise FileNotFoundError(f"A megadott kép nem létezik: {picture_path}")
        
        file_ext = os.path.splitext(picture_path)[1].lower()
        if file_ext not in allowed_extensions:
            raise ValueError(f"Nem támogatott képformátum. Csak {allowed_extensions} engedélyezettek.")
        
        pictures_dir = os.path.join(os.path.dirname(__file__), 'pictures')
        os.makedirs(pictures_dir, exist_ok=True)
        
        # Kép másolása a pictures mappába
        dest_filename = f"pic{self.oid}{file_ext}"
        dest_path = os.path.join(pictures_dir, dest_filename)
        shutil.copy2(picture_path, dest_path)
        
        # A content mostantól a kép relatív elérési útja lesz
        self.content = os.path.join('pictures', dest_filename)

    def to_csv_dict(self) -> Dict[str, Any]:
        """Dokumentum elem konvertálása CSV formátumba"""
        return {
            'oid': self.oid,
            'name': self.name,
            'content': self.content,
            'type': self.type.type_id if self.type else None,
            'status': self.status.name if self.status else None,
            'pid': self.pid,
            'position': self.position
        }

class Document:
    def __init__(self, name: str):
        self.oid = str(uuid.uuid4())  # Dokumentum egyedi azonosítója
        self.name = name
        self.elements: List[DocumentElement] = []

    def add_element(self, element: DocumentElement, position: int = -1):
        """
        Dokumentum elem hozzáadása adott pozícióra
        
        :param element: A hozzáadandó dokumentum elem
        :param position: Pozíció, ahova az elemet be kell szúrni
                         -1: dokumentum végére
                         0 vagy 1: dokumentum elejére
                         pozitív egész: adott indexre
        """
        # Pozíció korrekció
        if position < -1:
            position = -1
        
        # Ha üres a dokumentum, mindig a végére kerül
        if not self.elements:
            position = 0
        
        # Pozíció meghatározása
        if position == -1:
            # A dokumentum végére kerül
            position = max([elem.position for elem in self.elements] + [0]) + 1
        elif position <= 1:
            # A dokumentum elejére kerül, meglévő elemek pozíciójának növelése
            for elem in self.elements:
                elem.position += 1
            position = 0
        else:
            # Adott pozíciónál nagyobb pozíciójú elemek eltolása
            for elem in self.elements:
                if elem.position >= position:
                    elem.position += 1
        
        # Elem beállítása
        element.pid = self.oid
        element.position = position
        
        # Elem beszúrása a megfelelő helyre
        # Ha már létezik elem ezen a pozíción, utána szúrjuk be
        insert_index = next((i for i, elem in enumerate(self.elements) if elem.position >= position), len(self.elements))
        self.elements.insert(insert_index, element)
        
        # CSV mentése
        try:
            self.to_csv(f"doc{self.oid}.csv")
        except Exception as e:
            print(f"Hiba a dokumentum mentése során: {e}")
        
        return element

    def remove_element(self, oid: str):
        self.elements = [elem for elem in self.elements if elem.oid != oid]

    def update_element(self, oid: str, updated_element: DocumentElement):
        for i, elem in enumerate(self.elements):
            if elem.oid == oid:
                updated_element.pid = self.oid
                self.elements[i] = updated_element
                break

    def to_csv(self, filename: str):
        data = [elem.to_csv_dict() for elem in self.elements]
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False)

    @classmethod
    def from_csv(cls, filename: str, document_name: str):
        """
        Dokumentum betöltése CSV fájlból
        
        :param filename: A CSV fájl neve
        :param document_name: A dokumentum neve
        :return: Document objektum
        """
        import csv
        
        # Új dokumentum létrehozása
        document = cls(document_name)
        
        try:
            with open(filename, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    # Enum értékek konvertálása
                    element_type = DocumentElementType.get(row['type']) if row['type'] else None
                    element_status = DocumentElementStatus[row['status']] if row['status'] else None
                    
                    # Elem létrehozása
                    element = DocumentElement(
                        name=row['name'].strip('"'),
                        content=row['content'].strip('"'),
                        element_type=element_type,
                        status=element_status,
                        pid=row['pid'].strip('"'),
                        position=int(row['position'])
                    )
                    element.oid = row['oid'].strip('"')
                    
                    # Elem hozzáadása a dokumentumhoz
                    document.elements.append(element)
                    
            return document
            
        except Exception as e:
            print(f"Hiba a dokumentum betöltése során: {e}")
            return None

    def export_to_zip(self, base_dir: str = None):
        """
        Dokumentumok exportálása zip fájlba
        A zip fájl neve: save<ANSI formátumú dátum+idő>.zip
        """
        if base_dir is None:
            base_dir = os.path.join(os.path.dirname(__file__), 'exports')
        
        os.makedirs(base_dir, exist_ok=True)
        
        # Dátum ANSI formátumban
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"save{timestamp}.zip"
        zip_path = os.path.join(base_dir, zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # CSV fájl mentése
            csv_filename = f"{self.name}_{timestamp}.csv"
            csv_path = os.path.join(base_dir, csv_filename)
            self.to_csv(csv_path)
            zipf.write(csv_path, arcname=csv_filename)
            
            # Képek hozzáadása a zip fájlhoz
            pictures_dir = os.path.join(os.path.dirname(__file__), 'pictures')
            for elem in self.elements:
                if elem.type.type_id == "PICTURE":
                    pic_path = os.path.join(pictures_dir, os.path.basename(elem.content))
                    if os.path.exists(pic_path):
                        zipf.write(pic_path, arcname=os.path.join('pictures', os.path.basename(elem.content)))
            
            # Töröljük a ideiglenes CSV fájlt
            os.remove(csv_path)
        
        return zip_path

class ShowActiveElement:
    """Aktív elemek megjelenítésének kezelése"""
    
    @staticmethod
    def create_signature_widget(content: str, doc_manager) -> QLabel:
        """SIGNATURE típusú elem widget létrehozása"""
        # Content feldolgozása
        parts = content.split('#>')
        halign = parts[0].strip("'") if len(parts) > 0 else ""  # Idézőjelek eltávolítása
        textcontent = parts[1] if len(parts) > 1 else ""
        
        # Horizontális igazítás keresése
        halign_item = None
        list_items = doc_manager.show_list("HALIGN")
        
        # Keresés a megadott halign értékkel
        for item in list_items:
            if item['elementID'] == halign:
                halign_item = item
                break
        
        # Ha nincs találat, keressük az alapértelmezett elemet
        if not halign_item:
            for item in list_items:
                if item.get('isdefelement') == '1':
                    halign_item = item
                    break
        
        # Label létrehozása
        label = QLabel(textcontent)
        label.setWordWrap(True)
        label.setStyleSheet("margin: 5px; padding: 5px; width: 100%;")
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        # Horizontális igazítás beállítása
        if halign_item:
            if halign_item['elementname'] == 'Left':
                label.setAlignment(Qt.AlignLeft)
                
            elif halign_item['elementname'] == 'Center':
                label.setAlignment(Qt.AlignCenter)
            elif halign_item['elementname'] == 'Right':
                label.setAlignment(Qt.AlignRight)
        
        return label
        
    @staticmethod
    def create_widget(element_type: str, content: str, doc_manager) -> QWidget:
        """Widget létrehozása az elem típusa alapján"""
        if element_type == 'SIGNATURE':
            return ShowActiveElement.create_signature_widget(content, doc_manager)
        return None

# Példakód az export_to_zip metódus használatára
if __name__ == "__main__":
    # Dokumentum létrehozása
    doc = Document("Példa Dokumentum")
    
    # Dokumentum elemek hozzáadása
    title_elem = DocumentElement(
        name="Főcím", 
        content="VanDoor Dokumentumkezelő", 
        element_type=DocumentElementType.get("TITLE")
    )
    doc.add_element(title_elem)
    
    # Szöveg elem hozzáadása
    text_elem = DocumentElement(
        name="Bevezető", 
        content="Ez egy példa dokumentum a VanDoor rendszerben.", 
        element_type=DocumentElementType.get("TEXT")
    )
    doc.add_element(text_elem)
    
    # Kép elem hozzáadása (feltételezve, hogy van egy kép a megadott útvonalon)
    try:
        pic_elem = DocumentElement(
            name="Projekt Logo", 
            content="C:/Users/Vendel-Mohay István/CascadeProjects/VanDoor/logo.png", 
            element_type=DocumentElementType.get("PICTURE")
        )
        doc.add_element(pic_elem)
    except Exception as e:
        print(f"Hiba a kép hozzáadásakor: {e}")
    
    # Dokumentum exportálása zip fájlba
    try:
        zip_path = doc.export_to_zip()
        print(f"Dokumentum sikeresen exportálva: {zip_path}")
    except Exception as e:
        print(f"Hiba az exportálás során: {e}")
