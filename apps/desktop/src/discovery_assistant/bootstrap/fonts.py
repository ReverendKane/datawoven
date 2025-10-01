from pathlib import Path
import sys
from PySide6.QtGui import QFontDatabase, QFont

def resource_path(rel: str) -> Path:
    # Dev: use package dir; PyInstaller onefile: sys._MEIPASS temp dir
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base / rel

def load_app_fonts() -> str:
    font_dir = resource_path("assets/fonts")
    loaded = []
    for name in [
        "Montserrat-Regular.ttf",
        "Montserrat-SemiBold.ttf",
        "Roboto-Regular.ttf",
    ]:
        p = font_dir / name
        if p.exists():
            fid = QFontDatabase.addApplicationFont(str(p))
            if fid != -1:
                loaded += QFontDatabase.applicationFontFamilies(fid)
    if not loaded:
        raise RuntimeError("No fonts loaded—check assets inclusion.")
    # Prefer Montserrat if present
    return next((f for f in loaded if "Montserrat" in f), loaded[0])

def apply_default_font(app, family: str, point_size: int = 10) -> None:
    app.setFont(QFont(family, point_size))
