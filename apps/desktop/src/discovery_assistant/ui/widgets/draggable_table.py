from typing import Optional, List, Any, Callable
from PySide6 import QtWidgets, QtCore, QtGui


class DraggableTableWidget(QtWidgets.QTableWidget):
    """
    Reusable QTableWidget with drag-and-drop row reordering capability.

    Usage:
        table = DraggableTableWidget(0, 4)
        table.rowsReordered.connect(self._handle_reorder)

        def _handle_reorder(old_index, new_index):
            # Update your data model
            item = self._items.pop(old_index)
            self._items.insert(new_index, item)
            # Refresh table display
            self._repopulate_table()
    """

    rowsReordered = QtCore.Signal(int, int)  # old_index, new_index

    def __init__(self, rows=0, columns=0, parent=None):
        super().__init__(rows, columns, parent)

        # Configure for row-level selection and disable Qt's drag-drop
        self.setDragDropMode(QtWidgets.QAbstractItemView.NoDragDrop)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        # Manual drag-drop state
        self._drag_start_pos = None
        self._dragging = False
        self._drag_row = -1

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        """Start drag operation"""
        if event.button() == QtCore.Qt.LeftButton:
            self._drag_start_pos = event.pos()
            row = self.indexAt(event.pos()).row()
            if row >= 0:
                self.selectRow(row)
                self._drag_row = row
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        """Handle drag movement"""
        if (event.buttons() & QtCore.Qt.LeftButton) and self._drag_start_pos:
            # Check if we've moved far enough to start dragging
            if not self._dragging:
                manhattan_length = (event.pos() - self._drag_start_pos).manhattanLength()
                if manhattan_length >= QtWidgets.QApplication.startDragDistance():
                    self._dragging = True
                    self.setCursor(QtCore.Qt.ClosedHandCursor)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        """Complete drag operation"""
        if self._dragging and event.button() == QtCore.Qt.LeftButton:
            drop_pos = event.pos()
            drop_row = self.indexAt(drop_pos).row()

            # If dropping outside table bounds, drop at end
            if drop_row == -1:
                drop_row = self.rowCount()

            # Perform the reorder if valid
            if (self._drag_row >= 0 and drop_row >= 0 and
                self._drag_row != drop_row):

                # Adjust destination for the fact that we're moving a row
                if drop_row > self._drag_row:
                    drop_row -= 1

                self.rowsReordered.emit(self._drag_row, drop_row)

        # Reset drag state
        self._dragging = False
        self._drag_start_pos = None
        self._drag_row = -1
        self.setCursor(QtCore.Qt.ArrowCursor)

        super().mouseReleaseEvent(event)


class DraggableTableMixin:
    """
    Mixin class to add drag-and-drop functionality to any tab class.

    Usage:
        class MyTab(QtWidgets.QWidget, DraggableTableMixin):
            def __init__(self):
                super().__init__()
                # ... create your table ...
                self._setup_draggable_table(self.table, self._items, self._repopulate_rows)

    Requirements:
        - Your tab class must have a table widget
        - Your tab class must have a data list (e.g., self._items)
        - Your tab class must have a repopulate method
    """

    def _setup_draggable_table(self,
                               table_widget: QtWidgets.QTableWidget,
                               items_list: List[Any],
                               repopulate_callback: Callable[[], None]):
        """
        Convert an existing table widget to use drag-and-drop reordering.

        Args:
            table_widget: The QTableWidget to make draggable
            items_list: Reference to the data list that backs the table
            repopulate_callback: Function to call to refresh the table after reordering
        """
        # Store references
        table_widget._items_list = items_list
        table_widget._repopulate_callback = repopulate_callback

        # Replace the existing table with a draggable version
        if not isinstance(table_widget, DraggableTableWidget):
            # Create new draggable table
            new_table = DraggableTableWidget(table_widget.rowCount(), table_widget.columnCount())

            # Copy all properties from old table
            self._copy_table_properties(table_widget, new_table)

            # Connect reorder signal
            new_table.rowsReordered.connect(
                lambda old_idx, new_idx: self._handle_table_reorder(
                    old_idx, new_idx, items_list, repopulate_callback, new_table
                )
            )

            # Replace in layout
            layout = table_widget.parent().layout()
            if layout:
                layout.replaceWidget(table_widget, new_table)
                table_widget.deleteLater()

            return new_table

        return table_widget

    def _copy_table_properties(self, old_table: QtWidgets.QTableWidget, new_table: DraggableTableWidget):
        """Copy properties from old table to new draggable table"""
        # Copy headers
        for col in range(old_table.columnCount()):
            header_item = old_table.horizontalHeaderItem(col)
            if header_item:
                new_table.setHorizontalHeaderItem(col, QtWidgets.QTableWidgetItem(header_item.text()))

        # Copy basic properties
        new_table.setObjectName(old_table.objectName())
        new_table.setStyleSheet(old_table.styleSheet())
        new_table.setSizePolicy(old_table.sizePolicy())
        new_table.setMinimumSize(old_table.minimumSize())
        new_table.setMaximumSize(old_table.maximumSize())

        # Copy table-specific properties
        new_table.setAlternatingRowColors(old_table.alternatingRowColors())
        new_table.setShowGrid(old_table.showGrid())
        new_table.setVerticalScrollBarPolicy(old_table.verticalScrollBarPolicy())
        new_table.setHorizontalScrollBarPolicy(old_table.horizontalScrollBarPolicy())

        # Copy header properties
        old_hdr = old_table.horizontalHeader()
        new_hdr = new_table.horizontalHeader()

        for col in range(old_table.columnCount()):
            new_hdr.setSectionResizeMode(col, old_hdr.sectionResizeMode(col))
            new_table.setColumnWidth(col, old_table.columnWidth(col))

        new_hdr.setStretchLastSection(old_hdr.stretchLastSection())
        new_hdr.setDefaultAlignment(old_hdr.defaultAlignment())
        new_hdr.setHighlightSections(old_hdr.highlightSections())

        # Copy vertical header
        new_table.verticalHeader().setVisible(old_table.verticalHeader().isVisible())

        # Copy palette
        new_table.setPalette(old_table.palette())

    def _handle_table_reorder(self,
                              old_index: int,
                              new_index: int,
                              items_list: List[Any],
                              repopulate_callback: Callable[[], None],
                              table_widget: DraggableTableWidget):
        """Handle row reordering"""
        # Reorder the items list
        item = items_list.pop(old_index)
        items_list.insert(new_index, item)

        # Repopulate table
        repopulate_callback()

        # Select the moved row
        table_widget.selectRow(new_index)


# Utility function for quick setup
def make_table_draggable(table_widget: QtWidgets.QTableWidget,
                         items_list: List[Any],
                         repopulate_callback: Callable[[], None]) -> DraggableTableWidget:
    """
    Standalone function to convert any QTableWidget to draggable.

    Args:
        table_widget: The table to make draggable
        items_list: The data list backing the table
        repopulate_callback: Function to refresh table after reorder

    Returns:
        The new DraggableTableWidget instance
    """
    # Create mixin instance to use its methods
    mixin = DraggableTableMixin()
    return mixin._setup_draggable_table(table_widget, items_list, repopulate_callback)


# Example usage patterns:

"""
# Method 1: Use DraggableTableWidget directly
class MyTab(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        # Create draggable table from start
        self.table = DraggableTableWidget(0, 4)
        self.table.rowsReordered.connect(self._handle_reorder)

    def _handle_reorder(self, old_index, new_index):
        item = self._items.pop(old_index)
        self._items.insert(new_index, item)
        self._repopulate_table()


# Method 2: Use the mixin
class MyTab(QtWidgets.QWidget, DraggableTableMixin):
    def __init__(self):
        super().__init__()
        # Create regular table first
        self.table = QtWidgets.QTableWidget(0, 4)
        # Convert to draggable
        self.table = self._setup_draggable_table(self.table, self._items, self._repopulate_table)


# Method 3: Use utility function
class MyTab(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        # Create regular table first
        self.table = QtWidgets.QTableWidget(0, 4)
        # Convert to draggable
        self.table = make_table_draggable(self.table, self._items, self._repopulate_table)
"""
