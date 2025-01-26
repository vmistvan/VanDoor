from models import DocumentElement, DocumentElementType, TypeGeometry
import os
import pandas as pd

class DocumentManager:
    def __init__(self):
        self.current_document = None
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.type_geometries = {}  # TypeGeometry objektumok cache-elése
        self.list_elements = []    # Lista elemek tárolása
        self.load_type_geometries()  # Típusok betöltése inicializáláskor
        self.load_list_elements()  # Lista elemek betöltése inicializáláskor
        
    def load_type_geometries(self):
        """TypeGeometry objektumok betöltése az elementtypes.csv fájlból"""
        try:
            csv_path = os.path.join(self.base_path, "elementtypes.csv")
            df = pd.read_csv(csv_path)
            
            # Típusok betöltése a DataFrame-ből
            for _, row in df.iterrows():
                type_id = row['type_id']               
                # TypeGeometry objektum létrehozása
                geometry = TypeGeometry(
                    type_id=type_id,
                    type_name=row['type_name'],
                    body_type=row['body_type'],
                    wrap=row['wrap'],
                    slot_ids=row['slot_ids'],
                    slot_names=row['slot_names'],
                    slot_types=row['slot_types'],
                    slot_defaults=row['slot_defaults'] if pd.notna(row['slot_defaults']) else "",
                    isactive=str(row['isactive']) if pd.notna(row['isactive']) else "0"
                )
                # Megfelelő DocumentElementType objektum lekérése vagy létrehozása
                element_type = DocumentElementType.get(type_id)
                if element_type:
                    self.type_geometries[element_type] = geometry
                else:
                    print(f"Hiba a típus betöltése során: {type_id}")
                    
        except Exception as e:
            print(f"Hiba a típusok betöltése során: {e}")
            self.type_geometries = {}
            
    def get_type_geometries(self):
        """TypeGeometry objektumok visszaadása"""
        return self.type_geometries
        
    def escape_content(self, content):
        """Speciális karakterek escape-elése"""
        if not content:
            return content
            
        replacements = {
            '\n': '\\n',    # Újsor
            '\r': '\\r',    # Kocsi vissza
            '\t': '\\t',    # Tab
            '<': '&lt;',    # HTML tag kezdete
            '>': '&gt;',    # HTML tag vége
            '&': '&amp;',   # HTML és karakter
            '"': '&quot;',  # Idézőjel
            "'": '&apos;',  # Aposztróf
        }
        
        result = content
        for original, escaped in replacements.items():
            result = result.replace(original, escaped)
        return result
        
    def unescape_content(self, content):
        """Escape-elt karakterek visszaalakítása az eredeti formájukra"""
        if not content:
            return content
            
        # Először a HTML karaktereket alakítjuk vissza
        html_replacements = {
            '&lt;': '<',    # HTML tag kezdete
            '&gt;': '>',    # HTML tag vége
            '&amp;': '&',   # HTML és karakter
            '&quot;': '"',  # Idézőjel
            '&apos;': "'"   # Aposztróf
        }
        
        result = content
        for escaped, original in html_replacements.items():
            result = result.replace(escaped, original)
            
        # Majd a speciális karaktereket alakítjuk vissza
        special_chars = {
            '\\n': '\n',    # Újsor
            '\\r': '\r',    # Kocsi vissza
            '\\t': '\t',    # Tab
        }
        
        for escaped, original in special_chars.items():
            result = result.replace(escaped, original)
            
        return result
        
    def get_document_element_content(self, element):
        """Dokumentum elem tartalmának lekérése"""
        if not element or not element.content:
            return ""
        return self.unescape_content(element.content)
        
    def show_element(self, element: DocumentElement) -> dict:
        """
        Megkeresi a DocumentElement típusához tartozó TypeGeometry-t
        és előkészíti a megjelenítéshez szükséges információkat
        
        :param element: A megjelenítendő dokumentum elem
        :return: Megjelenítési információkat tartalmazó szótár
        """
        if not element:
            return None
            
        # TypeGeometry keresése
        type_geometry = self.type_geometries.get(element.type)
        if not type_geometry:
            return None
        
        return {
            'oid': element.oid,
            'name': element.name,
            'content': self.get_document_element_content(element),
            'type': element.type.name if element.type else None,  
            'status': element.status.name if element.status else None,  
            'pid': element.pid,
            'position': element.position,
            'geometry': {
                'type_id': type_geometry.type_id,
                'type_name': type_geometry.type_name,
                'body_type': type_geometry.body_type,
                'wrap': type_geometry.wrap,
                'slot_ids': type_geometry.slot_ids,
                'slot_names': type_geometry.slot_names,
                'slot_types': type_geometry.slot_types,
                'slot_defaults': type_geometry.slot_defaults
            } if type_geometry else None
        }

    def show_page(self, oid: str, name: str) -> dict:
        """
        Oldal betöltése CSV fájlból
        
        :param oid: Az oldal egyedi azonosítója
        :param name: Az oldal neve
        :return: Az oldal adatait tartalmazó szótár
        """
        from models import Document, DocumentElementType
        import os
        
        try:
            # Dokumentum betöltése CSV-ből
            filename = os.path.join(self.base_path, "pages", f"doc{oid}.csv")
            document = Document.from_csv(filename, name)
            
            # Dokumentum elemek rendezése pozíció szerint
            document.elements.sort(key=lambda x: x.position)
            
            # Elemek típus szerinti csoportosítása
            path_elements = []
            subpage_elements = []
            other_elements = []
            
            for elem in document.elements:
                elem_info = self.show_element(elem)
                if elem_info:
                    # Típus alapján rendezzük az elemeket
                    elem_type = elem.type.type_id if elem.type else None
                    if elem_type == "PATH":
                        path_elements.append(elem_info)
                    elif elem_type == "PAGE":
                        subpage_elements.append(elem_info)
                    else:
                        other_elements.append(elem_info)
            
            # Ha van legalább egy elem, használjuk az első elem pid-jét
            pid = document.elements[0].pid if document.elements else None
            
            # Dokumentum mentése az osztály példányban
            self.current_document = document
            
            return {
                'oid': oid,
                'name': name,
                'pid': pid,
                'path': path_elements,
                'subpages': subpage_elements,
                'elements': other_elements
            }
        
        except FileNotFoundError:
            print(f"Nem található a(z) {filename} dokumentum.")
            return None
        except Exception as e:
            print(f"Hiba a dokumentum betöltése során: {e}")
            return None

    def read_document(self, page="1"):
        """Dokumentum olvasása fájlból"""
        try:
            # CSV fájl beolvasása
            filename = os.path.join(self.base_path, "pages", f"doc{page}.csv")
            df = pd.read_csv(filename, dtype=str)  # Minden oszlopot string típusként olvasunk be
            
            # Dokumentum adatok inicializálása
            doc_info = {
                'oid': page,
                'name': f"doc{page}",
                'elements': [],
                'path': [],
                'subpages': []
            }
            
            # Sorok feldolgozása
            for _, row in df.iterrows():
                element_dict = row.to_dict()
                
                # Ellenőrizzük, hogy aktív típus-e
                element_type = DocumentElementType.get(element_dict['type'])
                type_geometry = self.type_geometries.get(element_type)
                is_active = type_geometry and type_geometry.isactive == '1'
                
                # Csak akkor unescape-eljük, ha nem aktív típus
                if not is_active:
                    element_dict['content'] = self.unescape_content(element_dict['content'])
                
                # PATH és PAGE típusú elemek külön kezelése
                if element_dict['type'] == 'PATH':
                    doc_info['path'].append(element_dict)
                elif element_dict['type'] == 'PAGE':
                    doc_info['subpages'].append(element_dict)
                else:
                    doc_info['elements'].append(element_dict)
            
            return doc_info
            
        except FileNotFoundError:
            print(f"A dokumentum nem található: {filename}")
            return None
        except Exception as e:
            print(f"Hiba a dokumentum olvasása során: {e}")
            return None

    def write_document(self, doc_info):
        """Dokumentum írása fájlba"""
        if not doc_info or 'oid' not in doc_info:
            return False
            
        # CSV fájl neve az oid alapján
        filename = os.path.join(self.base_path, "pages", f"doc{doc_info['oid']}.csv")
        
        # Összeállítjuk a mentendő elemek listáját
        elements_to_save = []
        
        # Normál elemek hozzáadása
        for elem in doc_info['elements']:
            # Ha DocumentElement objektum, akkor annak attribútumait használjuk
            if isinstance(elem, DocumentElement):
                # Ellenőrizzük, hogy aktív típus-e
                type_geometry = self.type_geometries.get(elem.type)
                is_active = type_geometry and type_geometry.isactive == '1'
                elements_to_save.append({
                    'oid': int(elem.oid),  # oid számként
                    'name': elem.name,
                    'content': elem.content if is_active else self.escape_content(elem.content),
                    'type': elem.type.name if elem.type else None,
                    'status': elem.status.name if elem.status else None,
                    'pid': elem.pid,
                    'position': int(elem.position)  # position számként
                })
            else:  # Ha szótár, akkor azt használjuk
                # Ellenőrizzük, hogy aktív típus-e
                element_type = DocumentElementType.get(elem['type'])
                type_geometry = self.type_geometries.get(element_type)
                is_active = type_geometry and type_geometry.isactive == '1'
                element_dict = {
                    'oid': int(elem['oid']),  # oid számként
                    'name': elem['name'],
                    'content': elem['content'] if is_active else self.escape_content(elem['content']),
                    'type': elem['type'],
                    'status': elem['status'],
                    'pid': elem['pid'],
                    'position': int(elem['position'])  # position számként
                }
                elements_to_save.append(element_dict)
                
        # PATH típusú elemek hozzáadása
        if 'path' in doc_info and doc_info['path']:
            for path_elem in doc_info['path']:
                # Csak a szükséges mezőket mentjük, és növeljük a pozíciót
                elements_to_save.append({
                    'oid': int(path_elem['oid']),  # oid számként
                    'name': path_elem['name'],
                    'content': path_elem['content'],
                    'type': path_elem['type'],
                    'status': path_elem['status'],
                    'pid': path_elem['pid'],
                    'position': int(path_elem['position'])  # position számként
                })
                
        # PAGE típusú elemek hozzáadása
        if 'subpages' in doc_info and doc_info['subpages']:
            for page_elem in doc_info['subpages']:
                # Csak a szükséges mezőket mentjük, és növeljük a pozíciót
                elements_to_save.append({
                    'oid': int(page_elem['oid']),  # oid számként
                    'name': page_elem['name'],
                    'content': page_elem['content'],
                    'type': page_elem['type'],
                    'status': page_elem['status'],
                    'pid': page_elem['pid'],
                    'position': int(page_elem['position'])  # position számként
                })

        try:
            # CSV fájl létrehozása és mentése
            df = pd.DataFrame(elements_to_save)
            
            # Oszlopok típusának beállítása
            df['oid'] = df['oid'].astype(int)  # oid oszlop egész számmá konvertálása
            df['position'] = df['position'].astype(int)  # position oszlop egész számmá konvertálása
            
            # CSV fájl mentése:
            # - index=False: ne legyen index oszlop
            # - quoting=1: QUOTE_MINIMAL - csak akkor használjon idézőjelet, ha szükséges
            # - quotechar='"': idézőjel karakter
            # - header=True: oszlopnevek kiírása
            df.to_csv(filename, 
                     index=False, 
                     quoting=1,  # QUOTE_MINIMAL
                     quotechar='"',
                     header=True)
            
            # Frissítjük a current_document-et
            self.current_document = doc_info
            return True
        except Exception as e:
            print(f"Hiba a dokumentum mentése során: {e}")
            return False

    def load_list_elements(self):
        """Lista elemek betöltése a lists.csv fájlból"""
        try:
            csv_path = os.path.join(self.base_path, "lists.csv")
            df = pd.read_csv(csv_path, dtype=str)  # Minden mezőt string típusként olvasunk
            
            # Lista elemek betöltése a DataFrame-ből
            self.list_elements = []
            for _, row in df.iterrows():
                list_element = {
                    'listname': row['listname'],
                    'elementID': row['elementID'],
                    'elementname': row['elementname'],
                    'isdefelement': row['isdefelement']
                }
                self.list_elements.append(list_element)
                
        except Exception as e:
            print(f"Hiba a lista elemek betöltése során: {e}")
            self.list_elements = []
            
    def show_list(self, listname="HALIGN"):
        """
        Visszaadja a megadott listanévhez tartozó elemeket
        
        :param listname: A kért lista neve (alapértelmezett: "HALIGN")
        :return: A listához tartozó elemek listája
        """
        return [elem for elem in self.list_elements if elem['listname'] == listname]

    def escape_page(self, content):
        """
        Speciális karakterek escape-elése page elemekhez.
        A soremelés karaktereket eltávolítja, minden más escape-elés ugyanúgy működik.
        """
        if not content:
            return content
            
        # Először eltávolítjuk a soremelés karakterek minden prezentációs módját
        content = content.replace('\n', ' ').replace('\r', ' ').replace('\\n', ' ').replace('\\r', ' ')
            
        # HTML karakterek escape-elése
        replacements = {
            '\t': '\\t',    # Tab
            '<': '&lt;',    # HTML tag kezdete
            '>': '&gt;',    # HTML tag vége
            '&': '&amp;',   # HTML és karakter
            '"': '&quot;',  # Idézőjel
            "'": '&apos;',  # Aposztróf
        }
        
        result = content
        for original, escaped in replacements.items():
            result = result.replace(original, escaped)
        return result

# Példa használat
if __name__ == "__main__":
    from models import DocumentElement, DocumentElementType, DocumentElementStatus
    
    # Példa dokumentum elem létrehozása
    test_element = DocumentElement(
        name="Főcím",
        content="VanDoor Dokumentumkezelő",
        element_type=DocumentElementType.TITLE,
        status=DocumentElementStatus.NEW
    )
    
    # Elem megjelenítési információinak lekérése
    display_info = DocumentManager().show_element(test_element)
    print(display_info)
