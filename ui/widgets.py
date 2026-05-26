from PySide6.QtGui import QColor
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QApplication, QFrame, QGraphicsDropShadowEffect, QLabel, QPushButton, QVBoxLayout


class Card(QFrame):
    def __init__(self, title: str = "", subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(77, 95, 133, 28))
        self.setGraphicsEffect(shadow)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(22, 20, 22, 20)
        self.layout.setSpacing(14)

        if title:
            heading = QLabel(title)
            heading.setObjectName("CardTitle")
            self.layout.addWidget(heading)
        if subtitle:
            caption = QLabel(subtitle)
            caption.setObjectName("CardSubtitle")
            caption.setWordWrap(True)
            self.layout.addWidget(caption)


class Pill(QLabel):
    def __init__(self, text: str, tone: str = "blue", parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignCenter)
        self.setProperty("tone", tone)
        self.setObjectName("Pill")


class TimeBlockButton(QPushButton):
    pressed_block = Signal(str)
    entered_block = Signal(str)
    released_block = Signal(str)

    def __init__(self, block_key: str, parent=None):
        super().__init__("", parent)
        self.block_key = block_key
        self.setMouseTracking(True)
        self.setObjectName("TimeBlock")
        self.setProperty("filled", False)
        self.setMinimumHeight(42)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.pressed_block.emit(self.block_key)
        super().mousePressEvent(event)

    def enterEvent(self, event):
        if QApplication.mouseButtons() & Qt.LeftButton:
            self.entered_block.emit(self.block_key)
        super().enterEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.released_block.emit(self.block_key)
        super().mouseReleaseEvent(event)
