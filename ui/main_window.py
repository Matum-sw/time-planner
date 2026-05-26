from collections import defaultdict
from datetime import datetime
import time

from PySide6.QtCore import QDate, QTimer, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.openai_feedback import AIFeedbackService
from core.reporting import build_markdown_report, save_markdown_report
from ui.subject_dialog import SubjectDialog
from ui.widgets import Card, Pill, TimeBlockButton


HOURS = list(range(4, 25))
MINUTES = (0, 10, 20, 30, 40, 50)


class MainWindow(QMainWindow):
    def __init__(self, store):
        super().__init__()
        self.store = store
        self.ai = AIFeedbackService()
        self.day = self.store.today()
        self.selected_todo_id = None
        self.todo_lookup = {}
        self.block_buttons = {}
        self.drag_todo_id = None
        self.drag_visited_blocks = set()
        self.drag_is_painting = False
        self.running = None
        self.tick = QTimer(self)
        self.tick.timeout.connect(self.update_timer)

        self.setWindowTitle("Daily Time Box Planner")
        self.resize(1360, 900)
        self.setMinimumSize(1180, 760)

        if not self.store.has_real_subjects():
            SubjectDialog(self.store, self).exec()

        self.build()
        self.refresh_all()

    def build(self) -> None:
        page = QWidget()
        page.setObjectName("AppRoot")
        self.setCentralWidget(page)

        root = QVBoxLayout(page)
        root.setContentsMargins(34, 30, 34, 30)
        root.setSpacing(24)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Daily Time Box Planner")
        title.setObjectName("AppTitle")
        subtitle = QLabel("Plan the day, protect deep work, and keep life tasks out of study stats.")
        subtitle.setObjectName("AppSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.dateChanged.connect(self.change_date)
        subject_button = QPushButton("과목 관리")
        subject_button.clicked.connect(self.open_subjects)
        subject_button.setObjectName("GhostButton")

        header.addLayout(title_box, 1)
        header.addWidget(self.date_edit)
        header.addWidget(subject_button)
        root.addLayout(header)

        board = QHBoxLayout()
        board.setSpacing(22)
        root.addLayout(board, 1)

        left = QVBoxLayout()
        left.setSpacing(18)
        board.addLayout(left, 3)

        middle = QVBoxLayout()
        middle.setSpacing(18)
        board.addLayout(middle, 5)

        right = QVBoxLayout()
        right.setSpacing(18)
        board.addLayout(right, 2)

        self.build_todo_card(left)
        self.build_brain_card(left)
        self.build_plan_card(middle)
        self.build_timer_card(right)
        self.build_stats_card(right)

    def build_todo_card(self, parent) -> None:
        card = Card("To Do List", "오늘 할 일을 과목 또는 기타 카테고리에 연결하세요.")
        parent.addWidget(card, 3)

        form = QHBoxLayout()
        self.todo_input = QLineEdit()
        self.todo_input.setPlaceholderText("예: 자료구조 복습하기")
        self.todo_input.returnPressed.connect(self.add_todo)
        self.subject_combo = QComboBox()
        self.add_button = QPushButton("추가")
        self.add_button.setObjectName("PrimaryButton")
        self.add_button.clicked.connect(self.add_todo)
        form.addWidget(self.todo_input, 1)
        form.addWidget(self.subject_combo)
        form.addWidget(self.add_button)
        card.layout.addLayout(form)

        self.todo_list = QListWidget()
        self.todo_list.itemClicked.connect(self.select_todo)
        card.layout.addWidget(self.todo_list, 1)

    def build_brain_card(self, parent) -> None:
        card = Card("Brain Dump", "떠오르는 일을 빠르게 비워두는 공간.")
        parent.addWidget(card, 2)
        self.brain_dump = QTextEdit()
        self.brain_dump.setPlaceholderText("걱정, 아이디어, 나중에 정리할 일...")
        self.brain_dump.textChanged.connect(self.save_brain_dump)
        card.layout.addWidget(self.brain_dump, 1)

    def build_plan_card(self, parent) -> None:
        card = Card(
            "Time Plan",
            "To Do를 선택하고 시간 블록을 클릭하거나 드래그하면 배치됩니다. 배치된 블록을 다시 클릭하면 타이머가 시작됩니다.",
        )
        parent.addWidget(card, 1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("PlanScroll")
        grid_widget = QWidget()
        grid_widget.setObjectName("TimeGrid")
        self.time_grid = QGridLayout(grid_widget)
        self.time_grid.setSpacing(8)
        self.time_grid.setContentsMargins(4, 4, 4, 4)

        self.time_grid.addWidget(QLabel(""), 0, 0)
        for column, minute in enumerate(MINUTES, start=1):
            label = QLabel(f"{minute:02d}")
            label.setObjectName("GridHeader")
            label.setAlignment(Qt.AlignCenter)
            self.time_grid.addWidget(label, 0, column)

        for row, hour in enumerate(HOURS, start=1):
            hour_label = QLabel(str(hour))
            hour_label.setObjectName("HourLabel")
            hour_label.setAlignment(Qt.AlignCenter)
            self.time_grid.addWidget(hour_label, row, 0)
            for column, minute in enumerate(MINUTES, start=1):
                key = f"{hour:02d}:{minute:02d}"
                button = TimeBlockButton(key)
                button.pressed_block.connect(self.on_block_pressed)
                button.entered_block.connect(self.on_block_entered)
                button.released_block.connect(self.on_block_released)
                self.block_buttons[key] = button
                self.time_grid.addWidget(button, row, column)

        scroll.setWidget(grid_widget)
        card.layout.addWidget(scroll, 1)

    def build_timer_card(self, parent) -> None:
        card = Card("Timer", "선택된 시간 블록의 집중 시간을 기록합니다.")
        parent.addWidget(card)
        self.timer_context = QLabel("아직 실행 중인 타이머가 없어요.")
        self.timer_context.setObjectName("TimerContext")
        self.timer_context.setWordWrap(True)
        self.timer_value = QLabel("00:00:00")
        self.timer_value.setObjectName("TimerValue")
        self.timer_value.setAlignment(Qt.AlignCenter)
        card.layout.addWidget(self.timer_context)
        card.layout.addWidget(self.timer_value)

        actions = QHBoxLayout()
        self.stop_button = QPushButton("저장")
        self.stop_button.setObjectName("PrimaryButton")
        self.stop_button.clicked.connect(lambda: self.stop_timer("completed"))
        self.pause_button = QPushButton("중단")
        self.pause_button.setObjectName("SoftButton")
        self.pause_button.clicked.connect(lambda: self.stop_timer("paused"))
        self.defer_button = QPushButton("미룸")
        self.defer_button.setObjectName("SoftButton")
        self.defer_button.clicked.connect(lambda: self.stop_timer("deferred"))
        actions.addWidget(self.stop_button)
        actions.addWidget(self.pause_button)
        actions.addWidget(self.defer_button)
        card.layout.addLayout(actions)

    def build_stats_card(self, parent) -> None:
        card = Card("Study Stats", "기타는 생활 일정으로만 집계하고 공부 통계에서는 제외합니다.")
        parent.addWidget(card, 1)
        self.stats_container = QVBoxLayout()
        card.layout.addLayout(self.stats_container)

        report_actions = QHBoxLayout()
        report_button = QPushButton("Markdown 리포트")
        report_button.setObjectName("PrimaryButton")
        report_button.clicked.connect(self.generate_report)
        ai_button = QPushButton("AI 피드백")
        ai_button.setObjectName("GhostButton")
        ai_button.clicked.connect(self.show_ai_feedback)
        report_actions.addWidget(report_button)
        report_actions.addWidget(ai_button)
        card.layout.addLayout(report_actions)

    def add_todo(self) -> None:
        title = self.todo_input.text().strip()
        if not title:
            return
        subject_id = self.subject_combo.currentData()
        self.store.add_todo(self.day, title, subject_id)
        self.todo_input.clear()
        self.refresh_todos()

    def select_todo(self, item: QListWidgetItem) -> None:
        self.selected_todo_id = item.data(Qt.UserRole)
        self.refresh_todos()

    def on_block_pressed(self, block_key: str) -> None:
        if self.selected_todo_id:
            self.drag_todo_id = self.selected_todo_id
            self.drag_visited_blocks = set()
            self.drag_is_painting = True
            self.paint_todo_to_block(block_key)
            return

        blocks = self.store.blocks_for_day(self.day)
        todo_id = blocks.get(block_key)
        if todo_id:
            self.start_timer(block_key, todo_id)
            return
        QMessageBox.information(self, "To Do 선택", "먼저 To Do 카드를 선택한 뒤 시간 블록을 클릭하세요.")

    def on_block_entered(self, block_key: str) -> None:
        if not self.drag_is_painting or not self.drag_todo_id:
            return
        self.paint_todo_to_block(block_key)

    def on_block_released(self, block_key: str) -> None:
        if not self.drag_is_painting:
            return

        visited_count = len(self.drag_visited_blocks)
        todo_id = self.drag_todo_id
        self.drag_todo_id = None
        self.drag_is_painting = False
        self.drag_visited_blocks = set()
        self.refresh_blocks()

        if visited_count == 1 and todo_id:
            self.start_timer(block_key, todo_id)

    def paint_todo_to_block(self, block_key: str) -> None:
        if not self.drag_todo_id or block_key in self.drag_visited_blocks:
            return
        self.store.assign_block(self.day, block_key, self.drag_todo_id)
        self.drag_visited_blocks.add(block_key)
        self.refresh_single_block(block_key, self.drag_todo_id)

    def on_block_clicked(self, block_key: str) -> None:
        blocks = self.store.blocks_for_day(self.day)
        if self.selected_todo_id:
            self.store.assign_block(self.day, block_key, self.selected_todo_id)
            self.start_timer(block_key, self.selected_todo_id)
            self.refresh_blocks()
            return
        todo_id = blocks.get(block_key)
        if todo_id:
            self.start_timer(block_key, todo_id)
            return
        QMessageBox.information(self, "To Do 선택", "먼저 To Do 카드를 선택한 뒤 시간 블록을 클릭하세요.")

    def start_timer(self, block_key: str, todo_id: int) -> None:
        if self.running:
            self.stop_timer("completed")
        todo = self.todo_lookup[todo_id]
        self.running = {
            "block_key": block_key,
            "todo_id": todo_id,
            "subject_id": todo.subject_id,
            "started_at": time.time(),
            "title": todo.title,
            "subject": todo.subject_name,
        }
        self.timer_context.setText(f"{block_key} · {todo.subject_name}\n{todo.title}")
        self.tick.start(1000)
        self.update_timer()

    def update_timer(self) -> None:
        if not self.running:
            self.timer_value.setText("00:00:00")
            return
        elapsed = int(time.time() - self.running["started_at"])
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.timer_value.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")

    def stop_timer(self, event_type: str) -> None:
        if not self.running:
            return
        self.tick.stop()
        ended = time.time()
        started_at = datetime.fromtimestamp(self.running["started_at"]).isoformat(timespec="seconds")
        ended_at = datetime.fromtimestamp(ended).isoformat(timespec="seconds")
        seconds = max(1, int(ended - self.running["started_at"]))
        memo = ""
        if event_type in {"paused", "deferred"}:
            memo = "사용자가 타이머 카드에서 기록"
        self.store.add_timer_record(
            self.day,
            self.running["todo_id"],
            self.running["subject_id"],
            self.running["block_key"],
            event_type,
            seconds,
            started_at,
            ended_at,
            memo,
        )
        if event_type == "completed":
            self.store.set_todo_status(self.running["todo_id"], "done")
        elif event_type == "deferred":
            self.store.set_todo_status(self.running["todo_id"], "deferred")
        self.running = None
        self.timer_context.setText("기록이 저장됐어요.")
        self.update_timer()
        self.refresh_all()

    def save_brain_dump(self) -> None:
        if hasattr(self, "brain_dump"):
            self.store.save_brain_dump(self.day, self.brain_dump.toPlainText())

    def change_date(self, qdate: QDate) -> None:
        self.day = qdate.toString("yyyy-MM-dd")
        self.selected_todo_id = None
        self.refresh_all()

    def open_subjects(self) -> None:
        SubjectDialog(self.store, self).exec()
        self.refresh_subjects()

    def refresh_all(self) -> None:
        self.refresh_subjects()
        self.refresh_todos()
        self.refresh_brain_dump()
        self.refresh_blocks()
        self.refresh_stats()

    def refresh_subjects(self) -> None:
        current = self.subject_combo.currentData() if hasattr(self, "subject_combo") else None
        self.subject_combo.clear()
        for subject in self.store.subjects(include_other=True):
            self.subject_combo.addItem(subject.name, subject.id)
        if current:
            index = self.subject_combo.findData(current)
            if index >= 0:
                self.subject_combo.setCurrentIndex(index)

    def refresh_todos(self) -> None:
        self.todo_list.clear()
        self.todo_lookup = {todo.id: todo for todo in self.store.todos_for_day(self.day)}
        for todo in self.todo_lookup.values():
            item = QListWidgetItem(f"{todo.title}\n{todo.subject_name} · {self.status_label(todo.status)}")
            item.setData(Qt.UserRole, todo.id)
            item.setSelected(todo.id == self.selected_todo_id)
            self.todo_list.addItem(item)

    def refresh_brain_dump(self) -> None:
        content = self.store.brain_dump(self.day)
        if self.brain_dump.toPlainText() != content:
            self.brain_dump.blockSignals(True)
            self.brain_dump.setPlainText(content)
            self.brain_dump.blockSignals(False)

    def refresh_blocks(self) -> None:
        blocks = self.store.blocks_for_day(self.day)
        for key, button in self.block_buttons.items():
            todo = self.todo_lookup.get(blocks.get(key))
            if not todo:
                button.set_task_text("")
                button.setProperty("filled", False)
                button.setProperty("life", False)
            else:
                button.set_task_text(f"{todo.subject_name}\n{todo.title}")
                button.setProperty("filled", True)
                button.setProperty("life", todo.subject_kind == "other")
            button.style().unpolish(button)
            button.style().polish(button)

    def refresh_single_block(self, block_key: str, todo_id: int) -> None:
        button = self.block_buttons.get(block_key)
        todo = self.todo_lookup.get(todo_id)
        if not button or not todo:
            return
        button.set_task_text(f"{todo.subject_name}\n{todo.title}")
        button.setProperty("filled", True)
        button.setProperty("life", todo.subject_kind == "other")
        button.style().unpolish(button)
        button.style().polish(button)

    def refresh_stats(self) -> None:
        self.clear_layout(self.stats_container)
        records = self.store.timer_records_for_day(self.day)
        totals = defaultdict(int)
        life_total = 0
        paused_count = 0
        for record in records:
            if record["subject_kind"] == "other":
                life_total += record["seconds"]
            else:
                totals[record["subject_name"]] += record["seconds"]
            if record["event_type"] in {"paused", "deferred"}:
                paused_count += 1

        if not totals:
            empty = QLabel("오늘 저장된 공부 시간이 아직 없습니다.")
            empty.setObjectName("MutedText")
            empty.setWordWrap(True)
            self.stats_container.addWidget(empty)
        else:
            for subject, seconds in sorted(totals.items(), key=lambda item: item[1], reverse=True):
                self.stats_container.addWidget(Pill(f"{subject} · {round(seconds / 60)}분", "blue"))

        self.stats_container.addWidget(Pill(f"생활 일정 {round(life_total / 60)}분", "green"))
        self.stats_container.addWidget(Pill(f"중단/미룸 {paused_count}회", "orange"))
        self.stats_container.addStretch(1)

    def generate_report(self) -> str:
        markdown = build_markdown_report(
            self.day,
            self.store.todos_for_day(self.day),
            self.store.timer_records_for_day(self.day),
            self.store.brain_dump(self.day),
        )
        path = save_markdown_report(self.day, markdown)
        QMessageBox.information(self, "리포트 생성", f"Markdown 리포트를 생성했습니다.\n{path}")
        return markdown

    def show_ai_feedback(self) -> None:
        markdown = build_markdown_report(
            self.day,
            self.store.todos_for_day(self.day),
            self.store.timer_records_for_day(self.day),
            self.store.brain_dump(self.day),
        )
        QMessageBox.information(self, "AI 피드백", self.ai.generate_feedback(markdown))

    def status_label(self, status: str) -> str:
        return {"open": "진행 전", "done": "완료", "deferred": "미룸"}.get(status, status)

    def clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
