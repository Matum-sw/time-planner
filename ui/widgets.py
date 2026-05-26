from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStyle,
    QStyleOptionButton,
    QVBoxLayout,
)


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
        self.task_text = ""
        self.setMouseTracking(True)
        self.setObjectName("TimeBlock")
        self.setProperty("filled", False)
        self.setMinimumHeight(16)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_task_text(self, text: str) -> None:
        self.task_text = text
        self.setText("")
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        option = QStyleOptionButton()
        self.initStyleOption(option)
        option.text = ""
        self.style().drawControl(QStyle.CE_PushButton, option, painter, self)

        if not self.task_text:
            return

        rect = self.rect().adjusted(5, 2, -5, -2)
        painter.setFont(self.scaled_font_for_text(self.task_text))
        painter.setPen(QColor(self.text_color()))
        painter.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap, self.task_text)

    def text_color(self) -> str:
        if self.property("life"):
            return "#477d37"
        if self.property("filled"):
            return "#1f5fcf"
        return "#647086"

    def scaled_font_for_text(self, text: str) -> QFont:
        font = QFont(self.font())
        compact_length = len(text.replace("\n", ""))
        line_count = max(1, text.count("\n") + 1)
        available_height = max(16, self.height() - 4)

        if not text:
            point_size = 10
        elif compact_length > 52 or line_count > 3 or available_height < 28:
            point_size = 6
        elif compact_length > 40:
            point_size = 7
        elif compact_length > 28:
            point_size = 8
        else:
            point_size = 9

        font.setPointSize(point_size)
        font.setBold(True)
        return font

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
