"""Interface gráfica (PyQt6): widgets customizados, grade de miniaturas,
painel de detalhes e janela principal."""
from __future__ import annotations

import math
import random
from pathlib import Path

from PyQt6.QtCore import (QEasingCurve, QObject, QPointF, QRectF, QRunnable, QSize, Qt,
                          QThreadPool, QTimer, QVariantAnimation, pyqtSignal)
from PyQt6.QtGui import (QBrush, QColor, QFont, QFontMetrics, QImage, QKeySequence,
                         QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QPolygonF,
                         QRadialGradient, QShortcut)
from PyQt6.QtWidgets import (QApplication, QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
                             QLineEdit, QListView, QListWidget, QListWidgetItem, QMainWindow,
                             QMessageBox, QPushButton, QStackedWidget, QStyle,
                             QStyledItemDelegate, QVBoxLayout, QWidget)
from PIL import Image

from . import image_ops as ops
from . import styles as st

CARD_W, CARD_H, THUMB = 164, 190, 136
MAX_LOADED = 1200  # miniaturas mantidas em memória antes de descartar as distantes

PATH_ROLE = Qt.ItemDataRole.UserRole
THUMB_ROLE = Qt.ItemDataRole.UserRole + 1
KEY_ROLE = Qt.ItemDataRole.UserRole + 2
REQ_ROLE = Qt.ItemDataRole.UserRole + 3
BROKEN_ROLE = Qt.ItemDataRole.UserRole + 4


# ------------------------------------------------------------------ helpers
def pil_to_qimage(img: Image.Image) -> QImage:
    img = img.convert("RGBA")
    w, h = img.size
    return QImage(img.tobytes("raw", "RGBA"), w, h, 4 * w, QImage.Format.Format_RGBA8888).copy()


def title_font(px: int, spacing: float = 3.0) -> QFont:
    f = QFont()
    f.setFamilies(st.TITLE_FAMILIES)
    f.setPixelSize(px)
    f.setWeight(QFont.Weight.DemiBold)
    f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
    return f


def make_label(text: str, name: str = "", wrap: bool = False) -> QLabel:
    lb = QLabel(text)
    if name:
        lb.setObjectName(name)
    lb.setWordWrap(wrap)
    return lb


def section_label(text: str) -> QLabel:
    lb = make_label(text.upper(), "section")
    f = lb.font()
    f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.6)
    lb.setFont(f)
    return lb


def diamond(c: QPointF, r: float) -> QPolygonF:
    return QPolygonF([QPointF(c.x(), c.y() - r), QPointF(c.x() + r, c.y()),
                      QPointF(c.x(), c.y() + r), QPointF(c.x() - r, c.y())])


def show_error(parent: QWidget, title: str, text: str) -> None:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.NoIcon)
    box.setWindowTitle("Relicário")
    box.setText(f"<b>{title}</b>")
    box.setInformativeText(text)
    box.addButton("Entendi", QMessageBox.ButtonRole.AcceptRole)
    box.exec()


def confirm(parent: QWidget, title: str, text: str, ok_text: str = "Confirmar") -> bool:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.NoIcon)
    box.setWindowTitle("Relicário")
    box.setText(f"<b>{title}</b>")
    box.setInformativeText(text)
    ok = box.addButton(ok_text, QMessageBox.ButtonRole.AcceptRole)
    cancel = box.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(cancel)
    box.exec()
    return box.clickedButton() is ok


# -------------------------------------------------------- fundo atmosférico
class AmbientBackdrop(QWidget):
    """Fundo animado leve com luz difusa, esporos e silhuetas de musgo."""

    def __init__(self, parent=None):
        super().__init__(parent)
        rng = random.Random(31)
        self._spores = [
            [rng.random(), rng.random(), rng.uniform(1.0, 2.4),
             rng.uniform(0.00025, 0.0008), rng.uniform(0, math.tau)]
            for _ in range(34)
        ]
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._animate)
        self._timer.start()

    def _animate(self) -> None:
        self._phase += 0.025
        for spore in self._spores:
            spore[1] -= spore[3]
            spore[0] += math.sin(self._phase + spore[4]) * 0.00012
            if spore[1] < -0.03:
                spore[1] = 1.03
                spore[0] = (spore[0] + 0.37) % 1
        self.update()

    def paintEvent(self, _event) -> None:
        w, h = self.width(), self.height()
        if not w or not h:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(st.BG))

        for x, y, radius, _, phase in (
            (0.50, 0.29, 0.52, 0, 0),
            (0.12, 0.68, 0.30, 0, 1.4),
            (0.91, 0.58, 0.34, 0, 3.0),
        ):
            pulse = 0.88 + math.sin(self._phase + phase) * 0.08
            center = QPointF(w * x, h * y)
            gradient = QRadialGradient(center, max(w, h) * radius)
            glow = QColor("#39c789")
            glow.setAlpha(round(38 * pulse))
            gradient.setColorAt(0, glow)
            glow.setAlpha(0)
            gradient.setColorAt(1, glow)
            p.fillRect(self.rect(), QBrush(gradient))

        floor = QLinearGradient(0, h * 0.68, 0, h)
        floor.setColorAt(0, QColor(8, 30, 22, 0))
        floor.setColorAt(1, QColor(3, 12, 10, 170))
        p.fillRect(self.rect(), QBrush(floor))

        moss = QPainterPath()
        moss.moveTo(0, h * 0.96)
        moss.cubicTo(w * 0.19, h * 0.91, w * 0.24, h * 0.99, w * 0.43, h * 0.95)
        moss.cubicTo(w * 0.67, h * 0.90, w * 0.81, h * 0.98, w, h * 0.92)
        moss.lineTo(w, h)
        moss.lineTo(0, h)
        moss.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(18, 54, 34, 72))
        p.drawPath(moss)

        p.setPen(QPen(QColor(66, 133, 75, 35), 1))
        for index, x in enumerate((0.06, 0.11, 0.86, 0.94)):
            length = h * (0.12 + (index % 2) * 0.08)
            vine = QPainterPath(QPointF(w * x, 0))
            vine.cubicTo(QPointF(w * (x - 0.015), length * 0.3),
                         QPointF(w * (x + 0.012), length * 0.65),
                         QPointF(w * x, length))
            p.drawPath(vine)

        for x, y, radius, _, phase in self._spores:
            alpha = round(55 + (math.sin(self._phase * 1.7 + phase) + 1) * 40)
            center = QPointF(x * w, y * h)
            glow = QRadialGradient(center, radius * 4)
            color = QColor("#a9ef68")
            color.setAlpha(alpha)
            glow.setColorAt(0, color)
            color.setAlpha(0)
            glow.setColorAt(1, color)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(glow))
            p.drawEllipse(center, radius * 4, radius * 4)
            color.setAlpha(min(alpha + 55, 220))
            p.setBrush(color)
            p.drawEllipse(center, radius * 0.65, radius * 0.65)


# ------------------------------------------------------- widgets customizados
class OrnateFrame(QFrame):
    """Moldura com borda fina dourada, filete interno carmesim e losangos."""

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        panel = QColor(st.PANEL)
        panel.setAlpha(232)
        p.setBrush(panel)
        p.setPen(QPen(QColor(st.GOLD_DIM), 1))
        p.drawRoundedRect(r, 10, 10)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(st.MOSS_ACCENT), 1))
        p.drawRoundedRect(r.adjusted(5, 5, -5, -5), 6, 6)
        p.setBrush(QColor(st.GOLD))
        p.setPen(Qt.PenStyle.NoPen)
        for y in (r.top(), r.bottom()):
            p.drawPolygon(diamond(QPointF(r.center().x(), y), 3.5))


class Divider(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(14)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy, w = self.width() / 2, self.height() / 2, self.width()
        line = QColor(st.GOLD_DIM)
        line.setAlpha(150)
        p.setPen(QPen(line, 1))
        p.drawLine(QPointF(0, cy), QPointF(cx - 12, cy))
        p.drawLine(QPointF(cx + 12, cy), QPointF(w, cy))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(st.GOLD))
        p.drawPolygon(diamond(QPointF(cx, cy), 3.5))


class AnimatedButton(QPushButton):
    """Botão com transição suave de cor ao passar o mouse."""

    def __init__(self, text: str, primary: bool = False, checkable: bool = False, parent=None):
        super().__init__(text, parent)
        self.primary = primary
        self.setCheckable(checkable)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(38)
        self._t = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(170)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_anim)

    def _on_anim(self, v):
        self._t = float(v)
        self.update()

    def _go(self, target: float):
        self._anim.stop()
        self._anim.setStartValue(self._t)
        self._anim.setEndValue(target)
        self._anim.start()

    def enterEvent(self, e):
        self._go(1.0)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._go(0.0)
        super().leaveEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        if not self.isEnabled():
            bg, border, fg = QColor("#0d1b15"), QColor("#20392c"), QColor(st.MUTED)
            fg.setAlpha(140)
        else:
            active = self.primary or self.isChecked()
            t = self._t
            bg = st.lerp(st.MOSS_DEEP if active else st.PANEL_2,
                         st.MOSS_HOVER if active else st.MOSS_DEEP, t)
            border = st.lerp(st.GOLD if self.isChecked() else st.GOLD_DIM, st.GOLD, t)
            fg = st.lerp(st.BONE if active else st.BONE_DIM, st.BONE, t)
            if self.isDown():
                bg = st.lerp(bg.name(), st.BG, 0.35)
        p.setBrush(bg)
        p.setPen(QPen(border, 1))
        p.drawRoundedRect(r, 7, 7)
        if self.hasFocus():
            focus = QColor(st.GOLD)
            focus.setAlpha(90)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(focus, 1, Qt.PenStyle.DotLine))
            p.drawRoundedRect(r.adjusted(3, 3, -3, -3), 5, 5)
        p.setPen(fg)
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, self.text())


class FormatCombo(QComboBox):
    def paintEvent(self, e):
        super().paintEvent(e)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QPointF(self.width() - 16, self.height() / 2)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(st.GOLD))
        p.drawPolygon(QPolygonF([QPointF(c.x() - 4, c.y() - 2), QPointF(c.x() + 4, c.y() - 2), QPointF(c.x(), c.y() + 3)]))


class PreviewWidget(QWidget):
    """Prévia grande, com fade-in suave ao trocar de imagem."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(150)
        self._pm: QPixmap | None = None
        self._opacity = 1.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(320)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_anim)

    def _on_anim(self, v):
        self._opacity = float(v)
        self.update()

    def set_pixmap(self, pm: QPixmap | None, fade: bool = False):
        self._pm = pm
        if fade and pm is not None:
            self._anim.stop()
            self._anim.start()
        else:
            self._opacity = 1.0
            self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setBrush(QColor(st.INPUT))
        p.setPen(QPen(QColor(st.BORDER), 1))
        p.drawRoundedRect(r, 8, 8)
        if self._pm is None or self._pm.isNull():
            p.setPen(QColor(st.MUTED))
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, "Selecione uma imagem")
            return
        box = self.rect().adjusted(10, 10, -10, -10)
        size = self._pm.size().scaled(box.size(), Qt.AspectRatioMode.KeepAspectRatio)
        if size.width() > self._pm.width():
            size = self._pm.size()
        x, y = box.center().x() - size.width() // 2, box.center().y() - size.height() // 2
        p.setOpacity(self._opacity)
        p.drawPixmap(x, y, size.width(), size.height(), self._pm)


# ------------------------------------------------------- grade de miniaturas
class ThumbSignals(QObject):
    done = pyqtSignal(str, int, QImage)
    failed = pyqtSignal(str, int)


class ThumbTask(QRunnable):
    def __init__(self, path: str, generation: int, signals: ThumbSignals):
        super().__init__()
        self.path, self.generation, self.signals = path, generation, signals

    def run(self):
        try:
            img = ops.make_thumbnail(Path(self.path), THUMB)
            self.signals.done.emit(self.path, self.generation, pil_to_qimage(img))
        except Exception:
            self.signals.failed.emit(self.path, self.generation)


class CardDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        return QSize(CARD_W, CARD_H)

    def paint(self, p, option, index):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        sel = bool(option.state & QStyle.StateFlag.State_Selected)
        hov = bool(option.state & QStyle.StateFlag.State_MouseOver)
        rect = QRectF(option.rect).adjusted(5, 5, -5, -5)
        bg = st.MOSS_DEEP if sel else (st.PANEL_2 if hov else "#0b1712")
        border = st.GOLD if sel else (st.MOSS_HOVER if hov else st.BORDER)
        p.setBrush(QColor(bg))
        p.setPen(QPen(QColor(border), 1.5 if sel else 1))
        p.drawRoundedRect(rect, 8, 8)

        box = QRectF(rect.left() + 9, rect.top() + 9, rect.width() - 18, rect.height() - 46)
        pm = index.data(THUMB_ROLE)
        if isinstance(pm, QPixmap) and not pm.isNull():
            p.drawPixmap(QPointF(box.center().x() - pm.width() / 2, box.center().y() - pm.height() / 2), pm)
        else:
            p.setPen(QColor(st.MUTED))
            p.drawText(box, Qt.AlignmentFlag.AlignCenter, "✕" if index.data(BROKEN_ROLE) else "◆")

        f = QFont(option.font)
        f.setPixelSize(11)
        p.setFont(f)
        p.setPen(QColor(st.BONE if sel else st.BONE_DIM))
        name = Path(index.data(PATH_ROLE)).name
        text = QFontMetrics(f).elidedText(name, Qt.TextElideMode.ElideMiddle, int(rect.width() - 16))
        p.drawText(QRectF(rect.left() + 8, rect.bottom() - 30, rect.width() - 16, 22),
                   Qt.AlignmentFlag.AlignCenter, text)
        p.restore()


class ThumbnailGrid(QListWidget):
    """Grade com rolagem. Miniaturas são geradas em threads, apenas para os
    itens visíveis (e uma margem), e reaproveitadas entre atualizações."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListView.ViewMode.IconMode)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setMovement(QListView.Movement.Static)
        self.setUniformItemSizes(True)
        self.setSpacing(2)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setMouseTracking(True)
        self.setItemDelegate(CardDelegate(self))
        self.verticalScrollBar().setSingleStep(40)

        self._generation = 0
        self._rows: dict[str, int] = {}
        self._loaded = 0
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(4)
        self._signals = ThumbSignals(self)
        self._signals.done.connect(self._on_done)
        self._signals.failed.connect(self._on_failed)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(60)
        self._timer.timeout.connect(self._request_visible)
        self.verticalScrollBar().valueChanged.connect(lambda _: self._timer.start())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._timer.start()

    def set_entries(self, entries: list[ops.ImageEntry]) -> None:
        old = {}
        for i in range(self.count()):
            it = self.item(i)
            pm = it.data(THUMB_ROLE)
            if isinstance(pm, QPixmap):
                old[it.data(PATH_ROLE)] = (it.data(KEY_ROLE), pm)
        self._generation += 1
        self._pool.clear()
        self._rows.clear()
        self._loaded = 0
        self.blockSignals(True)
        self.clear()
        for row, e in enumerate(entries):
            it = QListWidgetItem()
            key = (e.mtime_ns, e.size)
            it.setData(PATH_ROLE, str(e.path))
            it.setData(KEY_ROLE, key)
            it.setSizeHint(QSize(CARD_W, CARD_H))
            prev = old.get(str(e.path))
            if prev and prev[0] == key:  # arquivo inalterado: reaproveita a miniatura
                it.setData(THUMB_ROLE, prev[1])
                it.setData(REQ_ROLE, True)
                self._loaded += 1
            self.addItem(it)
            self._rows[str(e.path)] = row
        self.blockSignals(False)
        QTimer.singleShot(0, self._request_visible)

    def select_path(self, path: Path | None) -> None:
        row = self._rows.get(str(path)) if path else None
        self.blockSignals(True)
        if row is None:
            self.clearSelection()
            self.setCurrentItem(None)
        else:
            self.setCurrentRow(row)
            self.scrollToItem(self.item(row), QListWidget.ScrollHint.EnsureVisible)
        self.blockSignals(False)

    def _zone(self, factor: float):
        vp = self.viewport().rect()
        m = int(vp.height() * factor)
        return vp.adjusted(0, -m, 0, m)

    def _request_visible(self) -> None:
        zone = self._zone(1.0)
        for i in range(self.count()):
            it = self.item(i)
            if it.data(REQ_ROLE):
                continue
            if self.visualItemRect(it).intersects(zone):
                it.setData(REQ_ROLE, True)
                self._pool.start(ThumbTask(it.data(PATH_ROLE), self._generation, self._signals))

    def _on_done(self, path: str, gen: int, img: QImage) -> None:
        row = self._rows.get(path)
        if gen != self._generation or row is None:
            return
        it = self.item(row)
        it.setData(THUMB_ROLE, QPixmap.fromImage(img))
        self.viewport().update(self.visualItemRect(it))
        self._loaded += 1
        if self._loaded > MAX_LOADED:
            self._evict()

    def _on_failed(self, path: str, gen: int) -> None:
        row = self._rows.get(path)
        if gen != self._generation or row is None:
            return
        it = self.item(row)
        it.setData(BROKEN_ROLE, True)
        self.viewport().update(self.visualItemRect(it))

    def _evict(self) -> None:
        zone = self._zone(2.0)
        kept = 0
        for i in range(self.count()):
            it = self.item(i)
            if isinstance(it.data(THUMB_ROLE), QPixmap):
                if self.visualItemRect(it).intersects(zone):
                    kept += 1
                else:
                    it.setData(THUMB_ROLE, None)
                    it.setData(REQ_ROLE, None)
        self._loaded = kept


# ---------------------------------------------------------- painel de detalhes
class DetailPanel(OrnateFrame):
    changed = pyqtSignal(object)  # Path final após renomear/salvar

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(400)
        self._path: Path | None = None
        self._data: ops.Preview | None = None
        self._flip_h = self._flip_v = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 22)
        lay.setSpacing(8)

        title = make_label("DETALHES", "title")
        title.setFont(title_font(16))
        lay.addWidget(title)
        lay.addWidget(Divider())

        self.preview = PreviewWidget()
        lay.addWidget(self.preview, 1)
        lay.addSpacing(6)
        self.name_label = make_label("—", "name")
        self.info_label = make_label("", "muted")
        lay.addWidget(self.name_label)
        lay.addWidget(self.info_label)
        lay.addWidget(Divider())

        lay.addWidget(section_label("Espelhar"))
        row = QHBoxLayout()
        row.setSpacing(8)
        self.btn_h = AnimatedButton("Horizontal", checkable=True)
        self.btn_v = AnimatedButton("Vertical", checkable=True)
        self.btn_h.toggled.connect(self._on_flip)
        self.btn_v.toggled.connect(self._on_flip)
        row.addWidget(self.btn_h)
        row.addWidget(self.btn_v)
        lay.addLayout(row)

        lay.addWidget(section_label("Converter formato"))
        self.combo = FormatCombo()
        self.combo.currentIndexChanged.connect(self._on_format)
        lay.addWidget(self.combo)

        lay.addWidget(section_label("Nome do arquivo"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Nome do arquivo (sem extensão)")
        self.name_edit.textChanged.connect(self._validate_name)
        self.name_edit.returnPressed.connect(self._apply)
        lay.addWidget(self.name_edit)
        self.error_label = make_label("", "error", wrap=True)
        self.error_label.setMinimumHeight(18)
        lay.addWidget(self.error_label)

        lay.addWidget(Divider())
        row = QHBoxLayout()
        row.setSpacing(8)
        self.btn_revert = AnimatedButton("Descartar")
        self.btn_apply = AnimatedButton("Aplicar alterações", primary=True)
        self.btn_revert.clicked.connect(self._revert)
        self.btn_apply.clicked.connect(self._apply)
        row.addWidget(self.btn_revert)
        row.addWidget(self.btn_apply, 1)
        lay.addLayout(row)
        self.clear()

    # ----- estado
    @property
    def path(self) -> Path | None:
        return self._path

    def _target_ext(self) -> str:
        return (self.combo.currentData() or self._path.suffix).lower()

    @property
    def is_dirty(self) -> bool:
        if self._path is None:
            return False
        return (
            self._flip_h
            or self._flip_v
            or self._target_ext() != self._path.suffix.lower()
            or self.name_edit.text().strip() != self._path.stem
        )

    def _controls(self):
        return (self.btn_h, self.btn_v, self.combo, self.name_edit)

    def clear(self) -> None:
        self._path = self._data = None
        self._flip_h = self._flip_v = False
        self.preview.set_pixmap(None)
        self.name_label.setText("—")
        self.info_label.setText("Escolha uma miniatura para editar.")
        self.error_label.setText("")
        for w in self._controls():
            w.setEnabled(False)
        self.btn_apply.setEnabled(False)
        self.btn_revert.setEnabled(False)

    def load(self, path: Path) -> bool:
        try:
            data = ops.load_preview(path)
        except ops.ImageError as exc:
            self.clear()
            show_error(self, "Não foi possível abrir a imagem", str(exc))
            return False
        self._path, self._data = path, data
        self._flip_h = self._flip_v = False
        for b in (self.btn_h, self.btn_v):
            b.blockSignals(True)
            b.setChecked(False)
            b.blockSignals(False)
        self.combo.blockSignals(True)
        self.combo.clear()
        self.combo.addItem(f"Manter formato ({path.suffix.upper().lstrip('.')})", None)
        for label, ext in ops.OUTPUT_FORMATS.items():
            self.combo.addItem(label, ext)
        self.combo.blockSignals(False)
        for w in self._controls():
            w.setEnabled(True)
        self.name_edit.blockSignals(True)
        self.name_edit.setText(path.stem)
        self.name_edit.blockSignals(False)
        self._update_header()
        self._validate_name()
        self._refresh_preview(fade=True)
        self._update_buttons()
        return True

    def _update_header(self) -> None:
        p, d = self._path, self._data
        fm = QFontMetrics(self.name_label.font())
        self.name_label.setText(fm.elidedText(p.name, Qt.TextElideMode.ElideMiddle, 340))
        self.name_label.setToolTip(p.name)
        self.info_label.setText(f"{d.size[0]} × {d.size[1]} px  ·  {ops.format_size(d.file_size)}  ·  {d.fmt}")

    def _update_buttons(self) -> None:
        dirty = self.is_dirty
        valid_name = self._path is not None and not self.error_label.text()
        self.btn_apply.setEnabled(dirty and valid_name)
        self.btn_revert.setEnabled(dirty)

    # ----- prévia
    def _refresh_preview(self, fade: bool = False) -> None:
        img = ops.apply_flips(self._data.image, self._flip_h, self._flip_v)
        if self._target_ext() in (".jpg", ".jpeg") and self._data.has_alpha:
            img = ops.flatten_on_white(img)  # mostra como ficará o fundo branco
        self.preview.set_pixmap(QPixmap.fromImage(pil_to_qimage(img)), fade)

    def _on_flip(self) -> None:
        self._flip_h, self._flip_v = self.btn_h.isChecked(), self.btn_v.isChecked()
        self._refresh_preview()
        self._update_buttons()

    def _on_format(self) -> None:
        self._refresh_preview()
        self._update_buttons()

    def _revert(self) -> None:
        if self._path:
            self.load(self._path)

    # ----- renomear
    def _validate_name(self) -> None:
        if self._path is None:
            return
        stem = self.name_edit.text().strip()
        unchanged = (stem + self._path.suffix) == self._path.name
        err = None if unchanged else ops.check_new_stem(stem, self._path)
        self.error_label.setText(err or "")
        self._update_buttons()

    # ----- salvar
    def _apply(self) -> None:
        if not self.is_dirty or not self.btn_apply.isEnabled():
            return
        old, ext = self._path, self._target_ext()
        stem = self.name_edit.text().strip()
        renaming = stem != old.stem
        converting = ext != old.suffix.lower()
        new_path = old.with_name(f"{stem}{ext}")
        changes = []
        if renaming:
            changes.append(f"o arquivo passará a se chamar «{new_path.name}»")
        if converting:
            changes.append(f"o formato será convertido para {ext.lstrip('.').upper()}")
        if self._flip_h or self._flip_v:
            changes.append("as alterações de espelhamento serão aplicadas")
        if converting or self._flip_h or self._flip_v:
            text = f"«{old.name}» será substituído; " + " e ".join(changes) + "."
            if self._data.has_alpha and ext in (".jpg", ".jpeg"):
                text += "\n\nA transparência será substituída por fundo branco."
        else:
            text = f"«{old.name}» será renomeado para «{new_path.name}»."
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            if converting or self._flip_h or self._flip_v:
                result = ops.save_edited(old, self._flip_h, self._flip_v, ext, stem)
            else:
                result = ops.rename_image(old, stem)
        except ops.ImageError as exc:
            QApplication.restoreOverrideCursor()
            show_error(self, "Não foi possível aplicar as alterações", str(exc))
            return
        QApplication.restoreOverrideCursor()
        self.load(result)
        self.changed.emit(result)


# ----------------------------------------------------------------- janela
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Relicário — Gerenciador de imagens")
        self.resize(1240, 780)
        self.setMinimumSize(920, 620)
        self.folder: Path | None = None

        root = AmbientBackdrop()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(28, 22, 28, 26)
        outer.setSpacing(18)

        # cabeçalho
        head = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(2)
        title = make_label("RELICÁRIO", "title")
        title.setFont(title_font(28, 6))
        titles.addWidget(title)
        titles.addWidget(make_label("Gerenciador de imagens", "muted"))
        head.addLayout(titles)
        head.addStretch(1)
        self.path_label = make_label("Nenhuma pasta selecionada", "muted")
        head.addWidget(self.path_label)
        head.addSpacing(14)
        self.btn_folder = AnimatedButton("Escolher pasta", primary=True)
        self.btn_folder.setMinimumWidth(150)
        self.btn_folder.clicked.connect(self.choose_folder)
        head.addWidget(self.btn_folder)
        outer.addLayout(head)

        # conteúdo
        body = QHBoxLayout()
        body.setSpacing(18)
        card = OrnateFrame()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 18, 14, 18)
        cl.setSpacing(8)
        top = QHBoxLayout()
        top.addWidget(section_label("Galeria"))
        top.addStretch(1)
        self.count_label = make_label("", "muted")
        top.addWidget(self.count_label)
        top.addSpacing(8)
        cl.addLayout(top)
        cl.addWidget(Divider())
        self.stack = QStackedWidget()
        self.grid = ThumbnailGrid()
        self.empty = make_label("", "empty", wrap=True)
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stack.addWidget(self.grid)
        self.stack.addWidget(self.empty)
        cl.addWidget(self.stack, 1)
        body.addWidget(card, 1)

        self.panel = DetailPanel()
        body.addWidget(self.panel)
        outer.addLayout(body, 1)

        self.grid.currentItemChanged.connect(self._on_current)
        self.panel.changed.connect(self._on_changed)
        QShortcut(QKeySequence("F5"), self, activated=self.reload)
        self._show_empty("Escolha uma pasta para começar.")

    # ----- pasta
    def _show_empty(self, text: str) -> None:
        self.empty.setText(text)
        self.stack.setCurrentWidget(self.empty)
        self.count_label.setText("")

    def _confirm_discard(self) -> bool:
        if not self.panel.is_dirty:
            return True
        return confirm(self, "Alterações não aplicadas",
                       "Descartar as alterações não aplicadas desta imagem?", "Descartar")

    def choose_folder(self) -> None:
        if not self._confirm_discard():
            return
        start = str(self.folder) if self.folder else str(Path.home())
        chosen = QFileDialog.getExistingDirectory(self, "Escolher pasta de imagens", start)
        if chosen:
            self.panel.clear()
            self.load_folder(Path(chosen))

    def reload(self) -> None:
        if self.folder and self._confirm_discard():
            self.panel.clear()
            self.load_folder(self.folder)

    def load_folder(self, folder: Path, select: Path | None = None) -> bool:
        try:
            entries = ops.list_images(folder)
        except ops.ImageError as exc:
            show_error(self, "Não foi possível abrir a pasta", str(exc))
            return False
        self.folder = folder
        fm = QFontMetrics(self.path_label.font())
        self.path_label.setText(fm.elidedText(str(folder), Qt.TextElideMode.ElideLeft, 360))
        self.path_label.setToolTip(str(folder))
        self.grid.set_entries(entries)
        if not entries:
            self.panel.clear()
            self._show_empty("Nenhuma imagem encontrada nesta pasta.\nFormatos aceitos: JPG, JPEG, PNG, WEBP e BMP.")
            return True
        n = len(entries)
        self.count_label.setText(f"{n} {'imagem' if n == 1 else 'imagens'}")
        self.stack.setCurrentWidget(self.grid)
        self.grid.select_path(select)
        return True

    # ----- eventos
    def _on_current(self, current, _previous) -> None:
        if current is None:
            return
        path = Path(current.data(PATH_ROLE))
        if path == self.panel.path:
            return
        if not self._confirm_discard():
            self.grid.select_path(self.panel.path)
            return
        self.panel.load(path)

    def _on_changed(self, path: Path) -> None:
        """Após renomear/salvar: recarrega a pasta e a grade, mantendo a seleção."""
        self.load_folder(self.folder, select=path)
