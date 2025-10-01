from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Tuple
import math
from PySide6 import QtCore, QtGui, QtWidgets


# -------------------------
# Enhanced data structures (SQLite-friendly)
# -------------------------

@dataclass
class MarkerNote:
    id: str  # unique identifier for database
    kind: str  # "arrow" | "pin" | "redact"
    number: Optional[int]  # only for pins
    pos_x: float  # position coordinates
    pos_y: float
    rotation_deg: float  # arrow/redact orientation; 0 for pins
    length: float  # arrow shaft length; 0 for pins and redacts
    width: float  # redact width; 0 for arrows and pins
    height: float  # redact height; 0 for arrows and pins
    text: str  # user's note text
    created_timestamp: str  # for database tracking


@dataclass
class ScreenshotMetadata:
    """Enhanced metadata for screenshots including title and description"""
    title: str = ""
    description: str = ""
    markers: List[dict] = None  # List of marker data

    def __post_init__(self):
        if self.markers is None:
            self.markers = []


# -------------------------
# Custom list widget item to hold marker data
# -------------------------

class MarkerListItem(QtWidgets.QListWidgetItem):
    def __init__(self, marker_id: str, display_text: str):
        super().__init__(display_text)
        self.marker_id = marker_id
        self.setFlags(self.flags() | QtCore.Qt.ItemIsSelectable)


# -------------------------
# Graphics items for markers
# -------------------------

class ArrowItem(QtWidgets.QGraphicsItem):
    """Tail-anchored arrow with unique ID for tracking"""

    def __init__(self, marker_id: str, angle_deg: float = 0.0, length: float = 0.0):
        super().__init__()
        self.marker_id = marker_id
        self.length = max(0.0, length)
        self._pen = QtGui.QPen(QtGui.QColor("#EF4444"))
        self._pen.setWidth(3)
        self._brush = QtGui.QBrush(QtGui.QColor("#EF4444"))
        self.setRotation(angle_deg)
        self.setTransformOriginPoint(QtCore.QPointF(0, 0))
        self.setFlags(
            QtWidgets.QGraphicsItem.ItemIsSelectable
            | QtWidgets.QGraphicsItem.ItemIsMovable
        )

    def set_length(self, L: float):
        self.length = max(0.0, float(L))
        self.prepareGeometryChange()

    def boundingRect(self) -> QtCore.QRectF:
        pad = 16
        L = max(self.length, 0.0) + pad
        return QtCore.QRectF(-pad, -pad, L + pad, 2 * pad)

    def paint(self, painter: QtGui.QPainter, option, widget=None):
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setPen(self._pen)
        painter.setBrush(self._brush)

        L = max(self.length, 0.0)
        if L < 6:
            painter.drawLine(QtCore.QPointF(0, 0), QtCore.QPointF(L, 0))
            return

        shaft_end = QtCore.QPointF(max(L - 14, 0), 0)
        painter.drawLine(QtCore.QPointF(0, 0), shaft_end)

        head_base = max(L - 14, 0)
        head = QtGui.QPolygonF([
            QtCore.QPointF(L, 0),
            QtCore.QPointF(head_base, -8),
            QtCore.QPointF(head_base, 8),
        ])
        painter.drawPolygon(head)


class PinItem(QtWidgets.QGraphicsEllipseItem):
    """Numbered circle pin with unique ID for tracking"""

    def __init__(self, marker_id: str, number: int, r: float = 14.0):
        super().__init__(-r, -r, 2 * r, 2 * r)
        self.marker_id = marker_id
        self.number = number
        self.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        self.setBrush(QtGui.QBrush(QtGui.QColor("#FDE68A")))
        self.setFlags(
            QtWidgets.QGraphicsItem.ItemIsSelectable
            | QtWidgets.QGraphicsItem.ItemIsMovable
        )

    def paint(self, painter: QtGui.QPainter, option, widget=None):
        super().paint(painter, option, widget)
        painter.setPen(QtGui.QPen(QtGui.QColor("#111827")))
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        text = str(self.number)
        rect = self.rect()
        painter.drawText(rect, QtCore.Qt.AlignCenter, text)


class RedactItem(QtWidgets.QGraphicsItem):
    """Black rectangle for redacting text with rotation handles"""

    def __init__(self, marker_id: str, width: float = 0.0, height: float = 0.0):
        super().__init__()
        self.marker_id = marker_id
        self.rect_width = max(0.0, width)
        self.rect_height = max(0.0, height)
        self._brush = QtGui.QBrush(QtGui.QColor("#000000"))
        self._pen = QtGui.QPen(QtGui.QColor("#FF0000"))
        self._pen.setWidth(2)
        self._pen.setStyle(QtCore.Qt.DashLine)

        # Handle properties
        self._handle_size = 8
        self._rotation_handle_distance = 30
        self._handles = []
        self._dragging_handle = None
        self._last_mouse_pos = QtCore.QPointF()
        self._initial_rotation = 0.0  # Track initial rotation for smooth rotation

        # Set transform origin to center for proper rotation
        self.setTransformOriginPoint(0, 0)  # Will be updated in set_size

        self.setFlags(
            QtWidgets.QGraphicsItem.ItemIsSelectable
            | QtWidgets.QGraphicsItem.ItemIsMovable
        )
        self.setAcceptHoverEvents(True)

    def set_size(self, width: float, height: float):
        self.rect_width = max(0.0, width)
        self.rect_height = max(0.0, height)
        # Set transform origin to center of rectangle
        self.setTransformOriginPoint(self.rect_width / 2, self.rect_height / 2)
        self.prepareGeometryChange()
        self._update_handles()

    def boundingRect(self) -> QtCore.QRectF:
        # Include space for handles and rotation handle
        pad = max(self._handle_size, self._rotation_handle_distance) + 10
        return QtCore.QRectF(-pad, -pad,
                             self.rect_width + 2 * pad,
                             self.rect_height + 2 * pad)

    def _update_handles(self):
        """Update handle positions based on current size"""
        w, h = self.rect_width, self.rect_height
        self._handles = [
            QtCore.QRectF(-self._handle_size / 2, -self._handle_size / 2,
                          self._handle_size, self._handle_size),  # Top-left
            QtCore.QRectF(w - self._handle_size / 2, -self._handle_size / 2,
                          self._handle_size, self._handle_size),  # Top-right
            QtCore.QRectF(w - self._handle_size / 2, h - self._handle_size / 2,
                          self._handle_size, self._handle_size),  # Bottom-right
            QtCore.QRectF(-self._handle_size / 2, h - self._handle_size / 2,
                          self._handle_size, self._handle_size),  # Bottom-left
        ]

        # Rotation handle (above center top)
        center_x = w / 2
        self._rotation_handle = QtCore.QRectF(
            center_x - self._handle_size / 2,
            -self._rotation_handle_distance - self._handle_size / 2,
            self._handle_size, self._handle_size
        )

    def hoverMoveEvent(self, event):
        """Update cursor when hovering over rotation handle"""
        if self.isSelected():
            pos = event.pos()
            if self._rotation_handle.contains(pos):
                self.setCursor(QtCore.Qt.OpenHandCursor)
            else:
                self.setCursor(QtCore.Qt.ArrowCursor)
        super().hoverMoveEvent(event)

    def paint(self, painter: QtGui.QPainter, option, widget=None):
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)

        # Draw the black redaction rectangle
        painter.setBrush(self._brush)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRect(0, 0, self.rect_width, self.rect_height)

        # Add redaction indicator - bright green "R" in center
        # Only show when not selected (to avoid cluttering with handles)
        if not self.isSelected() and self.rect_width > 16 and self.rect_height > 16:
            painter.setPen(QtGui.QPen(QtGui.QColor("#00FF00")))  # Bright green
            font = painter.font()
            font.setPointSize(max(10, min(int(min(self.rect_width, self.rect_height) / 3), 24)))
            font.setBold(True)
            painter.setFont(font)

            # Draw "R" centered
            text = "R"
            text_rect = painter.fontMetrics().boundingRect(text)
            center_x = self.rect_width / 2 - text_rect.width() / 2
            center_y = self.rect_height / 2 + text_rect.height() / 2 - 2
            painter.drawText(center_x, center_y, text)

        # If selected, draw selection outline and handles
        if self.isSelected():
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.setPen(self._pen)
            painter.drawRect(0, 0, self.rect_width, self.rect_height)

            self._update_handles()

            # Draw resize handles
            handle_brush = QtGui.QBrush(QtGui.QColor("#FFFFFF"))
            handle_pen = QtGui.QPen(QtGui.QColor("#FF0000"))
            painter.setBrush(handle_brush)
            painter.setPen(handle_pen)

            for handle_rect in self._handles:
                painter.drawRect(handle_rect)

            # Draw rotation handle
            rotation_brush = QtGui.QBrush(QtGui.QColor("#00FF00"))
            painter.setBrush(rotation_brush)
            painter.drawEllipse(self._rotation_handle)

            # Draw line from top center to rotation handle
            painter.setPen(QtGui.QPen(QtGui.QColor("#00FF00")))
            center_top = QtCore.QPointF(self.rect_width / 2, 0)
            rotation_center = self._rotation_handle.center()
            painter.drawLine(center_top, rotation_center)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self.isSelected():
            pos = event.pos()

            # Check if clicked on rotation handle
            if self._rotation_handle.contains(pos):
                self._dragging_handle = "rotation"
                self._initial_rotation = self.rotation()  # Store current rotation

                # Calculate initial angle from center to mouse
                item_center = QtCore.QPointF(self.rect_width / 2, self.rect_height / 2)
                scene_center = self.mapToScene(item_center)
                mouse_vector = event.scenePos() - scene_center
                self._initial_mouse_angle = math.degrees(math.atan2(mouse_vector.y(), mouse_vector.x()))

                self.setCursor(QtCore.Qt.ClosedHandCursor)
                event.accept()
                return

            # Check if clicked on resize handles
            for i, handle_rect in enumerate(self._handles):
                if handle_rect.contains(pos):
                    self._dragging_handle = f"resize_{i}"
                    self._last_mouse_pos = pos
                    event.accept()
                    return

        # Default behavior for moving the item
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging_handle == "rotation":
            # Calculate rotation based on mouse position relative to center
            item_center = QtCore.QPointF(self.rect_width / 2, self.rect_height / 2)
            scene_center = self.mapToScene(item_center)

            # Vector from center to current mouse position
            mouse_vector = event.scenePos() - scene_center
            current_mouse_angle = math.degrees(math.atan2(mouse_vector.y(), mouse_vector.x()))

            # Calculate the angle difference and add to initial rotation
            angle_delta = current_mouse_angle - self._initial_mouse_angle
            new_rotation = self._initial_rotation + angle_delta

            self.setRotation(new_rotation)
            event.accept()
            return

        elif self._dragging_handle and self._dragging_handle.startswith("resize_"):
            handle_index = int(self._dragging_handle.split("_")[1])
            delta = event.pos() - self._last_mouse_pos

            new_width = self.rect_width
            new_height = self.rect_height

            # Calculate position adjustment needed to maintain center position
            old_center = QtCore.QPointF(self.rect_width / 2, self.rect_height / 2)

            # Adjust size based on which handle is being dragged
            if handle_index == 0:  # Top-left
                new_width -= delta.x()
                new_height -= delta.y()
            elif handle_index == 1:  # Top-right
                new_width += delta.x()
                new_height -= delta.y()
            elif handle_index == 2:  # Bottom-right
                new_width += delta.x()
                new_height += delta.y()
            elif handle_index == 3:  # Bottom-left
                new_width -= delta.x()
                new_height += delta.y()

            # Enforce minimum size
            min_size = 10
            new_width = max(min_size, new_width)
            new_height = max(min_size, new_height)

            # Calculate new center and adjust position to maintain rotation around center
            new_center = QtCore.QPointF(new_width / 2, new_height / 2)
            center_delta = old_center - new_center

            self.set_size(new_width, new_height)
            self.moveBy(center_delta.x(), center_delta.y())
            self._last_mouse_pos = event.pos()
            event.accept()
            return

        # Default behavior
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._dragging_handle:
            if self._dragging_handle == "rotation":
                # Reset cursor after rotation
                pos = event.pos()
                if self._rotation_handle.contains(pos):
                    self.setCursor(QtCore.Qt.OpenHandCursor)
                else:
                    self.setCursor(QtCore.Qt.ArrowCursor)
            self._dragging_handle = None
            event.accept()
            return

        super().mouseReleaseEvent(event)


# -------------------------
# Enhanced annotation dialog with title/description and redaction tool
# -------------------------

class AnnotationDialog(QtWidgets.QDialog):
    """Enhanced dialog with title/description fields and marker annotations including redaction."""
    saved = QtCore.Signal(QtGui.QPixmap, dict)  # flattened pixmap + ScreenshotMetadata dict

    def __init__(self, base_pix: QtGui.QPixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Annotate Screenshot")
        self.resize(1100, 720)  # Made wider to accommodate title/description

        self._base_pix = base_pix
        self._pin_counter = 1
        self._mode = "pan"  # Start with pan mode instead of arrow
        self._marker_counter = 0

        # Core data: marker_id -> MarkerNote
        self._markers: dict[str, MarkerNote] = {}
        # UI mapping: marker_id -> graphics_item
        self._id_to_item: dict[str, QtWidgets.QGraphicsItem] = {}
        # UI mapping: graphics_item -> marker_id
        self._item_to_id: dict[QtWidgets.QGraphicsItem, str] = {}

        # Pin drag state
        self._dragging_new_pin = False
        self._new_pin_item = None

        # Redaction drag state
        self._drawing_redact = False
        self._redact_start_pos = QtCore.QPointF()

        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # --- left: canvas ---
        canvas_box = QtWidgets.QVBoxLayout()
        toolbar = QtWidgets.QHBoxLayout()
        self.btn_pan = QtWidgets.QPushButton("Pan")
        self.btn_arrow = QtWidgets.QPushButton("Arrow")
        self.btn_pin = QtWidgets.QPushButton("Pin")
        self.btn_redact = QtWidgets.QPushButton("Redact")
        self.redact_hint_label = QtWidgets.QLabel("Press Enter to finish")
        self.redact_hint_label.setStyleSheet("""
            color: #888888;
            font-style: italic;
            font-size: 11px;
        """)
        self.redact_hint_label.setVisible(False)

        # Custom styling to prevent system color override
        button_style = """
            QPushButton {
                background: #404040;
                color: #FFFFFF;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: normal;
            }
            QPushButton:hover {
                background: #505050;
                border-color: #666666;
            }
            QPushButton:checked {
                background: #0078D4;
                border-color: #0078D4;
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background: #303030;
            }
        """

        for b in (self.btn_pan, self.btn_arrow, self.btn_pin, self.btn_redact):
            b.setCheckable(True)
            b.setStyleSheet(button_style)

        self.btn_pan.setChecked(True)  # Start with pan mode
        toolbar.addWidget(self.btn_pan)
        toolbar.addWidget(self.btn_arrow)
        toolbar.addWidget(self.btn_pin)
        toolbar.addWidget(self.btn_redact)
        toolbar.addWidget(self.redact_hint_label)
        toolbar.addStretch(1)

        self.view = QtWidgets.QGraphicsView()
        self.view.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
        self.view.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)  # Start in pan mode

        self.scene = QtWidgets.QGraphicsScene(self)
        self.view.setScene(self.scene)

        self.bg_item = self.scene.addPixmap(self._base_pix)
        self.bg_item.setZValue(-10)

        canvas_box.addLayout(toolbar)
        canvas_box.addWidget(self.view)

        # --- right: enhanced metadata panel ---
        side = QtWidgets.QVBoxLayout()

        # Title and description section
        metadata_section = QtWidgets.QVBoxLayout()
        metadata_section.setSpacing(8)

        title_label = QtWidgets.QLabel("Screenshot Title")
        title_label.setStyleSheet("font-weight:600; font-size:14px;")
        self.title_edit = QtWidgets.QLineEdit()
        self.title_edit.setPlaceholderText("Brief title for this screenshot...")
        self._apply_input_style(self.title_edit)

        desc_label = QtWidgets.QLabel("Description")
        desc_label.setStyleSheet("font-weight:600; font-size:14px; margin-top:10px;")
        self.desc_edit = QtWidgets.QTextEdit()
        self.desc_edit.setPlaceholderText("Describe what this screenshot shows and its purpose...")
        self.desc_edit.setMaximumHeight(80)
        self._apply_input_style(self.desc_edit)

        metadata_section.addWidget(title_label)
        metadata_section.addWidget(self.title_edit)
        metadata_section.addWidget(desc_label)
        metadata_section.addWidget(self.desc_edit)

        side.addLayout(metadata_section)

        # Annotations section (removed separator)
        annotations_label = QtWidgets.QLabel("Annotations")
        annotations_label.setStyleSheet("font-weight:600; font-size:14px; margin-top:10px;")

        # List with delete button
        list_section = QtWidgets.QVBoxLayout()
        list_section.setSpacing(6)

        self.markers_list = QtWidgets.QListWidget()
        self.markers_list.setMaximumHeight(150)

        self.btn_delete_marker = QtWidgets.QPushButton("Delete Selected")

        list_section.addWidget(self.markers_list)
        list_section.addWidget(self.btn_delete_marker)

        note_label = QtWidgets.QLabel("Note for Selected Annotation:")
        note_label.setStyleSheet("font-weight:600; margin-top:10px;")

        self.note_edit = QtWidgets.QTextEdit()
        self.note_edit.setPlaceholderText("Select an annotation above to write a note about it...")

        self.btn_accept = QtWidgets.QPushButton("Save Screenshot")
        # Make it match the existing button styling in the dialog
        self.btn_accept.setStyleSheet("""
            QPushButton {
                background: #404040;
                color: #FFFFFF;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: normal;
            }
            QPushButton:hover { 
                background: #505050; 
                border-color: #666666; 
            }
            QPushButton:pressed {
                background: #303030;
            }
        """)

        side.addWidget(annotations_label)
        side.addLayout(list_section)
        side.addWidget(note_label)
        side.addWidget(self.note_edit, 1)
        side.addStretch(0)
        side.addWidget(self.btn_accept)

        root.addLayout(canvas_box, 3)
        root.addLayout(side, 2)

        # wiring
        self.btn_pan.clicked.connect(lambda: self._set_mode("pan"))
        self.btn_arrow.clicked.connect(lambda: self._set_mode("arrow"))
        self.btn_pin.clicked.connect(lambda: self._set_mode("pin"))
        self.btn_redact.clicked.connect(lambda: self._set_mode("redact"))
        self.view.viewport().installEventFilter(self)

        self.scene.selectionChanged.connect(self._on_graphics_selection_changed)
        self.markers_list.itemSelectionChanged.connect(self._on_list_selection_changed)
        self.note_edit.textChanged.connect(self._on_note_text_changed)
        self.btn_delete_marker.clicked.connect(self._delete_selected_marker)
        self.btn_accept.clicked.connect(self._accept_and_save)

        # Add key event handling
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == QtCore.Qt.Key_Return or event.key() == QtCore.Qt.Key_Enter:
            if self._mode == "redact":
                # Clear any selections to hide handles
                self.scene.clearSelection()
                # Exit redact mode and switch to pan mode (default)
                self._set_mode("pan")
                event.accept()
                return
        super().keyPressEvent(event)

    def _apply_input_style(self, widget: QtWidgets.QWidget):
        """Apply consistent input styling to match the rest of the dialog"""
        # Match the existing list widget and text edit styling
        style = """
            background: #2B2B2B;
            color: #FFFFFF;
            border: 1px solid #555555;
            border-radius: 4px;
            padding: 6px 8px;
            selection-background-color: #0078D4;
        """
        focus_style = "border: 1px solid #0078D4;"

        if isinstance(widget, QtWidgets.QLineEdit):
            widget.setStyleSheet(f"QLineEdit{{{style}}}QLineEdit:focus{{{focus_style}}}")
        elif isinstance(widget, QtWidgets.QTextEdit):
            widget.setStyleSheet(f"QTextEdit{{{style}}}QTextEdit:focus{{{focus_style}}}")

        # Set placeholder color to match theme
        pal = widget.palette()
        if hasattr(QtGui.QPalette, "PlaceholderText"):
            pal.setColor(QtGui.QPalette.PlaceholderText, QtGui.QColor("#888888"))
        widget.setPalette(pal)

    def _generate_marker_id(self) -> str:
        """Generate unique marker ID for database"""
        self._marker_counter += 1
        return f"marker_{self._marker_counter}_{QtCore.QDateTime.currentMSecsSinceEpoch()}"

    def _set_mode(self, mode: str):
        self._mode = mode
        self.btn_pan.setChecked(mode == "pan")
        self.btn_arrow.setChecked(mode == "arrow")
        self.btn_pin.setChecked(mode == "pin")
        self.btn_redact.setChecked(mode == "redact")

        # Show/hide redact hint
        self.redact_hint_label.setVisible(mode == "redact")

        # Update view drag mode and cursor based on mode
        if mode == "pan":
            self.view.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
            self.view.setCursor(QtCore.Qt.OpenHandCursor)
        elif mode == "redact":
            self.view.setDragMode(QtWidgets.QGraphicsView.NoDrag)
            self.view.setCursor(QtCore.Qt.CrossCursor)
        else:  # arrow or pin mode
            self.view.setDragMode(QtWidgets.QGraphicsView.NoDrag)
            self.view.setCursor(QtCore.Qt.ArrowCursor)

    def eventFilter(self, obj, ev):
        if obj is self.view.viewport():
            # In pan mode, let the default drag behavior handle panning
            if self._mode == "pan":
                return False

            if ev.type() == QtCore.QEvent.MouseButtonPress and ev.button() == QtCore.Qt.LeftButton:
                pos = self.view.mapToScene(ev.position().toPoint())

                # Check if we clicked on an existing item first
                item_at_pos = self.scene.itemAt(pos, self.view.transform())
                if item_at_pos and item_at_pos != self.bg_item:
                    return False

                if self._mode == "arrow":
                    marker_id = self._generate_marker_id()
                    item = ArrowItem(marker_id, angle_deg=0.0, length=0.0)
                    item.setPos(pos)
                    self.scene.addItem(item)
                    self._drawing_arrow = item
                    self._arrow_tail = pos

                elif self._mode == "pin":
                    marker_id = self._generate_marker_id()
                    item = PinItem(marker_id, self._pin_counter)
                    self._pin_counter += 1
                    item.setPos(pos)
                    self.scene.addItem(item)

                    self._dragging_new_pin = True
                    self._new_pin_item = item
                    self.scene.clearSelection()
                    item.setSelected(True)

                    self._create_marker_entry(item, "pin")

                elif self._mode == "redact":
                    marker_id = self._generate_marker_id()
                    item = RedactItem(marker_id, width=0.0, height=0.0)
                    item.setPos(pos)
                    self.scene.addItem(item)

                    self._drawing_redact = True
                    self._redact_start_pos = pos
                    self._drawing_redact_item = item

                return True

            if ev.type() == QtCore.QEvent.MouseMove:
                # In pan mode, let default behavior handle the panning
                if self._mode == "pan":
                    return False

                if hasattr(self, "_drawing_arrow"):
                    scene_pos = self.view.mapToScene(ev.position().toPoint())
                    v = scene_pos - self._arrow_tail
                    length = (v.x() ** 2 + v.y() ** 2) ** 0.5
                    min_len = 12.0
                    self._drawing_arrow.set_length(max(length, min_len))
                    angle = math.degrees(math.atan2(v.y(), v.x()))
                    self._drawing_arrow.setRotation(angle)
                    return True

                if self._dragging_new_pin and self._new_pin_item:
                    scene_pos = self.view.mapToScene(ev.position().toPoint())
                    self._new_pin_item.setPos(scene_pos)
                    return True

                if self._drawing_redact and hasattr(self, "_drawing_redact_item"):
                    scene_pos = self.view.mapToScene(ev.position().toPoint())
                    # Calculate rectangle dimensions
                    rect = QtCore.QRectF(self._redact_start_pos, scene_pos).normalized()
                    width = rect.width()
                    height = rect.height()

                    # Update the redaction item
                    self._drawing_redact_item.setPos(rect.topLeft())
                    self._drawing_redact_item.set_size(width, height)
                    return True

            if ev.type() == QtCore.QEvent.MouseButtonRelease and ev.button() == QtCore.Qt.LeftButton:
                if hasattr(self, "_drawing_arrow"):
                    self._create_marker_entry(self._drawing_arrow, "arrow")
                    del self._drawing_arrow
                    del self._arrow_tail
                    return True

                if self._dragging_new_pin:
                    self._dragging_new_pin = False
                    self._new_pin_item = None
                    return True

                if self._drawing_redact and hasattr(self, "_drawing_redact_item"):
                    # Only create the marker if the rectangle has a meaningful size
                    if (self._drawing_redact_item.rect_width > 5 and
                        self._drawing_redact_item.rect_height > 5):
                        self._create_marker_entry(self._drawing_redact_item, "redact")
                    else:
                        # Remove the item if it's too small
                        self.scene.removeItem(self._drawing_redact_item)

                    self._drawing_redact = False
                    del self._drawing_redact_item
                    return True

        return super().eventFilter(obj, ev)

    def _create_marker_entry(self, graphics_item, kind: str):
        """Create marker data and list entry, then select it"""
        marker_id = graphics_item.marker_id

        marker = MarkerNote(
            id=marker_id,
            kind=kind,
            number=getattr(graphics_item, 'number', None),
            pos_x=graphics_item.pos().x(),
            pos_y=graphics_item.pos().y(),
            rotation_deg=graphics_item.rotation() if kind in ["arrow", "redact"] else 0.0,
            length=getattr(graphics_item, "length", 0.0) if kind == "arrow" else 0.0,
            width=getattr(graphics_item, "rect_width", 0.0) if kind == "redact" else 0.0,
            height=getattr(graphics_item, "rect_height", 0.0) if kind == "redact" else 0.0,
            text="",
            created_timestamp=QtCore.QDateTime.currentDateTime().toString(QtCore.Qt.ISODate)
        )

        self._markers[marker_id] = marker
        self._id_to_item[marker_id] = graphics_item
        self._item_to_id[graphics_item] = marker_id

        if kind == "pin":
            display_text = f"Pin {marker.number}"
        elif kind == "arrow":
            display_text = "Arrow"
        else:  # redact
            display_text = "Redaction"

        list_item = MarkerListItem(marker_id, display_text)
        self.markers_list.addItem(list_item)

        self.scene.clearSelection()
        graphics_item.setSelected(True)
        self.markers_list.setCurrentItem(list_item)

    def _on_graphics_selection_changed(self):
        """Handle selection changes in graphics view"""
        selected_items = self.scene.selectedItems()
        if not selected_items:
            return

        graphics_item = selected_items[0]
        marker_id = self._item_to_id.get(graphics_item)
        if not marker_id:
            return

        for i in range(self.markers_list.count()):
            list_item = self.markers_list.item(i)
            if isinstance(list_item, MarkerListItem) and list_item.marker_id == marker_id:
                self.markers_list.blockSignals(True)
                self.markers_list.setCurrentItem(list_item)
                self.markers_list.blockSignals(False)
                break

        self._load_note_for_marker(marker_id)

    def _on_list_selection_changed(self):
        """Handle selection changes in markers list"""
        current_item = self.markers_list.currentItem()

        if not isinstance(current_item, MarkerListItem):
            return

        marker_id = current_item.marker_id
        graphics_item = self._id_to_item.get(marker_id)
        if not graphics_item:
            return

        self.scene.blockSignals(True)
        self.scene.clearSelection()
        graphics_item.setSelected(True)
        self.scene.blockSignals(False)

        self._load_note_for_marker(marker_id)

    def _load_note_for_marker(self, marker_id: str):
        """Load the note text for the specified marker"""
        marker = self._markers.get(marker_id)
        if marker:
            self.note_edit.blockSignals(True)
            self.note_edit.setText(marker.text)
            self.note_edit.blockSignals(False)

    def _on_note_text_changed(self):
        """Save note text to currently selected marker"""
        current_item = self.markers_list.currentItem()
        if not isinstance(current_item, MarkerListItem):
            return

        marker_id = current_item.marker_id
        marker = self._markers.get(marker_id)
        if marker:
            marker.text = self.note_edit.toPlainText()

    def _delete_selected_marker(self):
        """Delete the currently selected marker from both graphics and list"""
        current_item = self.markers_list.currentItem()

        if not isinstance(current_item, MarkerListItem):
            QtWidgets.QMessageBox.information(
                self,
                "No Selection",
                "Please select an annotation from the list to delete."
            )
            return

        marker = self._markers.get(current_item.marker_id)
        if marker:
            if marker.kind == "pin":
                marker_type = f"Pin {marker.number}"
            elif marker.kind == "arrow":
                marker_type = "Arrow"
            else:  # redact
                marker_type = "Redaction"
        else:
            marker_type = "annotation"

        reply = QtWidgets.QMessageBox.question(
            self,
            "Delete Annotation",
            f"Are you sure you want to delete this {marker_type}?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if reply != QtWidgets.QMessageBox.Yes:
            return

        marker_id = current_item.marker_id
        deleted_row = self.markers_list.row(current_item)

        graphics_item = self._id_to_item.get(marker_id)
        if graphics_item:
            self.scene.removeItem(graphics_item)

        self._markers.pop(marker_id, None)
        self._id_to_item.pop(marker_id, None)
        if graphics_item:
            self._item_to_id.pop(graphics_item, None)

        self.markers_list.takeItem(deleted_row)
        self.scene.clearSelection()

        remaining_count = self.markers_list.count()
        if remaining_count > 0:
            new_selection_row = min(deleted_row, remaining_count - 1)
            new_item = self.markers_list.item(new_selection_row)
            if new_item and isinstance(new_item, MarkerListItem):
                self.markers_list.setCurrentItem(new_item)
                self._load_note_for_marker(new_item.marker_id)

                graphics_item = self._id_to_item.get(new_item.marker_id)
                if graphics_item:
                    graphics_item.setSelected(True)
        else:
            self.note_edit.clear()
            self.scene.clearSelection()

    def _update_marker_positions(self):
        """Update stored positions when items are moved"""
        for marker_id, graphics_item in self._id_to_item.items():
            marker = self._markers.get(marker_id)
            if marker:
                marker.pos_x = graphics_item.pos().x()
                marker.pos_y = graphics_item.pos().y()
                if hasattr(graphics_item, 'rotation'):
                    marker.rotation_deg = graphics_item.rotation()
                if hasattr(graphics_item, 'length'):
                    marker.length = getattr(graphics_item, 'length', 0.0)
                if hasattr(graphics_item, 'rect_width'):
                    marker.width = getattr(graphics_item, 'rect_width', 0.0)
                if hasattr(graphics_item, 'rect_height'):
                    marker.height = getattr(graphics_item, 'rect_height', 0.0)

    def _accept_and_save(self):
        """Save final image with annotations and return structured data"""
        self._update_marker_positions()

        # Create final image
        w, h = self._base_pix.width(), self._base_pix.height()
        out = QtGui.QPixmap(w, h)
        out.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(out)
        painter.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform, True)
        painter.drawPixmap(0, 0, self._base_pix)

        # Render each marker
        for marker_id, marker in self._markers.items():
            graphics_item = self._id_to_item.get(marker_id)
            if not graphics_item:
                continue

            painter.save()
            painter.translate(marker.pos_x, marker.pos_y)

            if marker.kind == "arrow":
                painter.rotate(marker.rotation_deg)
                pen = QtGui.QPen(QtGui.QColor("#EF4444"))
                pen.setWidth(3)
                painter.setPen(pen)
                painter.setBrush(QtGui.QBrush(QtGui.QColor("#EF4444")))

                L = max(float(marker.length), 0.0)
                shaft_end_x = max(L - 14, 0.0)
                painter.drawLine(QtCore.QPointF(0, 0), QtCore.QPointF(shaft_end_x, 0))

                head = QtGui.QPolygonF([
                    QtCore.QPointF(L, 0),
                    QtCore.QPointF(shaft_end_x, -8),
                    QtCore.QPointF(shaft_end_x, 8),
                ])
                painter.drawPolygon(head)

            elif marker.kind == "pin":
                r = 14.0
                painter.setBrush(QtGui.QBrush(QtGui.QColor("#FDE68A")))
                painter.setPen(QtCore.Qt.NoPen)
                painter.drawEllipse(QtCore.QRectF(-r, -r, 2 * r, 2 * r))

                painter.setPen(QtGui.QPen(QtGui.QColor("#111827")))
                font = painter.font()
                font.setBold(True)
                painter.setFont(font)
                rect = QtCore.QRectF(-r, -r, 2 * r, 2 * r)
                painter.drawText(rect, QtCore.Qt.AlignCenter, str(marker.number))

            elif marker.kind == "redact":
                painter.rotate(marker.rotation_deg)
                painter.setBrush(QtGui.QBrush(QtGui.QColor("#000000")))
                painter.setPen(QtCore.Qt.NoPen)
                painter.drawRect(0, 0, marker.width, marker.height)

                # Add bright green "R" indicator in center
                if marker.width > 16 and marker.height > 16:
                    painter.setPen(QtGui.QPen(QtGui.QColor("#00FF00")))  # Bright green
                    font = painter.font()
                    font.setPointSize(max(10, min(int(min(marker.width, marker.height) / 3), 24)))
                    font.setBold(True)
                    painter.setFont(font)

                    text = "R"
                    text_rect = painter.fontMetrics().boundingRect(text)
                    center_x = marker.width / 2 - text_rect.width() / 2
                    center_y = marker.height / 2 + text_rect.height() / 2 - 2
                    painter.drawText(center_x, center_y, text)

            painter.restore()

        painter.end()

        # Create enhanced metadata structure
        metadata = ScreenshotMetadata(
            title=self.title_edit.text().strip(),
            description=self.desc_edit.toPlainText().strip(),
            markers=[asdict(marker) for marker in self._markers.values()]
        )

        self.saved.emit(out, asdict(metadata))
        self.accept()


# -------------------------
# Enhanced screenshot overlay with semi-transparent background
# -------------------------

class ScreenshotOverlay(QtWidgets.QWidget):
    """Full-screen overlay to select a region with semi-transparent background."""
    regionSelected = QtCore.Signal(QtGui.QPixmap, QtCore.QRect)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint, True)
        self.setWindowState(QtCore.Qt.WindowFullScreen)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setCursor(QtCore.Qt.CrossCursor)

        app = QtWidgets.QApplication.instance()

        # Capture all screens instead of just primary
        screens = app.screens()
        if len(screens) > 1:
            # Multi-monitor setup - capture virtual desktop
            virtual_geometry = QtCore.QRect()
            for screen in screens:
                virtual_geometry = virtual_geometry.united(screen.geometry())

            # Create a pixmap that covers all screens
            total_width = virtual_geometry.width()
            total_height = virtual_geometry.height()
            self._full_pix = QtGui.QPixmap(total_width, total_height)
            self._full_pix.fill(QtCore.Qt.black)

            painter = QtGui.QPainter(self._full_pix)
            for screen in screens:
                screen_geometry = screen.geometry()
                screen_pixmap = screen.grabWindow(0)
                # Calculate offset from virtual desktop origin
                offset_x = screen_geometry.x() - virtual_geometry.x()
                offset_y = screen_geometry.y() - virtual_geometry.y()
                painter.drawPixmap(offset_x, offset_y, screen_pixmap)
            painter.end()

            # Position the overlay to cover the virtual desktop
            self.setGeometry(virtual_geometry)
        else:
            # Single monitor - use original approach
            desktop = app.primaryScreen()
            self._full_pix = desktop.grabWindow(0)

        self._dragging = False
        self._origin = QtCore.QPoint()
        self._current = QtCore.QPoint()
        self._rubber = QtCore.QRect()

        self._dpr = self._full_pix.devicePixelRatio()

    def paintEvent(self, e: QtGui.QPaintEvent) -> None:
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)

        # Draw the full screenshot first
        p.drawPixmap(0, 0, self._full_pix)

        # Then apply semi-transparent overlay everywhere
        overlay_color = QtGui.QColor(0, 0, 0, 153)  # 60% opacity
        p.fillRect(self.rect(), overlay_color)

        if not self._rubber.isNull():
            # Clear the overlay in the selection area by drawing the original image again
            p.setCompositionMode(QtGui.QPainter.CompositionMode_SourceOver)
            p.drawPixmap(self._rubber.topLeft(), self._full_pix.copy(self._rubber))

            # Selection border
            pen = QtGui.QPen(QtGui.QColor("#60A5FA"))
            pen.setWidth(3)
            pen.setStyle(QtCore.Qt.DashLine)
            p.setPen(pen)
            p.setBrush(QtCore.Qt.NoBrush)
            p.drawRect(self._rubber)

    def mousePressEvent(self, e: QtGui.QMouseEvent) -> None:
        if e.button() == QtCore.Qt.LeftButton:
            self._dragging = True
            self._origin = e.position().toPoint()
            self._current = self._origin
            self._rubber = QtCore.QRect(self._origin, self._current)
            self.update()
        elif e.button() == QtCore.Qt.RightButton:
            self.close()

    def mouseMoveEvent(self, e: QtGui.QMouseEvent) -> None:
        if self._dragging:
            self._current = e.position().toPoint()
            self._rubber = QtCore.QRect(self._origin, self._current).normalized()
            self.update()

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent) -> None:
        if e.button() == QtCore.Qt.LeftButton and self._dragging:
            self._dragging = False
            if self._rubber.isNull() or self._rubber.width() < 5 or self._rubber.height() < 5:
                self.close()
                return
            cropped = self._full_pix.copy(self._rubber)
            self.regionSelected.emit(cropped, self._rubber)
            self.close()


# -------------------------
# Enhanced screenshot tool
# -------------------------

class ScreenshotTool(QtCore.QObject):
    """Enhanced screenshot tool with title/description support and redaction."""
    screenshotSaved = QtCore.Signal(str, dict)  # file_path, metadata dict

    def __init__(self, parent=None, save_dir: Optional[Path] = None):
        super().__init__(parent)
        self._save_dir = save_dir or self._default_save_dir()
        self._save_dir.mkdir(parents=True, exist_ok=True)

    def _default_save_dir(self) -> Path:
        base = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.AppDataLocation)
        root = Path(base or Path.home() / ".discovery_assistant")
        return root / "screenshots"

    def start(self):
        self._overlay = ScreenshotOverlay()
        self._overlay.regionSelected.connect(self._on_region_selected)
        self._overlay.show()

    def _on_region_selected(self, pix: QtGui.QPixmap, rect: QtCore.QRect):
        dlg = AnnotationDialog(pix)
        dlg.saved.connect(self._save_final)
        dlg.exec()

    def _save_final(self, pix: QtGui.QPixmap, metadata: dict):
        filename = f"snap_{QtCore.QDateTime.currentDateTime().toString('yyyyMMdd_hhmmss_zzz')}.png"
        out_path = self._save_dir / filename
        pix.save(str(out_path), "PNG")
        self.screenshotSaved.emit(str(out_path), metadata)
