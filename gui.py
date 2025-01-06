import sys
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QTreeWidget, QTreeWidgetItem, QTextEdit, 
                            QPushButton, QLabel, QComboBox, QSizePolicy, QTableWidget,
                            QTableWidgetItem, QHeaderView, QScrollArea, QGroupBox, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from document_manager import DocumentManager
from translations import Translator
from config_manager import ConfigManager

class ClickableLabel(QLabel):
    clicked = pyqtSignal(str)  # Signal a kattintás eseményhez

    def __init__(self, text, content):
        super().__init__(text)
        self.content = content
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("color: blue; text-decoration: none;")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.content)

class VanDoorMainWindow(QMainWindow):
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
        
        # Fő elrendezés
        main_layout = QVBoxLayout(central_widget)

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
        
        main_layout.addWidget(self.top_panel)

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
        for up_button, new_button, down_button in self.element_buttons:
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
        self.add_new_element(row)
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
        self.config_manager.set_state('current_language', lang_code)
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
        self.doc_info = self.doc_manager.show_page(page, title)
        
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
                group_box = QGroupBox(f"{element['oid']}: {element['name']} ({element['type']})")
                group_box_layout = QVBoxLayout(group_box)
                content_label = QLabel(str(element['content']))
                content_label.setWordWrap(True)
                
                # Ha PATH típusú elem, akkor kattinthatóvá tesszük
                if element['type'] == 'PATH':
                    clickable_label = ClickableLabel(str(element['content']), str(element['content']))
                    clickable_label.clicked.connect(self.handle_path_click)
                    group_box_layout.addWidget(clickable_label)
                else:
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
                content = path_element['content']
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
            for element in self.doc_info['subpages']:
                content = element['content']
                page, title = content.split('#>')
                label = ClickableLabel(title, content)
                label.clicked.connect(self.handle_path_click)  # Ugyanazt a handlert használjuk
                self.subpage_elements_layout.addWidget(label)

    def handle_path_click(self, content):
        """PATH elem kattintás kezelése"""
        page, title = content.split('#>')
        self.load_initial_document(page, title)

    def move_element_up(self, current_position):
        """Elem mozgatása felfelé a position érték alapján"""
        if not hasattr(self, 'doc_info') or 'elements' not in self.doc_info:
            return
            
        # Keressük meg a jelenlegi és az előző elemet
        current_element = None
        previous_element = None
        
        for element in self.doc_info['elements']:
            if str(element.get('position', '')) == str(current_position):
                current_element = element
            elif str(element.get('position', '')) == str(int(current_position) - 1):
                previous_element = element
                
        if current_element and previous_element:
            # Pozíciók cseréje
            current_element['position'] = int(current_position) - 1
            previous_element['position'] = int(current_position)
            
            # Lista rendezése position szerint
            self.doc_info['elements'].sort(key=lambda x: int(x.get('position', 0)))
            
            # Dokumentum mentése
            self.doc_manager.write_document(self.doc_info)
            
            # UI frissítése
            self.load_initial_document(self.current_page, self.current_title)

    def add_new_element(self, row):
        """Új elem hozzáadása a kiválasztott sor után"""
        print(f"Új elem hozzáadása a(z) {row}. sor után")
        # TODO: Implementálja az új elem hozzáadásának logikáját

    def move_element_down(self, current_position):
        """Elem mozgatása lefelé a position érték alapján"""
        if not hasattr(self, 'doc_info') or 'elements' not in self.doc_info:
            return
            
        # Keressük meg a jelenlegi és a következő elemet
        current_element = None
        next_element = None
        
        for element in self.doc_info['elements']:
            if str(element.get('position', '')) == str(current_position):
                current_element = element
            elif str(element.get('position', '')) == str(int(current_position) + 1):
                next_element = element
                
        if current_element and next_element:
            # Pozíciók cseréje
            current_element['position'] = int(current_position) + 1
            next_element['position'] = int(current_position)
            
            # Lista rendezése position szerint
            self.doc_info['elements'].sort(key=lambda x: int(x.get('position', 0)))
            
            # Dokumentum mentése
            self.doc_manager.write_document(self.doc_info)
            
            # UI frissítése
            self.load_initial_document(self.current_page, self.current_title)

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
        # TODO: Implementáld az új aloldal létrehozását
        pass

def main():
    app = QApplication(sys.argv)
    window = VanDoorMainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()