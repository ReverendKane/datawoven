import sys
from PySide6 import QtCore, QtWidgets

APP_NAME = "Discovery"
APP_VERSION = "0.1.0"
DISPLAY_VERSION = "v0.1"

def make_app():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)

    # Optional: predictable HiDPI rounding
    app.setHighDpiScaleFactorRoundingPolicy(
        QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    w = QtWidgets.QMainWindow()
    w.setWindowTitle(f"{APP_NAME} [{DISPLAY_VERSION}]")  # "Discovery [v.01]"

    # Size/center logic
    screen = app.primaryScreen()
    avail = screen.availableGeometry()
    target_w = max(960, min(int(avail.width() * 0.75), 1440))
    target_h = max(640, min(int(avail.height() * 0.80), 900))
    w.resize(target_w, target_h)
    w.setMinimumSize(QtCore.QSize(960, 640))

    frame = w.frameGeometry()
    frame.moveCenter(avail.center())
    w.move(frame.topLeft())

    w.show()
    app._main_window = w  # keep ref
    return app

if __name__ == "__main__":
    app = make_app()
    sys.exit(app.exec())
