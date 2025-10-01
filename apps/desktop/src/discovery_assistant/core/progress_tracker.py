from PySide6 import QtCore

class ProgressTracker(QtCore.QObject):
    progressChanged = QtCore.Signal(int)   # 0–100
    thresholdReached = QtCore.Signal(int)  # emits the % when first crossing threshold

    def __init__(self, sections: list[str], threshold: int = 60, parent=None):
        super().__init__(parent)
        self.threshold = threshold
        self._sections = {name: False for name in sections}
        self._fired_threshold = False

    def set_section_done(self, name: str, done: bool = True):
        if name not in self._sections:
            return
        self._sections[name] = done
        self._emit()

    def percent(self) -> int:
        total = max(1, len(self._sections))
        done = sum(1 for v in self._sections.values() if v)
        return int(round(100 * done / total))

    def _emit(self):
        p = self.percent()
        self.progressChanged.emit(p)
        if not self._fired_threshold and p >= self.threshold:
            self._fired_threshold = True
            self.thresholdReached.emit(p)
