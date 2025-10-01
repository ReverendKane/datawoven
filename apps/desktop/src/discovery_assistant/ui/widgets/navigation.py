from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import Signal, Slot
import logging

_LOGGER = logging.getLogger('Discovery.navigation')


# navigation.py  (only showing the class; keep your imports)
class Navigation(QtWidgets.QWidget):
    tabSelected = QtCore.Signal(str)

    def __init__(self, sections: dict[str, str], parent=None):
        super().__init__(parent)
        self.sections = sections

        self.setObjectName("NavBar")
        # Light gray gutter + no heavy frame
        self.setStyleSheet("""
            #NavBar { background: #F1F5F9; }                  /* light gray gutter */
            QScrollArea { background: transparent; border: none; }
            QWidget#NavHost { background: #F1F5F9; }          /* keep host matching gutter */
        """)

        # Keep the whole bar compact
        self.setMinimumHeight(34)
        self.setMaximumHeight(45)

        scroll = QtWidgets.QScrollArea(self)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll.setWidgetResizable(True)

        host = QtWidgets.QWidget()
        host.setObjectName("NavHost")
        self._layout = QtWidgets.QHBoxLayout(host)
        self._layout.setContentsMargins(10, 6, 10, 6)   # tighter vertical padding
        self._layout.setSpacing(8)

        self.buttons: dict[str, QtWidgets.QPushButton] = {}
        for name in sections.keys():
            btn = QtWidgets.QPushButton(name, host)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, n=name: self._on_clicked(n))
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.setMinimumHeight(25)                  # shorter pills
            btn.setStyleSheet("""
              QPushButton {
                background: #FFFFFF;
                color: #0F172A;
                border: 1px solid #E5E7EB;
                padding: 4px 10px;
                border-radius: 4px;
                outline: none;                          /* Remove outline */
              }
              QPushButton:hover { 
                background: #F8FAFC; 
                outline: none;                          /* Remove outline on hover */
              }
              QPushButton:checked {
                background: #0F172A;
                color: #FFFFFF;
                border-color: #0F172A;
                outline: none;                          /* Remove outline when selected */
              }
              QPushButton:focus {
                outline: none;                          /* Remove focus outline */
                border: 1px solid #E5E7EB;             /* Keep original border */
              }
              QPushButton:focus:checked {
                outline: none;                          /* Remove outline on focused + selected */
                border-color: #0F172A;                 /* Keep selected border color */
              }
            """)
            self._layout.addWidget(btn)
            self.buttons[name] = btn

        self._layout.addStretch(1)
        scroll.setWidget(host)

        outer = QtWidgets.QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)          # nav gutter hugs container
        outer.addWidget(scroll)

    def _on_clicked(self, name: str):
        for k, b in self.buttons.items():
            b.setChecked(k == name)
        self.tabSelected.emit(name)

    def select_first(self):
        if self.buttons:
            first = next(iter(self.buttons))
            self.buttons[first].setChecked(True)
            self.tabSelected.emit(first)
