from PySide6.QtWidgets import QCheckBox
from PySide6.QtCore import Qt


class StyledCheckBox(QCheckBox):
    def __init__(
        self,
        text="",
        bg_color="#1A415E",
        bg_color_checked="#0BE5F5",
        border_color="#000000",
        border_color_checked="#FFFFFF",
        checkmark_color="#FFFFFF",
        text_color="#F9FAFB",
        text_size=14,
        indicator_size=18,
        parent=None
    ):
        super().__init__(text, parent)

        self.bg_color = bg_color
        self.bg_color_checked = bg_color_checked
        self.border_color = border_color
        self.border_color_checked = border_color_checked
        self.checkmark_color = checkmark_color
        self.text_color = text_color
        self.text_size = text_size
        self.indicator_size = indicator_size

        self._apply_stylesheet()

    def _apply_stylesheet(self):
        stylesheet = f"""
            QCheckBox {{
                color: {self.text_color};
                font-size: {self.text_size}px;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: {self.indicator_size}px;
                height: {self.indicator_size}px;
                background-color: {self.bg_color};
                border: 1px solid {self.border_color};
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.bg_color_checked};
                border: 1px solid {self.border_color_checked};
                image: url(:/checkmark.svg);
            }}
        """
        self.setStyleSheet(stylesheet)
