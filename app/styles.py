"""Paleta e folha de estilos (bosque profundo, musgo e luz bioluminescente)."""
from PyQt6.QtGui import QColor

PALETTE = {
    "BG": "#06110f",
    "BG_2": "#0a211b",
    "PANEL": "#0b1915",
    "PANEL_2": "#10251e",
    "MOSS_DEEP": "#172c20",
    "MOSS_ACCENT": "#315b40",
    "MOSS_HOVER": "#527b4d",
    "RED_BRIGHT": "#e16a72",
    "GOLD": "#a6bf75",
    "GOLD_DIM": "#536f48",
    "BONE": "#e3ead7",
    "BONE_DIM": "#aebca5",
    "MUTED": "#788d7d",
    "BORDER": "#244438",
    "INPUT": "#091510",
}
globals().update(PALETTE)

# Títulos: Cinzel se estiver instalada/embutida; senão, serifadas elegantes.
TITLE_FAMILIES = ["Cinzel", "Trajan Pro", "Palatino Linotype", "Book Antiqua", "Georgia", "serif"]


def lerp(a: str, b: str, t: float) -> QColor:
    ca, cb = QColor(a), QColor(b)
    return QColor(
        round(ca.red() + (cb.red() - ca.red()) * t),
        round(ca.green() + (cb.green() - ca.green()) * t),
        round(ca.blue() + (cb.blue() - ca.blue()) * t),
    )


_TEMPLATE = """
QWidget {
    color: @BONE@;
    font-family: "Segoe UI", "Inter", "Helvetica Neue", "Noto Sans", sans-serif;
    font-size: 13px;
}
QMainWindow, QDialog, QMessageBox {
    background: @BG@;
}
#root {
    background: transparent;
}
QLabel { background: transparent; }
QLabel#title { color: @GOLD@; font-weight: 700; font-family: "Cinzel", "Trajan Pro", "Palatino Linotype", "Book Antiqua", Georgia, serif; }
QLabel#section { color: @GOLD@; font-size: 11px; font-weight: 600; }
QLabel#muted { color: @MUTED@; font-size: 12px; }
QLabel#name { color: @BONE@; font-size: 14px; font-weight: 600; }
QLabel#error { color: @RED_BRIGHT@; font-size: 12px; }
QLabel#empty { color: @MUTED@; font-size: 14px; }

QLineEdit {
    background: @INPUT@;
    border: 1px solid @BORDER@;
    border-radius: 6px;
    padding: 8px 10px;
    selection-background-color: @MOSS_ACCENT@;
}
QLineEdit:hover { border-color: @GOLD_DIM@; }
QLineEdit:focus { border-color: @GOLD@; }
QLineEdit:disabled { color: @MUTED@; }

QComboBox {
    background: @INPUT@;
    border: 1px solid @BORDER@;
    border-radius: 6px;
    padding: 8px 10px;
    min-height: 20px;
}
QComboBox:hover { border-color: @GOLD_DIM@; }
QComboBox:focus, QComboBox:on { border-color: @GOLD@; }
QComboBox::drop-down { border: none; width: 28px; }
QComboBox::down-arrow { image: none; }
QComboBox QAbstractItemView {
    background: @PANEL_2@;
    border: 1px solid @GOLD_DIM@;
    selection-background-color: @MOSS_ACCENT@;
    selection-color: @BONE@;
    outline: 0;
    padding: 4px;
}

QListWidget { background: transparent; border: none; outline: 0; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: @MOSS_ACCENT@; border-radius: 3px; min-height: 36px; }
QScrollBar::handle:vertical:hover { background: @MOSS_HOVER@; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }

QToolTip {
    background: @PANEL_2@; color: @BONE@;
    border: 1px solid @GOLD_DIM@; padding: 4px 8px;
}
QMessageBox QLabel { color: @BONE@; min-width: 320px; }
QMessageBox QPushButton {
    background: @PANEL_2@;
    border: 1px solid @GOLD_DIM@;
    border-radius: 6px;
    padding: 7px 18px;
    min-width: 88px;
}
QMessageBox QPushButton:hover { border-color: @GOLD@; background: @MOSS_DEEP@; }
"""

STYLESHEET = _TEMPLATE
for _k, _v in PALETTE.items():
    STYLESHEET = STYLESHEET.replace(f"@{_k}@", _v)
