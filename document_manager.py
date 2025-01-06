from models import DocumentElement, DocumentElementType, TypeGeometry

class DocumentManager:
    @staticmethod
    def show_element(element: DocumentElement) -> dict:
        """
        Megkeresi a DocumentElement típusához tartozó TypeGeometry-t
        és előkészíti a megjelenítéshez szükséges információkat
        
        :param element: A megjelenítendő dokumentum elem
        :return: Megjelenítési információkat tartalmazó szótár
        """
        # Alapértelmezett típusgeometriák
        type_geometries = DocumentManager.get_type_geometries()
        
        # Elem típusgeometriájának kikeresése
        type_geometry = type_geometries.get(element.type, element.type_geometry)
        
        return {
            'oid': element.oid,
            'name': element.name,
            'content': element.content,
            'type': element.type.name if element.type else None,  
            'status': element.status.name if element.status else None,  
            'pid': element.pid,
            'position': element.position,
            'geometry': {
                'type_id': type_geometry.type_id,
                'wrap': type_geometry.wrap,
                'slot_ids': type_geometry.slot_ids,
                'slot_names': type_geometry.slot_names,
                'slot_types': type_geometry.slot_types,
                'slot_defaults': type_geometry.slot_defaults
            } if type_geometry else None
        }

    @staticmethod
    def get_type_geometries():
        """
        Visszaadja az összes típusgeometriát
        
        :return: Típusgeometriák szótára, ahol a kulcs a DocumentElementType
        """
        return {
            DocumentElementType.TITLE: TypeGeometry(
                type_id="TITLE",
                wrap="<H1>#></H1>",
                slot_ids="TITLE",
                slot_names="Title Text",
                slot_types="TEXT",
                slot_defaults=""
            ),
            DocumentElementType.SUBTITLE: TypeGeometry(
                type_id="SUBTITLE",
                wrap="<H2>#></H2>",
                slot_ids="SUBTITLE",
                slot_names="Subtitle Text",
                slot_types="TEXT",
                slot_defaults=""
            ),
            DocumentElementType.SYNOPSIS: TypeGeometry(
                type_id="SYNOPSIS",
                wrap="<B>#></B>",
                slot_ids="SYNOPSIS",
                slot_names="Synopsis Text",
                slot_types="TEXT",
                slot_defaults=""
            ),
            DocumentElementType.TEXT: TypeGeometry(
                type_id="TEXT",
                wrap="<P>#></P>",
                slot_ids="TEXT",
                slot_names="Text Content",
                slot_types="TEXT",
                slot_defaults=""
            ),
            DocumentElementType.BOLDTEXT: TypeGeometry(
                type_id="BOLDTEXT",
                wrap="<B>#></B>",
                slot_ids="BOLDTEXT",
                slot_names="Bold Text Content",
                slot_types="TEXT",
                slot_defaults=""
            ),
            DocumentElementType.PICTURE: TypeGeometry(
                type_id="PICTURE",
                wrap="<IMG SRC='pic#.>'></IMG>",
                slot_ids="PICID#>FILE#>PICNAME#>PICTYPE",
                slot_names="Picture ID#>Picture File#>Picture Name#>Picture Type",
                slot_types="HIDDEN#>FILE#>TEXT#>TEXT",
                slot_defaults=""
            ),
            DocumentElementType.POSITION: TypeGeometry(
                type_id="POSITION",
                wrap="<B>#><BR>#> - #></B>",
                slot_ids="NAME#>LATITUDE#>LONGITUDE",
                slot_names="Position Name#>Latitude#>Longitude",
                slot_types="TEXT#>TEXT#>TEXT",
                slot_defaults=""
            ),
            DocumentElementType.TABLE: TypeGeometry(
                type_id="TABLE",
                wrap="<TABLE>#></TABLE>",
                slot_ids="ROW#>COLUMN",
                slot_names="Row Number#>Column Number",
                slot_types="INTEGER#>INTEGER",
                slot_defaults="1#>1"
            ),
            DocumentElementType.PAGE: TypeGeometry(
                type_id="PAGE",
                wrap="<P><A HREF='#'>#</A></P>",
                slot_ids="PAGEID#>PAGETITLE",
                slot_names="Page ID#>Page Title",
                slot_types="HIDDEN#>TEXT",
                slot_defaults=""
            ),
            DocumentElementType.LINK: TypeGeometry(
                type_id="LINK",
                wrap="<A HREF='doc#>.csv'>#></A>",
                slot_ids="PAGEID#>LINKTEXT",
                slot_names="Page#>Link Text",
                slot_types="PAGEID#>TEXT",
                slot_defaults=""
            ),
            DocumentElementType.PATH: TypeGeometry(
                type_id="PATH",
                wrap="<A HREF='doc#>.csv'>#></A>",
                slot_ids="PAGEID#>TITLE",
                slot_names="Page#>Title Text",
                slot_types="HIDDEN#>HIDDEN",
                slot_defaults=""
            )
        }

    @staticmethod
    def show_page(oid: str, name: str) -> dict:
        """
        Oldal betöltése CSV fájlból
        
        :param oid: Az oldal egyedi azonosítója
        :param name: Az oldal neve
        :return: Az oldal adatait tartalmazó szótár
        """
        from models import Document, DocumentElementType
        
        try:
            # Dokumentum betöltése CSV-ből
            filename = f"doc{oid}.csv"
            document = Document.from_csv(filename, name)
            
            # Dokumentum elemek rendezése pozíció szerint
            sorted_elements = sorted(document.elements, key=lambda x: x.position)
            
            # Elemek típus szerinti csoportosítása
            path_elements = []
            subpage_elements = []
            other_elements = []
            
            for elem in sorted_elements:
                elem_info = DocumentManager.show_element(elem)
                if elem.type == DocumentElementType.PATH:
                    path_elements.append(elem_info)
                elif elem.type == DocumentElementType.PAGE:
                    subpage_elements.append(elem_info)
                else:
                    other_elements.append(elem_info)
            
            # Ha van legalább egy elem, használjuk az első elem pid-jét
            pid = sorted_elements[0].pid if sorted_elements else None
            
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

    def write_document(self, doc_info):
        """Dokumentum mentése CSV formátumban
        
        Args:
            doc_info (dict): A dokumentum adatai, ami tartalmazza az elements, path és subpages listákat
        """
        if not doc_info or 'oid' not in doc_info:
            return False
            
        # CSV fájl neve az oid alapján
        filename = f"pages/doc{doc_info['oid']}.csv"
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                # Fejléc írása
                csvfile.write("oid,name,content,type,status,pid,position\n")
                
                def format_value(value):
                    """Érték formázása CSV-hez"""
                    if value is None:
                        return '""'
                    # Ha az érték szám, ne tegyük idézőjelbe
                    if isinstance(value, (int, float)):
                        return str(value)
                    # Egyébként idézőjelbe tesszük és escape-eljük a belső idézőjeleket
                    return '"' + str(value).replace('"', '""') + '"'
                
                def write_element(element):
                    """Egy elem sorának írása"""
                    line = (
                        f"{format_value(element.get('oid'))},"
                        f"{format_value(element.get('name'))},"
                        f"{format_value(element.get('content'))},"
                        f"{format_value(element.get('type'))},"
                        f"{format_value(element.get('status'))},"
                        f"{format_value(element.get('pid'))},"
                        f"{format_value(element.get('position'))}\n"
                    )
                    csvfile.write(line)
                    # print(f"Írás: {line.strip()}")
                
                # Elements lista írása
                if 'elements' in doc_info:
                    # print("\nElements írása:")
                    for element in doc_info['elements']:
                        write_element(element)
                
                # Path lista írása
                if 'path' in doc_info:
                    # print("\nPath írása:")
                    for path in doc_info['path']:
                        write_element(path)
                
                # Subpages lista írása
                if 'subpages' in doc_info:
                    # print("\nSubpages írása:")
                    for subpage in doc_info['subpages']:
                        write_element(subpage)
            
            return True
        except Exception as e:
            print(f"Hiba a dokumentum mentése közben: {e}")
            return False

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
    display_info = DocumentManager.show_element(test_element)
    print(display_info)
