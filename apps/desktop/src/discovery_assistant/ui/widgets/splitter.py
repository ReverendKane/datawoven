from PySide6 import QtCore, QtGui, QtWidgets

class GrippyHandle(QtWidgets.QSplitterHandle):
    DOT_RADIUS = 1.8   # size of each dot
    DOT_GAP    = 7     # px between dot centers (↓ this to reduce spacing)
    DOT_COUNT  = 3     # how many dots (odd number keeps one centered)

    def paintEvent(self, ev):
        super().paintEvent(ev)
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)

        c = self.palette().color(QtGui.QPalette.Mid)
        c.setAlpha(100)
        p.setBrush(c)
        p.setPen(QtCore.Qt.NoPen)

        w, h = self.width(), self.height()
        r = self.DOT_RADIUS

        half = self.DOT_COUNT // 2
        offsets = [ (i - half) * self.DOT_GAP for i in range(self.DOT_COUNT) ]

        if self.orientation() == QtCore.Qt.Horizontal:
            x = w / 2.0
            cy = h / 2.0
            for dy in offsets:
                p.drawEllipse(QtCore.QPointF(x, cy + dy), r, r)
        else:
            y = h / 2.0
            cx = w / 2.0
            for dx in offsets:
                p.drawEllipse(QtCore.QPointF(cx + dx, y), r, r)

class IconSplitter(QtWidgets.QSplitter):
    def createHandle(self):
        return GrippyHandle(self.orientation(), self)
