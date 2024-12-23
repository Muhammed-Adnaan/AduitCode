from PyQt5.QtWidgets import (
    QDesktopWidget, QApplication,
    QFrame,
    QSizePolicy,
    QHBoxLayout,
    QSplitter,
    QVBoxLayout,
    QComboBox,
    QTabWidget,
    QLineEdit, QCheckBox, QLabel,
    QListWidget,
    QSpacerItem,
    QMessageBox, QStatusBar, QFileDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QEnterEvent, QMouseEvent
from PyQt5.Qsci import QsciScintilla

from editor import Editor
from file_manager import FileManager
from fuzzy_searcher import SearchItem, SearchWorker
from heading import Heading

from qframelesswindow import FramelessMainWindow
import ollama 

import threading
import sys
import os
from pathlib import Path
import jedi
from PyQt5.QtGui import QIcon

# Main window class
class MainWindow(FramelessMainWindow):
    def __init__(self):
        super().__init__()
        self.app_name = "QCodeEditor"

        self.current_file = None
        self.current_side_bar = None
        self.envs = list(jedi.find_virtualenvs())
        self.init_ui()
        self.conversation_history = []
        # self.header = Heading(self)		
    @property
    def current_file(self) -> Path:
        return self._current_file

    @current_file.setter
    def current_file(self, file: Path):
        self._current_file: Path = file

    def init_ui(self):
        # self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        # self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle(self.app_name)
        self.resize(1300, 900)
        # put the window Location center in screen
        self.center()

        self.setStyleSheet(open("./styles/style.qss", "r").read())
        
        self.window_font = QFont("FiraCode", 12)
        self.setFont(self.window_font)
        
        self.setUpBody()
        self.setMouseTracking(True)
        self.set_up_status_bar()

        self.show()

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def get_editor(self, path: Path = None, file_type=".py") -> QsciScintilla:
        """Create a New Editor"""
        venv = None
        if len(self.envs) > 0:
            venv = self.envs[0]
        editor = Editor(self, path=path, env=venv, file_type=file_type)
        return editor

    def set_cursor_pointer(self, e: QEnterEvent) -> None:
        self.setCursor(Qt.PointingHandCursor)

    def set_cursor_arrow(self, e) -> None:
        self.setCursor(Qt.ArrowCursor)

    def get_sidebar_button(self, img_path: str, widget) -> QLabel:
        label = QLabel()
        label.setStyleSheet("border: none; padding: 4px;")
        icon = QIcon(img_path)
        label.setPixmap(icon.pixmap(30, 30))
        label.setAlignment(Qt.AlignmentFlag.AlignTop)
        label.setFont(self.window_font)
        label.mousePressEvent = lambda e: self.show_hide_tab(e, widget)
        label.setMouseTracking(True)
        label.enterEvent = self.set_cursor_pointer
        label.leaveEvent = self.set_cursor_arrow
        return label

    def get_frame(self) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.NoFrame)
        frame.setFrameShadow(QFrame.Plain)
        frame.setContentsMargins(0, 0, 0, 0)
        frame.setStyleSheet(
        """
            QFrame {
                background-color: #21252b;
                border-radius: 5px;
                border: none;
                padding: 5px;
                color: #D3D3D3;
            }

            QFrame::hover {
                color: white;
            }
        """
        )

        return frame

    def create_label(self, text, style_sheet, alignment, font="Consolas", font_size=15, min_height=200):
        lbl = QLabel(text)
        lbl.setAlignment(alignment)
        lbl.setFont(QFont(font, font_size))
        lbl.setStyleSheet(style_sheet)
        lbl.setContentsMargins(0, 0, 0, 0)
        lbl.setMaximumHeight(min_height)
        return lbl

    def setUpBody(self):
        ###############################################
        ################ BODY ####################
        body_frame = QFrame()
        body_frame.setFrameShape(QFrame.NoFrame)
        body_frame.setFrameShadow(QFrame.Plain)
        body_frame.setLineWidth(0)
        body_frame.setMidLineWidth(0)
        body_frame.setContentsMargins(0, 0, 0, 0)
        body_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        ###############################################
        ################# HSPLIT ######################
        # horizontal split view
        self.hsplit = QSplitter(Qt.Horizontal)
    
        ###############################################
        ################ TAB VIEW ####################
        # Tab Widget to add editor to
        self.tab_view = QTabWidget()
        self.tab_view.setContentsMargins(0, 0, 0, 0)
        self.tab_view.setTabsClosable(True)
        self.tab_view.setMovable(True)
        self.tab_view.setDocumentMode(True)
        self.tab_view.tabCloseRequested.connect(self.close_tab)
        self.tab_view.setMouseTracking(True)
        self.tab_view.enterEvent = self.set_cursor_pointer
        self.tab_view.leaveEvent = self.set_cursor_arrow
        self.tab_view.currentChanged.connect(self.tab_changed)


        ###############################################
        ############## SideBar #######################
        self.side_bar = QFrame()
        self.side_bar.setFrameShape(QFrame.StyledPanel)
        self.side_bar.setFrameShadow(QFrame.Raised)
        self.side_bar.setContentsMargins(0, 0, 0, 0)
        self.side_bar.setMaximumWidth(50)
        self.side_bar.setStyleSheet(
            """
            background-color: #282c34;
        """
        )
        side_bar_content = QVBoxLayout()
        side_bar_content.setContentsMargins(5, 10, 5, 0)
        side_bar_content.setAlignment(Qt.AlignTop | Qt.AlignCenter)


        ###############################################
        ############ File Manager ###############

        # frame and layout to hold tree view
        self.file_manager_frame = self.get_frame()
        self.file_manager_frame.setMaximumWidth(400)
        self.file_manager_frame.setMinimumWidth(200)

        # layout for tree view
        
        self.file_manager_layout = QVBoxLayout() # was tree_view_layout
        self.file_manager_layout.setContentsMargins(0, 0, 0, 0)
        self.file_manager_layout.setSpacing(0)


        # setup layout
        # get current direcotory
        self.current_dir_lbl = QLabel(Path(os.getcwd()).name)
        self.current_dir_lbl.setStyleSheet("""
        font-size: 14px;
        background-color: #282c34;
        font-weight: bold;
        """)

        self.file_manager = FileManager(tab_view=self.tab_view,set_new_tab=self.set_new_tab, main_window=self) # was tree_view
        
        self.file_manager_layout.addWidget(self.current_dir_lbl)
        self.file_manager_layout.addWidget(self.file_manager)
        self.file_manager_frame.setLayout(self.file_manager_layout)

        ###############################################
        ############## Search View ####################

        # layout for search view
        self.search_frame = self.get_frame()
        self.search_frame.setMaximumWidth(400)
        self.search_frame.setMinimumWidth(200)
        search_layout = QVBoxLayout()
        search_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        search_layout.setContentsMargins(0, 10, 0, 0)
        search_layout.setSpacing(0)
        search_input = QLineEdit()
        search_input.setPlaceholderText("Search")
        search_input.setFont(self.window_font)
        search_input.setAlignment(Qt.AlignmentFlag.AlignTop)

        ############# CHECKBOX ################
        self.search_checkbox = QCheckBox("Search in modules")
        self.search_checkbox.setFont(self.window_font)
        self.search_checkbox.setStyleSheet("color: white; margin-bottom: 10px;")

        self.search_worker = SearchWorker()
        self.search_worker.finished.connect(self.search_finished)
        search_input.textChanged.connect(
            lambda text: self.search_worker.update(
                text,
                self.file_manager.model.rootDirectory().absolutePath(),
                self.search_checkbox.isChecked(),
            )
        )

        ###############################################
        ############## Search ListView ####################
        self.search_list_view = QListWidget()
        self.search_list_view.setFont(QFont("FiraCode", 13))

        self.search_list_view.itemClicked.connect(self.search_list_view_clicked)

        search_layout.addWidget(self.search_checkbox)
        search_layout.addWidget(search_input)
        search_layout.addSpacerItem(
            QSpacerItem(5, 5, QSizePolicy.Minimum, QSizePolicy.Minimum)
        )
        search_layout.addWidget(self.search_list_view)
        self.search_frame.setLayout(search_layout)

        ###############################################
        ############## Chat View ######################

        # layout for search view
        self.chat_frame = self.get_frame()
        self.chat_frame.setMaximumWidth(400)
        self.chat_frame.setMinimumWidth(200)
        chat_layout = QVBoxLayout()
        chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        chat_layout.setContentsMargins(0, 10, 0, 0)
        chat_layout.setSpacing(0)
        
        # Chat Input Field
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("chat")
        self.chat_input.setFont(self.window_font)
        self.chat_input.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chat_input.returnPressed.connect(self.process_chat_input)  # Connect to the processing function

        ################### CHECKBOX #####################
        # self.chat_checkbox = QCheckBox("Chat With Modules")
        # self.chat_checkbox.setFont(self.window_font)
        # self.chat_checkbox.setStyleSheet("color: white; margin-bottom: 10px;")

        ###################################################
        ############## Chat ListView #####################
        self.chat_list_view = QListWidget()
        self.chat_list_view.setFont(QFont("FiraCode", 13))

        # self.chat_list_view.itemClicked.connect(self.search_list_view_clicked)

        # chat_layout.addWidget(self.chat_checkbox)
        chat_layout.addWidget(self.chat_input)
        chat_layout.addSpacerItem(
            QSpacerItem(5, 5, QSizePolicy.Minimum, QSizePolicy.Minimum)
        )
        chat_layout.addWidget(self.chat_list_view)
        self.chat_frame.setLayout(chat_layout)
    
        ####################################################
        ############## SideBar Icons #######################
        folder_label = self.get_sidebar_button(
            "icons/folder_icon.svg", self.file_manager_frame
        )
        side_bar_content.addWidget(folder_label)
        search_label = self.get_sidebar_button("icons/search_icon.svg", self.search_frame)
        side_bar_content.addWidget(search_label)

        
        # chat_label = self.get_sidebar_button(":/icons/search_icon.svg", self.chat_frame)
        chat_label = self.get_sidebar_button("icons/chat_icon.svg", self.chat_frame)
        side_bar_content.addWidget(chat_label)

    
        self.side_bar.setLayout(side_bar_content)
        body.addWidget(self.side_bar)

        # Welcome Windwo - UPDATED EP 10
        self.welcome_frame = self.get_frame()
        self.welcome_frame.setStyleSheet(
        """
            QFrame {
                background-color: #21252b;
                border: none;
                color: #D3D3D3;
            }
            QFrame::hover {
                color: white;
            }
        """
        )

        welcome_layout = QVBoxLayout()
        welcome_layout.setContentsMargins(0, 0, 0, 0)
        welcome_layout.setSpacing(20)
        welcome_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)


        wlcm_title = self.create_label(
            "Welcome to Auditcode!",
            "color: #84878B;",
            Qt.AlignmentFlag.AlignHCenter,
            font_size=25,
            min_height=90,
        )
        wlcm_msg = self.create_label(
            "This is a simple code editor.\nYou can create new files or open existing ones.\n Muhammed Adnaan 4HG21CS026 Sinchana C V 4HG21CS045 \nK R Archana 4HG22CS403 Megha N N 4HG22CS406",
            "color: #84878B;",
            Qt.AlignmentFlag.AlignHCenter,
            font_size=15,
            min_height=100,
        )

        welcome_layout.addWidget(wlcm_title)
        welcome_layout.addWidget(wlcm_msg)
        self.welcome_frame.setLayout(welcome_layout)

        self.file_manager_frame.setStyleSheet(self.file_manager_frame.styleSheet() + "border: none;")
        self.welcome_frame.setStyleSheet(self.welcome_frame.styleSheet() + "border: none;")
        self.side_bar.setStyleSheet(self.side_bar.styleSheet() + "border: none; border-right: 1px solid #333641;")
        self.tab_view.setStyleSheet(self.tab_view.styleSheet() + "border: none;")
        self.hsplit.setStyleSheet(self.hsplit.styleSheet() + "border: none;")
        
        body_frame.setStyleSheet(body_frame.styleSheet() + "border: none;")


        # add file manager and tab view
        self.hsplit.addWidget(self.file_manager_frame)
        self.hsplit.addWidget(self.welcome_frame)
        self.current_side_bar = self.file_manager_frame

        # header
        self.header = Heading(self)
        self.header.setStyleSheet(self.header.styleSheet() + "border: none; border-bottom: 1px solid #333641; border-bottom-left-radius: 0; border-bottom-right-radius: 0;")
        
        # self.hsplit.addWidget(self.tab_view)

        # add hsplit and sidebar to body
        # body.addWidget(self.side_bar)
        body.addWidget(self.hsplit)

        # top and bottom stuff
        full_body = QVBoxLayout()
        full_body.setContentsMargins(0, 0, 0, 0)  
        full_body.setSpacing(0)
        full_body.addWidget(self.header)        
        full_body.addLayout(body)        

        body_frame.setLayout(full_body)
        # set central widget

        self.setCentralWidget(body_frame)
        self.frame_stlye = f"""
        QFrame {{
            background: #282c34;
            border-radius: 10px;
            border: 0.5px solid #3A3E49;
            border-bottom-left-radius: 0; 
            border-bottom-right-radius: 0;
        }}
        """
        self.frame_style_no_border = f"""
        QFrame {{
            background: #282c34;
            border-radius: 0px;
        }}
        """
        
        self.centralWidget().setStyleSheet(self.frame_stlye)

    def process_chat_input(self):
        """Handle the chat input and generate a response."""
        user_input = self.chat_input.text()
        if not user_input.strip():
            return

        # Clear input field
        self.chat_input.clear()

        # Display user input in the chat view
        self.chat_list_view.addItem(f"You: {user_input}")

        # Create a thread to handle the AI response generation
        thread = threading.Thread(target=self.handle_ai_response, args=(user_input,))
        thread.start()
    def handle_ai_response(self, user_input):
        """Fetch and display the AI response in a separate thread."""
        ai_response = self.generate_ai_response(user_input)
        # Update the chat list view with the AI response (must run on the main thread)
        self.chat_list_view.addItem(f"AI: {ai_response}")
        print(ai_response)

        ##code with conversation history
    def generate_ai_response(self, input_text, model="llama3.2", max_history_length=10):
        
        
        try:
            # Add user message to conversation history
            self.conversation_history.append({
                "role": "user",
                "content": input_text
            })

            # Trim conversation history if it exceeds max length
            if len(self.conversation_history) > max_history_length:
                # Remove oldest messages, keeping the most recent ones
                self.conversation_history = self.conversation_history[-max_history_length:]

            # Generate response using Ollama with conversation history
            response = ollama.chat(
                model=model,
                messages=self.conversation_history
            )
            
            # Extract AI response
            ai_response = response.get("message", {}).get("content", "Sorry, I couldn't process that.")
            
            # Add AI response to conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": ai_response
            })

            return ai_response

        except Exception as e:
            # Handle any errors
            return f"Error: {e}"

    def get_conversation_history(self):
        """
        Retrieve the current conversation history
        
        :return: List of conversation messages
        """
        return self.conversation_history

    def clear_conversation_history(self):
        """
        Clear the entire conversation history
        """
        self.conversation_history = []
###code acctuly running 
    # def generate_ai_response(self, input_text):
    #     """Generate a response using the Ollama library."""
    #     print(input_text)
    #     try:
    #         # Wrap the input text in a list of dictionaries
    #         messages = [
    #             {
    #                 "role": "user",
    #                 "content": input_text
    #             }
    #         ]
            
    #         response = ollama.chat(model="llama3.2", messages=messages)
    #         return response.get("message", {}).get("content", "Sorry, I couldn't process that.")
    #     except Exception as e:
    #         return f"Error: {e}"




    def search_finished(self, items):
        self.search_list_view.clear()
        for i in items:
            self.search_list_view.addItem(i)

    def search_list_view_clicked(self, item: SearchItem):
        self.set_new_tab(Path(item.full_path))
        editor: Editor = self.tab_view.currentWidget()
        editor.setCursorPosition(item.lineno, item.end)
        editor.setFocus()

    def show_hide_tab(self, e: QMouseEvent, widget: str):

        if self.current_side_bar == widget:
            if widget.isHidden():
                widget.show()
            else:
                widget.hide()

            return
       
        self.hsplit.replaceWidget(0, widget)
        self.current_side_bar = widget
        self.current_side_bar.show()


    def show_dialog(self, title, msg) -> int:
        dialog = QMessageBox(self)
        dialog.setFont(self.font())
        dialog.font().setPointSize(14)
        dialog.setWindowTitle(title)
        dialog.setWindowIcon(QIcon("./icons/close-icon.svg"))
        dialog.setText(msg)
        dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        dialog.setDefaultButton(QMessageBox.No)
        dialog.setIcon(QMessageBox.Warning)
        return dialog.exec_()

    def close_tab(self, index: int):
        # UPDATED EP 9
        editor: Editor = self.tab_view.currentWidget()
        if editor.current_file_changed:
            dialog = self.show_dialog(
                "Close", f"Do you want to save the changes made to {self.current_file.name}?"
            )
            if dialog == QMessageBox.Yes:
                self.save_file()

        self.tab_view.removeTab(index)

    def tab_changed(self, index: int):
        editor = self.tab_view.widget(index)
        if editor:
            self.current_file = editor.path

    # UPDATED EP 9 
    def set_up_status_bar(self):
        # Create a status bar
        stat = QStatusBar(self)
        # change message
        stat.setStyleSheet("color: #D3D3D3;")
        stat.showMessage("Ready", 3000)
        self.setStatusBar(stat)

    def is_binary(self, path):
        """
        Check if file is binary
        """
        with open(path, "rb") as f:
            return b"\0" in f.read(1024)

    def copy(self):
        t = self.tab_view.currentWidget()
        if t is not None:
            t.copy()

    def set_new_tab(self, path: Path, is_new_file=False):

        if not is_new_file and self.is_binary(path):
            self.statusBar().showMessage("Cannot Open Binary File", 2000)
            return
        
        if path.is_dir():
            return
        
        if self.welcome_frame:
            idx = self.hsplit.indexOf(self.welcome_frame)
            if idx != -1:
                self.hsplit.replaceWidget(idx, self.tab_view)

        text_edit = self.get_editor(path, path.suffix)
        
        if is_new_file:
            self.tab_view.addTab(text_edit, "untitled")
            self.setWindowTitle("untitled - " + self.app_name)
            self.statusBar().showMessage(f"Opened untitled", 2000)
            self.tab_view.setCurrentIndex(self.tab_view.count() - 1)
            self.current_file = None
            return

        # check if file is already open
        for i in range(self.tab_view.count()):

            if self.tab_view.tabText(i) == path.name or self.tab_view.tabText(i) == "*"+path.name: # check for unsaved state too
                # set the active tab to that
                self.tab_view.setCurrentIndex(i)
                self.current_file = path
                return

        self.tab_view.addTab(text_edit, path.name)
        text_edit.setText(path.read_text(encoding="utf-8"))
        self.setWindowTitle(f"{path.name} - {self.app_name}")
        self.statusBar().showMessage(f"Opened {path.name}", 2000)
        # set the active tab to that
        self.tab_view.setCurrentIndex(self.tab_view.count() - 1)
        self.current_file = path

    def new_file(self):
        # create new file
        self.set_new_tab(Path("untitled"), True)

    def save_file(self):

        if self.current_file is None and self.tab_view.count() > 0:
            self.save_as()
            return

        if self.current_file is None:
            return

        text_edit = self.tab_view.currentWidget()
        self.current_file.write_text(text_edit.text())
        self.statusBar().showMessage(f"Saved {self.current_file.name}", 2000)

        text_edit.current_file_changed = False

    def save_as(self):

        text_edit = self.tab_view.currentWidget()
        if text_edit is None:
            return
        file_path = QFileDialog.getSaveFileName(self, "Save As", os.getcwd())[0]
        if file_path == "":
            self.statusBar().showMessage("Cancelled", 2000)
            return
        path = Path(file_path)
        path.write_text(text_edit.text())
        # new
        self.current_file = path
        self.tab_view.setTabText(self.tab_view.currentIndex(), path.name)
        self.statusBar().showMessage(f"Saved {path.name}", 2000)

        # UPDATED EP 9
        editor: Editor = self.tab_view.currentWidget()
        editor.current_file_changed = False

    def open_file_dlg(self):
        new_file, _ = QFileDialog.getOpenFileName(
            self, "Pick A File", "", "All Files (*);;Python Files (*.py)"
        )

        if new_file:
            f = Path(new_file)
            self.set_new_tab(f)

    def open_folder(self):
        new_folder = QFileDialog.getExistingDirectory(
            self, "Pick A Folder", ""
        )
        if new_folder:
            self.file_manager.model.setRootPath(new_folder)
            self.file_manager.setRootIndex(self.file_manager.model.index(new_folder))
            self.statusBar().showMessage(f"Opened {new_folder}", 2000)
            self.current_dir_lbl.setText(Path(new_folder).name)

            self.tab_view.clear()
            idx = self.hsplit.indexOf(self.tab_view)
            if idx != -1:
                self.hsplit.replaceWidget(idx, self.welcome_frame)

    
if __name__ == "__main__":
    QApplication.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication([])
    app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)

    window = MainWindow()
    app.installEventFilter(window.header)


    sys.exit(app.exec_())