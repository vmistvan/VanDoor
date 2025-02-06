import sys
import os
import json
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QScrollArea, QTableWidget, QTableWidgetItem,
    QDialog, QFormLayout, QLineEdit, QSpinBox, QComboBox, QListWidget,
    QListWidgetItem, QGroupBox, QGridLayout, QFileDialog, QTextEdit,
    QSizePolicy, QSpacerItem, QStackedWidget, QHeaderView, QTreeWidget, 
    QTreeWidgetItem, QGroupBox, QFrame, QMenu
    )
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont
from document_manager import DocumentManager
from config_manager import ConfigManager
from translations import Translator
from models import ShowActiveElement, DocumentElement, DocumentElementType, DocumentElementStatus

class ClickableLabel(QLabel):
    clicked = pyqtSignal(str)  # Signal a kattintás eseményhez

    def __init__(self, text, content, element=None, parent=None, doc_manager=None):
        super().__init__(text)
        self.content = content
        self.element = element
        self.parent = parent
        self.doc_manager = doc_manager
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("color: blue; text-decoration: none;")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.content)
        elif event.button() == Qt.RightButton and self.element:
            context_menu = ElementContextMenu(self.parent, self.element, self.doc_manager, called_from='subpages')
            menu = context_menu.create_menu(event)
            menu.exec_(event.globalPos())

    def contextMenuEvent(self, event):
        context_menu = ElementContextMenu(self.parent, self.element, self.doc_manager, called_from='subpages')
        menu = context_menu.create_menu(event)
        menu.exec_(event.globalPos())

class ElementGroupBox(QGroupBox):
    """Elem megjelenítő doboz kontextus menüvel"""
    
    def __init__(self, title, parent, element, doc_manager):
        super().__init__(title)
        self.parent = parent
        self.element = element
        self.doc_manager = doc_manager
        
    def contextMenuEvent(self, event):
        context_menu = ElementContextMenu(self.parent, self.element, self.doc_manager)
        menu = context_menu.create_menu(event)
        menu.exec_(event.globalPos())

class ElementEditorDialog(QDialog):
    def __init__(self, parent=None, doc_info=None):
        super().__init__(parent)
        self.parent = parent
        self.doc_info = doc_info
        self.doc_manager = parent.doc_manager
        self.selected_type = None
        self.field_widgets = {}
        self.position = None
        
        # Dialog beállítások
        self.setWindowTitle(self.parent.config_manager.get_translation('add_element_title'))
        
        # Ablak méretének beállítása a szülő ablak 80%-ára
        parent_rect = self.parent.rect()
        dialog_width = int(parent_rect.width() * 0.8)
        dialog_height = int(parent_rect.height() * 0.8)
        self.resize(dialog_width, dialog_height)
        
        # Központi pozicionálás
        self.move(
            self.parent.mapToGlobal(parent_rect.center()) - 
            self.rect().center()
        )
        
        self.setModal(True)
        
        # Layout beállítások
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Típus választó konténer
        type_container = QHBoxLayout()
        type_container.setAlignment(Qt.AlignRight)
        
        # Típus választó címke
        type_label = QLabel(self.parent.config_manager.get_translation('choose_element_type'))
        type_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        type_container.addWidget(type_label, alignment=Qt.AlignLeft)
        
        # Típus lista
        self.type_list = QListWidget()
        self.type_list.setSizeAdjustPolicy(QListWidget.AdjustToContents)
        
        # Típusok hozzáadása a listához
        type_geometries = self.doc_manager.get_type_geometries()
        
        for element_type, geometry in type_geometries.items():
            stripped = geometry.body_type.strip('"')
            if stripped == "YES":
                item = QListWidgetItem(geometry.type_name)
                item.setData(Qt.UserRole, element_type)  # Tároljuk az enum értéket
                self.type_list.addItem(item)
        
        # Lista méretének beállítása a tartalom alapján
        self.type_list.setFixedWidth(
            self.type_list.sizeHintForColumn(0) + 20  # +20 a görgetősávnak
        )
        type_container.addWidget(self.type_list)
        layout.addLayout(type_container)
        
        # Mezők konténer
        fields_container = QWidget()
        self.fields_layout = QFormLayout()  
        fields_container.setLayout(self.fields_layout)
        
        # Görgetési terület a mezőkhöz
        scroll = QScrollArea()
        scroll.setWidget(fields_container)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)
        
        # Gombok
        button_layout = QHBoxLayout()
        
        self.back_button = QPushButton(self.parent.config_manager.get_translation('back'))
        self.back_button.clicked.connect(self.show_type_selection)
        self.back_button.hide()
        button_layout.addWidget(self.back_button)
        
        button_layout.addStretch()
        
        self.next_button = QPushButton(self.parent.config_manager.get_translation('next'))
        self.next_button.clicked.connect(self.show_fields)
        self.next_button.setEnabled(False)  # Kezdetben inaktív
        button_layout.addWidget(self.next_button)
        
        self.add_button = QPushButton(self.parent.config_manager.get_translation('add'))
        self.add_button.clicked.connect(self.add_element)
        self.add_button.hide()
        button_layout.addWidget(self.add_button)
        
        self.cancel_button = QPushButton(self.parent.config_manager.get_translation('cancel'))
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # Típus kiválasztás eseménykezelő
        self.type_list.itemClicked.connect(self.handle_type_selection)
        
    def show_fields(self):
        """Mezők megjelenítése"""
        # UI elemek átváltása
        self.type_list.hide()
        self.next_button.hide()
        self.fields_layout.parent().show()
        self.back_button.show()
        self.add_button.show()
        
        # Címke hozzáadása
        fields_label = QLabel(self.parent.config_manager.get_translation('fill_element_data'))
        fields_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        fields_label.setAlignment(Qt.AlignLeft)
        self.fields_layout.addRow(fields_label)
        
        # Típus geometria lekérése
        type_geometries = self.doc_manager.get_type_geometries()
        geometry = type_geometries.get(self.selected_type)
        
        if geometry:
            # Slot-ok feldolgozása
            slot_ids = geometry.slot_ids.split('#>')
            slot_names = geometry.slot_names.split('#>')
            slot_types = geometry.slot_types.split('#>')
            slot_defaults = geometry.slot_defaults.split('#>') if geometry.slot_defaults else []
            
            # Ha ez egy létező elem szerkesztése
            existing_values = {}
            if hasattr(self, 'doc_info') and self.doc_info:
                element = self.doc_info.get('element')
                if element:
                    # A content mező unescapelése
                    content = self.doc_manager.unescape_content(element.content) if element.content else ""
                    existing_values = {'content': content}
            
            # Mezők létrehozása minden slot-hoz
            for i, (slot_id, slot_name, slot_type) in enumerate(zip(slot_ids, slot_names, slot_types)):
                slot_default = slot_defaults[i] if i < len(slot_defaults) else ""
                
                # Ha van létező érték, azt használjuk alapértelmezettként
                if slot_id in existing_values:
                    slot_default = existing_values[slot_id]
                
                if slot_type != 'HIDDEN':
                    # Beviteli mező típus alapján
                    if slot_type == 'TEXT':
                        widget = QTextEdit()
                        widget.setMinimumHeight(200)  # 8 sor magasság (kb. 25 pixel/sor)
                        widget.setPlainText(slot_default)
                    elif slot_type.startswith('LIST'):
                        # Lista típus feldolgozása
                        list_parts = slot_type.split(':')
                        list_name = list_parts[1] if len(list_parts) > 1 else "HALIGN"
                        
                        # Lista elemek lekérése
                        list_items = []
                        if list_name:
                            list_items = self.doc_manager.show_list(list_name)
                        if not list_items:  # Ha üres a lista vagy nincs lista név, az alapértelmezett listát használjuk
                            list_items = self.doc_manager.show_list()
                        
                        # ComboBox létrehozása a lista elemekhez
                        widget = QComboBox()
                        for item in list_items:
                            widget.addItem(item['elementname'], item['elementID'])
                        
                        # Alapértelmezett érték beállítása
                        if slot_default:
                            index = widget.findData(slot_default)
                            if index >= 0:
                                widget.setCurrentIndex(index)
                    elif slot_type == 'INTEGER':
                        widget = QSpinBox()
                        widget.setMinimum(0)
                        widget.setMaximum(100)
                        if slot_default:
                            widget.setValue(int(slot_default))
                    elif slot_type == 'FILE':
                        widget = QLineEdit()
                        widget.setReadOnly(True)
                        browse_button = QPushButton("Browse")
                        browse_button.clicked.connect(
                            lambda checked, w=widget: self.handle_file_browse(w)
                        )
                        container = QWidget()
                        layout = QHBoxLayout(container)
                        layout.addWidget(widget)
                        layout.addWidget(browse_button)
                        layout.setContentsMargins(0, 0, 0, 0)
                        self.field_widgets[slot_id] = widget
                        self.fields_layout.addRow(slot_name, container)
                        continue  # Skip the default widget addition
                    else:
                        widget = QLineEdit()
                        widget.setText(slot_default)
                    
                    # Widget hozzáadása
                    self.field_widgets[slot_id] = widget
                    self.fields_layout.addRow(slot_name, widget)
        
        # Stretch hozzáadása
        spacer_widget = QWidget()
        spacer_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        spacer_widget.setMinimumHeight(40)
        self.fields_layout.addRow("", spacer_widget)
        
    def handle_type_selection(self):
        """Típus kiválasztás kezelése"""
        current_item = self.type_list.currentItem()
        if not current_item:
            return
            
        # Kiválasztott típus lekérése
        self.selected_type = current_item.data(Qt.UserRole)
        
        # Tovább gomb aktiválása
        self.next_button.setEnabled(True)
        
    def showEvent(self, event):
        """Megjelenéskor középre pozicionálás"""
        parent_rect = self.parent.rect()
        self.move(
            self.parent.mapToGlobal(parent_rect.center()) - 
            self.rect().center()
        )
        
        # ConfigManager újratöltése az aktuális nyelvvel
        self.parent.config_manager.load_translations()
        
    def on_type_selected(self, item):
        """Típus kiválasztás eseménykezelő"""
        selected_type = item.data(Qt.UserRole)
        self.selected_type = selected_type.type_id
        self.next_button.setEnabled(True)  # Típus kiválasztásakor aktiválódik
        
    def show_type_selection(self):
        """Típus választó megjelenítése"""
        self.type_list.show()
        self.next_button.show()
        self.fields_layout.parent().hide()
        self.back_button.hide()
        self.add_button.hide()
        
    def select_file(self, slot_id):
        """Fájl kiválasztása"""
        file_name, _ = QFileDialog.getOpenFileName(self)
        if file_name:
            self.field_widgets[slot_id].setText(file_name)
            
    def add_element(self):
        """Elem hozzáadása"""
        from models import DocumentElementType  # Explicit import a függvényen belül
        
        # Elem típusának lekérése
        element_type = DocumentElementType.get(self.selected_type)
        if not element_type:
            return
            
        # Értékek összegyűjtése
        values = {}
        for slot_id, widget in self.field_widgets.items():
            if isinstance(widget, QLineEdit):
                values[slot_id] = widget.text()
            elif isinstance(widget, QTextEdit):
                values[slot_id] = widget.toPlainText()
            elif isinstance(widget, QPushButton):  # FILE típus
                values[slot_id] = widget.text()
            elif isinstance(widget, QSpinBox):
                values[slot_id] = str(widget.value())
            elif isinstance(widget, QComboBox):
                values[slot_id] = widget.currentData()
        
        # Config és State kezelése
        config_manager = self.parent.config_manager
        
        # Next OID kezelése
        next_oid = config_manager.get_state('next_oid', '1')
        config_manager.set_state('next_oid', str(int(next_oid) + 1))
        
        # Elem típusának neve (pl. "TEXT", "BOLDTEXT")
        type_name = element_type.type_id
        
        # Position konvertálása int típusra és növelése
        insert_position = int(self.position) + 1
        
        # Új elem létrehozása
        from models import DocumentElement, DocumentElementType, DocumentElementStatus
        new_element = DocumentElement(
            name=f"{type_name}{next_oid}",
            content="#>".join(values.values()),
            element_type=element_type,
            status=DocumentElementStatus.NEW,
            pid=self.doc_info['elements'][0].get('pid', '1') if self.doc_info['elements'] else "1",
            position=insert_position
        )
        
        # Az oid manuális beállítása
        new_element.oid = str(next_oid)
        
        # Position értékek módosítása a dokumentumban
        elements = []
        for element_dict in self.doc_info['elements']:
            # DocumentElement objektum létrehozása a szótárból
            element = DocumentElement(
                name=element_dict['name'],
                content=element_dict['content'],
                element_type=DocumentElementType.get(element_dict['type']),
                status=DocumentElementStatus[element_dict['status']],
                pid=element_dict['pid'],
                position=int(element_dict['position'])
            )
            element.oid = element_dict['oid']
            
            # Ha az elem pozíciója nagyobb vagy egyenlő az új elem pozíciójával,
            # növeljük eggyel
            if element.position >= insert_position:
                element.position += 1
                
            elements.append(element)
        
        # Új elem beszúrása
        elements.append(new_element)
        
        # Path és Subpages elemek pozíciójának növelése
        if 'path' in self.doc_info:
            for path_element in self.doc_info['path']:
                path_element['position'] = str(int(path_element['position']) + 1)
                
        if 'subpages' in self.doc_info:
            for subpage_element in self.doc_info['subpages']:
                subpage_element['position'] = str(int(subpage_element['position']) + 1)
        
        # Dokumentum mentése előtt rendezzük a listákat position szerint
        elements.sort(key=lambda x: x.position)
        if 'path' in self.doc_info:
            self.doc_info['path'].sort(key=lambda x: int(x['position']))
        if 'subpages' in self.doc_info:
            self.doc_info['subpages'].sort(key=lambda x: int(x['position']))
        
        # Dokumentum mentése
        self.doc_manager.write_document({
            'oid': self.doc_info['oid'],
            'name': self.doc_info['name'],
            'elements': elements,
            'path': self.doc_info.get('path', []),
            'subpages': self.doc_info.get('subpages', [])
        })
                
        
        # Dialog bezárása
        self.accept()
        
        # Dokumentum újratöltése a főablakban
        self.parent.load_initial_document(
            self.doc_info['oid'],
            self.doc_info['name']
        )
        
class AddSubPage(QDialog):
    """Új aloldal hozzáadása dialógus"""
    def __init__(self, parent=None, doc_info=None):
        super().__init__(parent)
        self.parent = parent
        self.doc_info = doc_info
        self.doc_manager = parent.doc_manager
        
        # Dialog beállítások
        self.setWindowTitle(self.parent.config_manager.get_translation('add_subpage_title'))
        
        # Ablak méretének beállítása a szülő ablak 80%-ára
        parent_rect = self.parent.rect()
        dialog_width = int(parent_rect.width() * 0.8)
        dialog_height = int(parent_rect.height() * 0.8)
        self.resize(dialog_width, dialog_height)
        
        # Központi pozicionálás
        self.move(
            self.parent.mapToGlobal(parent_rect.center()) - 
            self.rect().center()
        )
        
        self.setModal(True)
        
        # Layout beállítások
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Név beviteli mező konténer
        name_container = QHBoxLayout()
        
        # Név címke
        name_label = QLabel(self.parent.config_manager.get_translation('new_page_name_label'))
        name_label.setStyleSheet("font-size: 14px;")
        name_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        name_container.addWidget(name_label)
        
        # Név beviteli mező
        self.name_input = QLineEdit()
        self.name_input.setObjectName("new_page_name")
        name_container.addWidget(self.name_input)
        
        layout.addLayout(name_container)
        
        # Gombok konténer
        button_container = QHBoxLayout()
        button_container.setAlignment(Qt.AlignRight)
        
        # Mégse gomb
        self.cancel_button = QPushButton(self.parent.config_manager.get_translation('cancel'))
        self.cancel_button.clicked.connect(self.handle_cancel)
        button_container.addWidget(self.cancel_button)
        
        # Hozzáad gomb
        self.add_button = QPushButton(self.parent.config_manager.get_translation('add'))
        self.add_button.clicked.connect(self.handle_add)
        self.add_button.setEnabled(False)  # Kezdetben inaktív
        button_container.addWidget(self.add_button)
        
        layout.addLayout(button_container)
        
        # Szövegmező változás figyelése
        self.name_input.textChanged.connect(self.handle_text_changed)
        
    def handle_cancel(self):
        """Mégse gomb kezelése"""
        self.reject()
        # Oldal frissítése
        self.parent.load_initial_document()
        
    def handle_add(self):
        """Hozzáad gomb kezelése"""
        try:
            # Következő OID-k lekérése
            config_manager = self.parent.config_manager
            link_oid = config_manager.get_state('next_oid', '1')
            page_oid = str(int(link_oid) + 1)
            new_path_oid = str(int(page_oid) + 1)
            
            # next_oid növelése (eredeti + 3)
            config_manager.set_state('next_oid', str(int(link_oid) + 3))
            
            # Új oldal neve
            new_page_name = self.name_input.text()
            if not new_page_name:
                return
                
            # Maximum pozíció meghatározása
            max_path_pos = max([int(p['position']) for p in self.doc_info.get('path', []) if 'position' in p] or [0])
            max_subpages_pos = max([int(p['position']) for p in self.doc_info.get('subpages', []) if 'position' in p] or [0])
            new_position = max(max_path_pos, max_subpages_pos) + 1
            
            # Új subpage elem létrehozása
            new_subpage = {
                'oid': link_oid,
                'name': f"PAGE{page_oid}",
                'content': f"{page_oid}#>{self.doc_manager.escape_page(new_page_name)}",
                'type': "PAGE",
                'status': "NEW",
                'pid': self.doc_info['oid'],
                'position': str(new_position)
            }
            
            # Subpages lista frissítése
            if 'subpages' not in self.doc_info:
                self.doc_info['subpages'] = []
            self.doc_info['subpages'].append(new_subpage)
            
            # Dokumentum mentése előtt rendezzük a listákat position szerint
            self.doc_info['subpages'].sort(key=lambda x: int(x['position']))
            if 'path' in self.doc_info:
                self.doc_info['path'].sort(key=lambda x: int(x['position']))
            
            # Dokumentum mentése
            if self.doc_manager.write_document(self.doc_info):
                # Új dokumentum létrehozása
                new_doc_info = {
                    'oid': page_oid,
                    'name': f"doc{page_oid}",
                    'elements': [{
                        'oid': page_oid,
                        'name': f"TITLE{page_oid}",
                        'content': self.doc_manager.escape_page(new_page_name),
                        'type': "TITLE",
                        'status': "NEW",
                        'pid': self.doc_info['oid'],
                        'position': "1"
                    }],
                    'subpages': [],
                    'path': []
                }
                
                # Path lista másolása és új elem hozzáadása
                if 'path' in self.doc_info:
                    new_doc_info['path'] = self.doc_info['path'].copy()
                
                # Új path elem hozzáadása
                new_path = {
                    'oid': new_path_oid,
                    'name': f"PATH{page_oid}",
                    'content': f"{page_oid}#>{self.doc_manager.escape_page(new_page_name)}",
                    'type': "PATH",
                    'status': "NEW",
                    'pid': self.doc_info['oid'],
                    'position': str(max_path_pos + 1)
                }
                new_doc_info['path'].append(new_path)
                
                # Új dokumentum mentése
                if self.doc_manager.write_document(new_doc_info):
                    self.accept()
                    # Az eredeti dokumentum újratöltése a jelenlegi oldal adataival
                    current_title = next((elem['content'] for elem in self.doc_info.get('elements', []) 
                                if elem.get('type') == 'TITLE'), '')
                    self.parent.load_initial_document(page=str(self.doc_info['oid']), title=current_title)
                else:
                    print("Hiba az új dokumentum mentése során")
            else:
                print("Hiba a dokumentum mentése során")
                
        except Exception as e:
            print(f"Hiba az új aloldal létrehozása során: {e}")
        
    def handle_text_changed(self):
        """Szövegmező változásának kezelése"""
        # Eltávolítjuk a whitespace karaktereket és ellenőrizzük, hogy maradt-e valami
        has_content = bool(self.name_input.text().strip())
        self.add_button.setEnabled(has_content)
        
class ElementContextMenu:
    """Elem kontextus menü kezelése"""
    
    def __init__(self, parent, element, doc_manager, called_from='elements'):
        self.parent = parent
        self.element = element
        self.doc_manager = doc_manager
        self.called_from = called_from  # 'elements' vagy 'subpages'
        
    def create_menu(self, event):
        """Kontextus menü létrehozása"""
        menu = QMenu(self.parent)  # Parent megadása a menünek
        menu.setStyleSheet("QMenu { menu-scrollable: 1; padding-left: 0px; } QMenu::item { padding-left: 5px; padding-right: 5px;} QMenu::separator { margin-left: 0px; }")
        
        if self.element['status'] == "PUBLIC":
            # Címsor hozzáadása
            title_action = menu.addAction(self.parent.config_manager.get_translation('context_menu.status_titles.public'))
            title_action.setEnabled(False)  # Nem kattintható
            menu.addSeparator()  # Elválasztó vonal
            
            # PUBLIC állapotú elem menüpontjai
            recall_action = menu.addAction(self.parent.config_manager.get_translation('context_menu.recall'))
            recall_action.triggered.connect(self.handle_recall)
            
            delete_action = menu.addAction(self.parent.config_manager.get_translation('context_menu.delete'))
            delete_action.triggered.connect(self.handle_delete)
            
        elif self.element['status'] == "PRE":
            # Címsor hozzáadása
            title_action = menu.addAction(self.parent.config_manager.get_translation('context_menu.status_titles.pre'))
            title_action.setEnabled(False)  # Nem kattintható
            menu.addSeparator()  # Elválasztó vonal
            
            # PRE állapotú elem menüpontjai
            back_to_edit_action = menu.addAction(self.parent.config_manager.get_translation('context_menu.back_to_edit'))
            back_to_edit_action.triggered.connect(self.handle_back_to_edit)
            
            publish_action = menu.addAction(self.parent.config_manager.get_translation('context_menu.publish'))
            publish_action.triggered.connect(self.handle_publish)
            
            delete_action = menu.addAction(self.parent.config_manager.get_translation('context_menu.delete'))
            delete_action.triggered.connect(self.handle_delete)
            
        elif self.element['status'] == "NEW":
            # Címsor hozzáadása
            title_action = menu.addAction(self.parent.config_manager.get_translation('context_menu.status_titles.new'))
            title_action.setEnabled(False)  # Nem kattintható
            menu.addSeparator()  # Elválasztó vonal
            
            # NEW állapotú elem menüpontjai
            edit_action = menu.addAction(self.parent.config_manager.get_translation('context_menu.edit'))
            edit_action.triggered.connect(self.handle_edit)
            
            pre_publish_action = menu.addAction(self.parent.config_manager.get_translation('context_menu.pre_publish'))
            pre_publish_action.triggered.connect(self.handle_pre_publish)
            
            delete_action = menu.addAction(self.parent.config_manager.get_translation('context_menu.delete'))
            delete_action.triggered.connect(self.handle_delete)
            
        elif self.element['status'] == "EDIT":
            # Címsor hozzáadása
            title_action = menu.addAction(self.parent.config_manager.get_translation('context_menu.status_titles.edit'))
            title_action.setEnabled(False)  # Nem kattintható
            menu.addSeparator()  # Elválasztó vonal
            
            # EDIT állapotú elem menüpontjai
            edit_action = menu.addAction(self.parent.config_manager.get_translation('context_menu.edit'))
            edit_action.triggered.connect(self.handle_edit)
            
            pre_publish_action = menu.addAction(self.parent.config_manager.get_translation('context_menu.pre_publish'))
            pre_publish_action.triggered.connect(self.handle_pre_publish)
            
            delete_action = menu.addAction(self.parent.config_manager.get_translation('context_menu.delete'))
            delete_action.triggered.connect(self.handle_delete)
            
        elif self.element['status'] == "DEL":
            # Címsor hozzáadása
            title_action = menu.addAction(self.parent.config_manager.get_translation('context_menu.status_titles.del'))
            title_action.setEnabled(False)  # Nem kattintható
            menu.addSeparator()  # Elválasztó vonal
            
            # DEL állapotú elem menüpontjai
            undelete_action = menu.addAction(self.parent.config_manager.get_translation('context_menu.undelete'))
            undelete_action.triggered.connect(self.handle_undelete)
            
        return menu  # Visszaadjuk a menüt
        
    def handle_recall(self):
        """Recall menüpont kezelése"""
        self.element['status'] = "EDIT"
        self.save_and_refresh()
        
    def handle_back_to_edit(self):
        """Back to edit menüpont kezelése"""
        self.element['status'] = "EDIT"
        self.save_and_refresh()
        
    def handle_publish(self):
        """Publish menüpont kezelése"""
        self.element['status'] = "PUBLIC"
        self.save_and_refresh()
        
    def handle_edit(self):
        """Edit menüpont kezelése"""
        print("Editálás")
    
    def handle_pre_publish(self):
        """Pre publish menüpont kezelése"""
        self.element['status'] = 'PRE'
        self.save_and_refresh()
    
    def handle_delete(self):
        """Delete menüpont kezelése"""
        self.element['status'] = 'DEL'
        self.save_and_refresh()
    
    def handle_undelete(self):
        """Undelete menüpont kezelése"""
        self.element['status'] = 'EDIT'
        self.save_and_refresh()
    
    def save_and_refresh(self):
        """Dokumentum mentése és újratöltése"""
        # Az elem státuszának módosítása a megfelelő listában
        if self.called_from == 'elements':
            for element in self.parent.doc_info['elements']:
                if element['oid'] == self.element['oid']:
                    element['status'] = self.element['status']
                    break
        elif self.called_from == 'subpages':
            for subpage in self.parent.doc_info['subpages']:
                if subpage['oid'] == self.element['oid']:
                    subpage['status'] = self.element['status']
                    break
                    
        # Dokumentum mentése előtt rendezzük a listákat position szerint
        if 'elements' in self.parent.doc_info:
            self.parent.doc_info['elements'].sort(key=lambda x: int(x['position']))
        if 'path' in self.parent.doc_info:
            self.parent.doc_info['path'].sort(key=lambda x: int(x['position']))
        if 'subpages' in self.parent.doc_info:
            self.parent.doc_info['subpages'].sort(key=lambda x: int(x['position']))
        
        # Dokumentum mentése
        self.doc_manager.write_document(self.parent.doc_info)
        # Csak az oid-t adjuk át
        self.parent.load_initial_document(str(self.parent.doc_info['oid']))

class VanDoorMainWindow(QMainWindow):
    """VanDoor főablak"""
    
    # Státusz színek
    STATUS_COLORS = {
        'NEW': '#dddddd',  # szürke
        'EDIT': '#ffffd0',  # halványsárga
        'DEL': '#ffd0d0',   # halványpiros
        'PUBLIC': '#d0d0ff',   # halványkék
        'PRE': '#d0ffd0'    # halványzöld
    }
    
    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.translator = Translator(self.config_manager.get_state('current_language', 'hu'))
        self.doc_manager = DocumentManager()
        self.element_buttons = []  # Gombok tárolása a nyelvváltáshoz
        self.disabled_positions = {
            'up': set(),    # Felfelé mozgatás tiltott pozíciói
            'down': set(),  # Lefelé mozgatás tiltott pozíciói
            'new': set()    # Új elem tiltott pozíciói
        }
        self.position_timers = {}  # position -> timer
        self.init_ui()
        
        # Oszlopszélességek beállítása egy kicsivel később
        QTimer.singleShot(100, self.adjust_table_columns)
        
        # Ablak állapot visszaállítása
        window_state = self.config_manager.get_state('window', {})
        if window_state:
            self.setGeometry(
                window_state.get('x', 100),
                window_state.get('y', 100),
                window_state.get('width', 1200),
                window_state.get('height', 800)
            )
            if window_state.get('is_maximized', False):
                self.showMaximized()
        
        # Utolsó dokumentum betöltése
        last_doc = self.config_manager.get_state('last_document', {})
        if last_doc:
            self.load_initial_document(
                last_doc.get('page', "1"),
                last_doc.get('title', "VanDoor Test Page")
            )
    
    def init_ui(self):
        """Ablak felületének inicializálása"""
        # Ablak alapértelmezett mérete a konfigurációból
        self.setWindowTitle(self.translator.get_text('window_title'))
        window_config = self.config_manager.get_config('ui.window', {})
        self.setGeometry(
            100, 100,
            window_config.get('default_width', 1200),
            window_config.get('default_height', 800)
        )
        self.setMinimumSize(
            window_config.get('min_width', 800),
            window_config.get('min_height', 600)
        )
        
        # Központi widget létrehozása
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Felső panel (max 20% magasság, min 100px)
        self.top_panel = QWidget()
        self.top_panel.setMinimumHeight(100)
        panels_config = self.config_manager.get_config('ui.panels', {})
        max_height_percent = panels_config.get('top_panel_max_height_percent', 20)
        self.top_panel.setMaximumHeight(int(self.height() * max_height_percent / 100))  # 20% maximum magasság
        self.top_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.top_panel.setStyleSheet("background-color: #ffffff;")  # Fehér háttérszín
        
        # Top panel layout
        top_layout = QVBoxLayout(self.top_panel)
        
        # Cím label
        self.title_label = QLabel("")
        self.title_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        self.title_label.setAlignment(Qt.AlignCenter)
        top_layout.addWidget(self.title_label)
        
        # Path elemek container
        self.path_container = QWidget()
        self.path_layout = QHBoxLayout(self.path_container)
        self.path_layout.setAlignment(Qt.AlignLeft)
        top_layout.addWidget(self.path_container)
        
        main_layout = QVBoxLayout(central_widget)
        
        # Dokumentum kezelő rész (fa nézet és szerkesztő)
        doc_layout = QHBoxLayout()
        
        # Bal oldali panel (dokumentum struktúra)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setAlignment(Qt.AlignTop)  # Top alignment

        # Cím hozzáadása
        self.subpages_label = QLabel(self.translator.get_text('subpages'))
        self.subpages_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
        left_layout.addWidget(self.subpages_label)

        # Scroll area a labeleknek
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(50)  # Minimum magasság
        scroll_content = QWidget()
        self.subpage_elements_layout = QVBoxLayout(scroll_content)
        self.subpage_elements_layout.setAlignment(Qt.AlignTop)  # Top alignment
        scroll_area.setWidget(scroll_content)
        
        left_layout.addWidget(scroll_area)
        
        # Új aloldal gomb
        self.new_subpage_btn = QPushButton(self.translator.get_text('new_subpage'))
        self.new_subpage_btn.clicked.connect(self.add_new_subpage)
        left_layout.addWidget(self.new_subpage_btn)
        
        # Jobb oldali panel (dokumentum tartalom)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Eszköztár
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        
        # Új elem hozzáadása gomb és típus választó
        self.add_button = QPushButton(self.translator.get_text('new_element'))
        self.type_combo = QComboBox()
        for key in ["TITLE", "TEXT", "PATH", "PAGE", "LINK"]:
            self.type_combo.addItem(
                self.translator.get_text(f'element_types.{key}'),
                key
            )
        
        # Könyvjelző gombok és címke
        self.save_bookmark_btn = QPushButton(self.translator.get_text('save_bookmark'))
        self.load_bookmark_btn = QPushButton(self.translator.get_text('load_bookmark'))
        self.bookmark_label = QLabel()
        self.update_bookmark_label()
        
        toolbar_layout.addWidget(self.save_bookmark_btn)
        toolbar_layout.addWidget(self.load_bookmark_btn)
        toolbar_layout.addWidget(self.bookmark_label)
        toolbar_layout.addStretch()
        
        # Gombok eseménykezelőinek beállítása
        self.save_bookmark_btn.clicked.connect(self.save_current_as_bookmark)
        self.load_bookmark_btn.clicked.connect(self.load_bookmark)
        
        # Elemek táblázat
        self.elements_table = QTableWidget()
        self.elements_table.setColumnCount(2)
        self.elements_table.horizontalHeader().setVisible(False)
        self.elements_table.verticalHeader().setVisible(False)
        
        right_layout.addWidget(toolbar)
        right_layout.addWidget(self.elements_table)
        
        # Panelek hozzáadása a dokumentum kezelő részhez
        doc_layout.addWidget(left_panel, 1)
        doc_layout.addWidget(right_panel, 2)
        
        # Nyelv választó panel alul
        bottom_panel = QWidget()
        bottom_layout = QHBoxLayout(bottom_panel)
        bottom_layout.addStretch()  # Kitölti a bal oldalt
        
        # Nyelv választó
        self.language_combo = QComboBox()
        self.language_combo.addItems(['Magyar', 'English'])
        self.language_combo.currentTextChanged.connect(self.change_language)
        
        # Aktuális nyelv beállítása a combo boxban
        current_lang = self.config_manager.get_state('current_language', 'hu')
        self.language_combo.setCurrentText('English' if current_lang == 'en' else 'Magyar')
        
        bottom_layout.addWidget(self.language_combo)
        
        # Fő elrendezés összeállítása
        main_layout.addWidget(self.top_panel)
        main_layout.addLayout(doc_layout)
        main_layout.addWidget(bottom_panel)
        
        # Kezdeti dokumentum betöltése
        self.load_initial_document()
    
    def create_element_buttons(self, row, total_elements, element):
        """Elem gombok létrehozása"""
        button_widget = QWidget()
        button_layout = QVBoxLayout(button_widget)
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        # Gombok létrehozása
        up_button = QPushButton(self.translator.get_text('move_up'))
        new_button = QPushButton(self.translator.get_text('new_element'))
        down_button = QPushButton(self.translator.get_text('move_down'))
        
        # Position tulajdonság beállítása
        position = str(element.get('position', ''))  # Biztosítjuk, hogy string legyen
        up_button.position = position
        new_button.position = position  # Ez is kell
        down_button.position = position
        
        # Gombok eseménykezelőinek beállítása
        up_button.clicked.connect(lambda: self.handle_up_button_click(position))
        new_button.clicked.connect(lambda: self.handle_new_button_click(position, row))
        down_button.clicked.connect(lambda: self.handle_down_button_click(position))
        
        # Gombok engedélyezése/tiltása
        up_button.setEnabled(row > 0 and position not in self.disabled_positions['up'])
        new_button.setEnabled(position not in self.disabled_positions['new'])
        down_button.setEnabled(row < total_elements - 1 and position not in self.disabled_positions['down'])
        
        # Gombok hozzáadása a layouthoz
        button_layout.addWidget(up_button)
        button_layout.addWidget(new_button)
        button_layout.addWidget(down_button)
        
        # Gombok tárolása a későbbi frissítéshez
        self.element_buttons.append((up_button, new_button, down_button))
        
        return button_widget

    def update_button_states(self):
        """Gombok állapotának frissítése"""        
        for up_button, new_button, down_button in self.element_buttons[:]:  # Másolaton iterálunk
            if up_button and up_button.parent() is not None:
                position = str(up_button.position)  # Biztosítjuk, hogy string legyen
                row = int(position) - 1
                total_elements = len(self.doc_info['elements'])
                
                # Alap engedélyezés/tiltás pozíció alapján
                up_enabled = row > 0 and position not in self.disabled_positions['up']
                down_enabled = row < total_elements - 1 and position not in self.disabled_positions['down']
                new_enabled = position not in self.disabled_positions['new']
                               
                
                up_button.setEnabled(up_enabled)
                new_button.setEnabled(new_enabled)
                down_button.setEnabled(down_enabled)

    def temporarily_disable_position(self, position, button_type, seconds=5):
        """Pozíció ideiglenes letiltása adott gomb típusra"""
        position = str(position)  # Biztosítjuk, hogy string legyen
        
        
        # Pozíció letiltása
        self.disabled_positions[button_type].add(position)
                
        # Ha már van timer ehhez a pozícióhoz, töröljük
        timer_key = (position, button_type)
        if timer_key in self.position_timers:
            self.position_timers[timer_key].stop()
            del self.position_timers[timer_key]
        
        # Új timer létrehozása
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self.enable_position(position, button_type))
        self.position_timers[timer_key] = timer
        timer.start(seconds * 1000)
        
        # Gombok állapotának azonnali frissítése
        self.update_button_states()

    def enable_position(self, position, button_type):
        """Pozíció újraengedélyezése"""
        position = str(position)  # Biztosítjuk, hogy string legyen
             
        self.disabled_positions[button_type].discard(position)
                
        timer_key = (position, button_type)
        if timer_key in self.position_timers:
            del self.position_timers[timer_key]
        
        self.update_button_states()

    def handle_up_button_click(self, position):
        """Fel gomb kezelése"""
        self.move_element_up(position)
        self.temporarily_disable_position(position, 'up')

    def handle_new_button_click(self, position, row):
        """Új elem gomb kezelése"""
        if hasattr(self, 'element_editor'):
            self.element_editor.close()
        self.element_editor = ElementEditorDialog(self, self.doc_info)
        self.element_editor.position = position
        if self.element_editor.exec_() == QDialog.Accepted:
            # Az aktuális oldal adataival töltjük újra
            current_doc = self.doc_manager.read_document(str(self.doc_info['oid']))
            self.doc_info = current_doc
            # Aloldalak listájának frissítése
            for i in reversed(range(self.subpage_elements_layout.count())): 
                self.subpage_elements_layout.itemAt(i).widget().setParent(None)
            for subpage in current_doc.get('subpages', []):
                content = self.doc_manager.unescape_content(str(subpage['content']))  # Unescape-elés
                page, title = content.split('#>')
                label = ClickableLabel(title, content, subpage, self, self.doc_manager)
                label.clicked.connect(self.handle_path_click)  # Ugyanazt a handlert használjuk
                # Háttérszín beállítása status alapján
                bg_color = self.STATUS_COLORS.get(subpage['status'], '#ffffff')  # alapértelmezett: fehér
                label.setStyleSheet(f"background-color: {bg_color};")
                self.subpage_elements_layout.addWidget(label)
        self.temporarily_disable_position(position, 'new')

    def handle_down_button_click(self, position):
        """Le gomb kezelése"""
        self.move_element_down(position)
        self.temporarily_disable_position(position, 'down')

    def resizeEvent(self, event):
        """Ablak átméretezés kezelése"""
        super().resizeEvent(event)
        
        # Top panel magasság frissítése
        panels_config = self.config_manager.get_config('ui.panels', {})
        max_height_percent = panels_config.get('top_panel_max_height_percent', 20)
        self.top_panel.setMaximumHeight(int(self.height() * max_height_percent / 100))
        
        # Táblázat oszlopok frissítése
        self.adjust_table_columns()
        
        # Ablak állapot mentése
        if not self.isMaximized():
            geo = self.geometry()
            self.config_manager.save_window_state(
                geo.x(), geo.y(),
                geo.width(), geo.height(),
                False
            )
    
    def changeEvent(self, event):
        """Ablak állapot változás kezelése"""
        super().changeEvent(event)
        if event.type() == event.WindowStateChange:
            # Maximalizált állapot mentése
            self.config_manager.save_window_state(
                self.geometry().x(),
                self.geometry().y(),
                self.geometry().width(),
                self.geometry().height(),
                self.isMaximized()
            )
    
    def adjust_table_columns(self):
        """Táblázat oszlopszélességének beállítása"""
        table_width = self.elements_table.width()
        if table_width > 0:
            table_config = self.config_manager.get_config('ui.table', {})
            content_width = int(table_width * table_config.get('content_column_width_percent', 80) / 100)
            buttons_width = int(table_width * table_config.get('buttons_column_width_percent', 15) / 100)
            self.elements_table.setColumnWidth(0, content_width)
            self.elements_table.setColumnWidth(1, buttons_width)
    
    def change_language(self, language):
        """Nyelv váltása"""
        lang_code = 'en' if language == 'English' else 'hu'
        self.translator.change_language(lang_code)
        self.config_manager.change_language(lang_code)  # Ez is frissíti a fordításait
        self.update_ui_texts()
    
    def update_window_title(self, title_content):
        """Ablak címének frissítése"""
        # Maximum 36 karakter + esetleg 3 pont
        if len(title_content) > 36:
            title_content = title_content[:36] + "..."
        
        self.setWindowTitle(f"VanDoor - {title_content}")

    def update_ui_texts(self):
        """UI szövegek frissítése"""
        self.save_bookmark_btn.setText(self.translator.get_text('save_bookmark'))
        self.load_bookmark_btn.setText(self.translator.get_text('load_bookmark'))
        self.update_bookmark_label()
        self.subpages_label.setText(self.translator.get_text('subpages'))
        self.new_subpage_btn.setText(self.translator.get_text('new_subpage'))
        
        # Elem gombok szövegeinek frissítése csak ha vannak még gombok
        if hasattr(self, 'element_buttons'):
            for buttons in self.element_buttons[:]:  # Másolaton iterálunk
                try:
                    up_btn, new_btn, down_btn = buttons
                    up_btn.setText(self.translator.get_text('move_up'))
                    new_btn.setText(self.translator.get_text('new_element'))
                    down_btn.setText(self.translator.get_text('move_down'))
                except RuntimeError:
                    # Ha valamelyik gomb már törölve van, eltávolítjuk a listából
                    self.element_buttons.remove(buttons)
    
    def update_bookmark_label(self):
        """Könyvjelző címke frissítése"""
        bookmark = self.config_manager.get_bookmark()
        self.bookmark_label.setText(f"{self.translator.get_text('bookmark_label')}: {bookmark['title']}")
    
    def load_initial_document(self, page="1", title="VanDoor Test Page"):
        """Kezdeti dokumentum betöltése"""
        self.current_page = page
        self.current_title = title
        
        # Dokumentum betöltése
        self.doc_info = self.doc_manager.read_document(page)
        
        # Töröljük a régi elemeket
        self.elements_table.setRowCount(0)
        self.element_buttons.clear()
        
        if self.doc_info and 'elements' in self.doc_info:
            elements = self.doc_info['elements']
            # Táblázat sorainak beállítása
            self.elements_table.setRowCount(len(elements))
            
            # Keressük meg az első TITLE típusú elemet
            title_found = False
            
            # Táblázat feltöltése
            for row, element in enumerate(elements):
                # Ha ez az első TITLE típusú elem, beállítjuk az ablak címét és a top panel címét
                if not title_found and element['type'] == 'TITLE':
                    self.update_window_title(str(element['content']))
                    self.title_label.setText(str(element['content']))
                    title_found = True
                
                # Első oszlop: GroupBox
                group_box = ElementGroupBox(f"{element['oid']}: {element['name']} ({element['type']})", self, element, self.doc_manager)
                
                # Háttérszín beállítása status alapján
                bg_color = self.STATUS_COLORS.get(element['status'], '#ffffff')  # alapértelmezett: fehér
                group_box.setStyleSheet(f"QGroupBox {{ background-color: {bg_color}; }}")
                
                group_box_layout = QVBoxLayout(group_box)
                
                # Content megjelenítése az isactive flag alapján
                if element.get('isactive', True) and element['type'] == 'SIGNATURE':
                    content_widget = ShowActiveElement.create_widget(
                        element['type'],
                        self.doc_manager.unescape_content(str(element['content'])),
                        self.doc_manager
                    )
                    if content_widget:
                        group_box_layout.addWidget(content_widget)
                else:
                    content_label = QLabel(self.doc_manager.unescape_content(str(element['content'])))
                    content_label.setWordWrap(True)
                    group_box_layout.addWidget(content_label)
                
                self.elements_table.setCellWidget(row, 0, group_box)
                
                # Második oszlop: Gombok
                button_widget = self.create_element_buttons(row, len(elements), element)
                self.elements_table.setCellWidget(row, 1, button_widget)
                
                # Dinamikus sormagasság beállítása
                group_box_height = group_box.sizeHint().height()
                button_height = button_widget.sizeHint().height()
                row_height = max(group_box_height, button_height)
                self.elements_table.setRowHeight(row, row_height)

        # Path elemek frissítése
        # Először töröljük az összes elemet a path_layout-ból
        while self.path_layout.count():
            item = self.path_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Path elemek hozzáadása
        if self.doc_info and 'path' in self.doc_info:
            sorted_path = sorted(self.doc_info['path'], key=lambda x: x['position'])
            for i, path_element in enumerate(sorted_path):
                content = self.doc_manager.unescape_content(str(path_element['content']))  # Unescape-elés
                page, title = content.split('#>')
                label = ClickableLabel(title, content)
                label.clicked.connect(self.handle_path_click)
                self.path_layout.addWidget(label)
                if i < len(sorted_path) - 1:
                    separator = QLabel(" > ")
                    self.path_layout.addWidget(separator)
        self.path_layout.addStretch()
        
        # Subpage elements megjelenítése kattintható labelekkel
        if self.doc_info and 'subpages' in self.doc_info:
            for i in reversed(range(self.subpage_elements_layout.count())): 
                self.subpage_elements_layout.itemAt(i).widget().setParent(None)
            for subpage in self.doc_info['subpages']:
                content = self.doc_manager.unescape_content(str(subpage['content']))  # Unescape-elés
                page, title = content.split('#>')
                label = ClickableLabel(title, content, subpage, self, self.doc_manager)
                label.clicked.connect(self.handle_path_click)  # Ugyanazt a handlert használjuk
                # Háttérszín beállítása status alapján
                bg_color = self.STATUS_COLORS.get(subpage['status'], '#ffffff')  # alapértelmezett: fehér
                label.setStyleSheet(f"background-color: {bg_color};")
                self.subpage_elements_layout.addWidget(label)

    def handle_path_click(self, content):
        """PATH elem kattintás kezelése"""
        page, title = content.split('#>')
        self.load_initial_document(page, title)

    def move_element_up(self, position):
        """
        Elem mozgatása felfelé
        
        :param position: Az elem jelenlegi pozíciója
        """
        from models import DocumentElement, DocumentElementType, DocumentElementStatus
        
        # Position konvertálása int típusra
        current_pos = int(position)
        if current_pos <= 1:  # Az első elem nem mozgatható feljebb
            return
            
        # Elemek listájának konvertálása DocumentElement objektumokká
        elements = []
        for element_dict in self.doc_info['elements']:
            # Elem típusának lekérése
            element_type = DocumentElementType.get(element_dict['type'])
            if not element_type:
                continue
                
            # Elem létrehozása
            element = DocumentElement(
                name=element_dict['name'],
                content=element_dict['content'],
                element_type=element_type,
                status=DocumentElementStatus[element_dict['status']],
                pid=element_dict['pid'],
                position=int(element_dict['position'])
            )
            element.oid = element_dict['oid']
            
            # Ha az elem pozíciója nagyobb vagy egyenlő az új elem pozíciójával,
            # növeljük eggyel
            if element.position >= current_pos:
                element.position += 1
                
            elements.append(element)
            
        # PATH típusú elemek pozícióinak növelése
        if 'path' in self.doc_info:
            for path_element in self.doc_info['path']:
                if int(path_element['position']) >= current_pos:
                    path_element['position'] = str(int(path_element['position']) + 1)
                    
        # PAGE típusú elemek pozícióinak növelése
        if 'subpages' in self.doc_info:
            for page_element in self.doc_info['subpages']:
                if int(page_element['position']) >= current_pos:
                    page_element['position'] = str(int(page_element['position']) + 1)
                    
        # A mozgatandó elem és az előtte lévő elem megkeresése
        current_element = None
        previous_element = None
        for element in elements:
            if element.position == current_pos:
                current_element = element
            elif element.position == current_pos - 1:
                previous_element = element
                
        if current_element and previous_element:
            # Pozíciók cseréje
            current_element.position, previous_element.position = previous_element.position, current_element.position
            
            # Dokumentum mentése előtt rendezzük a listákat position szerint
            elements.sort(key=lambda x: x.position)
            if 'path' in self.doc_info:
                self.doc_info['path'].sort(key=lambda x: int(x['position']))
            if 'subpages' in self.doc_info:
                self.doc_info['subpages'].sort(key=lambda x: int(x['position']))
            
            # Dokumentum mentése
            self.doc_manager.write_document({
                'oid': self.doc_info['oid'],
                'name': self.doc_info['name'],
                'elements': elements,
                'path': self.doc_info['path'],
                'subpages': self.doc_info['subpages']
            })
            
            # Dokumentum újratöltése
            self.load_initial_document(
                self.doc_info['oid'],
                self.doc_info['name']
            )
            
    def move_element_down(self, position):
        """
        Elem mozgatása lefelé
        
        :param position: Az elem jelenlegi pozíciója
        """
        from models import DocumentElement, DocumentElementType, DocumentElementStatus
        
        # Position konvertálása int típusra
        current_pos = int(position)
        
        # Elemek listájának konvertálása DocumentElement objektumokká
        elements = []
        for element_dict in self.doc_info['elements']:
            # Elem típusának lekérése
            element_type = DocumentElementType.get(element_dict['type'])
            if not element_type:
                continue
                
            # Elem létrehozása
            element = DocumentElement(
                name=element_dict['name'],
                content=element_dict['content'],
                element_type=element_type,
                status=DocumentElementStatus[element_dict['status']],
                pid=element_dict['pid'],
                position=int(element_dict['position'])
            )
            element.oid = element_dict['oid']
            
            # Ha az elem pozíciója nagyobb vagy egyenlő az új elem pozíciójával,
            # növeljük eggyel
            if element.position > current_pos:
                element.position += 1
                
            elements.append(element)
            
        # PATH típusú elemek pozícióinak növelése
        if 'path' in self.doc_info:
            for path_element in self.doc_info['path']:
                if int(path_element['position']) > current_pos:
                    path_element['position'] = str(int(path_element['position']) + 1)
                    
        # PAGE típusú elemek pozícióinak növelése
        if 'subpages' in self.doc_info:
            for page_element in self.doc_info['subpages']:
                if int(page_element['position']) > current_pos:
                    page_element['position'] = str(int(page_element['position']) + 1)
                    
        # A mozgatandó elem és az utána következő elem megkeresése
        current_element = None
        next_element = None
        for element in elements:
            if element.position == current_pos:
                current_element = element
            elif element.position == current_pos + 1:
                next_element = element
                
        if current_element and next_element:
            # Pozíciók cseréje
            current_element.position, next_element.position = next_element.position, current_element.position
            
            # Dokumentum mentése előtt rendezzük a listákat position szerint
            elements.sort(key=lambda x: x.position)
            if 'path' in self.doc_info:
                self.doc_info['path'].sort(key=lambda x: int(x['position']))
            if 'subpages' in self.doc_info:
                self.doc_info['subpages'].sort(key=lambda x: int(x['position']))
            
            # Dokumentum mentése
            self.doc_manager.write_document({
                'oid': self.doc_info['oid'],
                'name': self.doc_info['name'],
                'elements': elements,
                'path': self.doc_info['path'],
                'subpages': self.doc_info['subpages']
            })
            
            # Dokumentum újratöltése
            self.load_initial_document(
                self.doc_info['oid'],
                self.doc_info['name']
            )
            
    def add_new_element(self, row):
        """Új elem hozzáadása a kiválasztott sor után"""
        print(f"Új elem hozzáadása a(z) {row}. sor után")
        # TODO: Implementálja az új elem hozzáadásának logikáját

    def save_current_as_bookmark(self):
        """Aktuális dokumentum mentése könyvjelzőként"""
        if hasattr(self, 'current_page') and hasattr(self, 'current_title'):
            self.config_manager.save_bookmark(
                self.current_page,
                self.current_title
            )
            self.update_bookmark_label()
    
    def load_bookmark(self):
        """Könyvjelző betöltése"""
        bookmark = self.config_manager.get_bookmark()
        self.load_initial_document(bookmark['page'], bookmark['title'])

    def add_new_subpage(self):
        """Új aloldal hozzáadása"""
        if hasattr(self, 'subpage_dialog'):
            self.subpage_dialog.close()
        # Frissítsük a doc_info-t a legfrissebb állapottal
        current_doc = self.doc_manager.read_document(str(self.doc_info['oid']))
        self.subpage_dialog = AddSubPage(self, current_doc)
        self.subpage_dialog.exec_()
        
    def get_element_types(self):
        """Visszaadja a választható elem típusokat"""
        type_geometries = self.doc_manager.get_type_geometries()
        result = []
        for t, g in type_geometries.items():
            stripped = g.body_type.strip('"')
            if stripped == "YES":
                result.append((t, g.type_name))
        return result

def main():
    app = QApplication(sys.argv)
    window = VanDoorMainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()