from document_manager import DocumentManager

# Oldal betöltése és megjelenítése
page_info = DocumentManager.show_page("1", "VanDoor Test Page")

if page_info:
    print("Dokumentum adatai:")
    print(f"OID: {page_info['oid']}")
    print(f"Név: {page_info['name']}")
    print(f"PID: {page_info['pid']}")
    
    print("\nÚtvonal elemek:")
    for elem in page_info['path']:
        print(f"\nElem típus: {elem['type']}")
        print(f"Elem név: {elem['name']}")
        print(f"Tartalom: {elem['content']}")
        print(f"Pozíció: {elem['position']}")
    
    print("\nAloldalak:")
    for elem in page_info['subpages']:
        print(f"\nElem típus: {elem['type']}")
        print(f"Elem név: {elem['name']}")
        print(f"Tartalom: {elem['content']}")
        print(f"Pozíció: {elem['position']}")
    
    print("\nEgyéb elemek:")
    for elem in page_info['elements']:
        print(f"\nElem típus: {elem['type']}")
        print(f"Elem név: {elem['name']}")
        print(f"Tartalom: {elem['content']}")
        print(f"Pozíció: {elem['position']}")
else:
    print("Nem sikerült betölteni a dokumentumot.")