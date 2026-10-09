"""Relicário — gerenciador de imagens. Ponto de entrada."""
import sys
from pathlib import Path

from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import QApplication

from app import styles
from app.ui import MainWindow

ROOT = Path(__file__).resolve().parent


def load_fonts() -> None:
    """Carrega fontes (.ttf/.otf) colocadas em assets/fonts, ex.: Cinzel."""
    for font in (ROOT / "assets" / "fonts").glob("*.[to]tf"):
        QFontDatabase.addApplicationFont(str(font))


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Relicário")
    load_fonts()
    app.setStyleSheet(styles.STYLESHEET)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
