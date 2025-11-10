import sys
import typing
import threading
from PyQt6.QtWidgets import QApplication, QLabel, QHBoxLayout, QVBoxLayout, QWidget, QFrame, QSizePolicy, QGridLayout
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt, pyqtSignal


class Shibarania(QWidget):
    # Console thread-safe requests into the UI thread
    request_add_task = pyqtSignal(str, str)
    request_delete_task = pyqtSignal(str)
    request_move_task = pyqtSignal(str, str)  # title, destination section

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Shibarania")
        self.setGeometry(100, 100, 800, 480)

        self.tasks = {
            "現在のタスク": [
                {"title": "TaskB", "description": " "},
                {"title": "TaskD", "description": " "},
                {"title": "TaskE", "description": " "},
                {"title": "TaskF", "description": " "},
                {"title": "TaskG", "description": "Omochikun!?!?"},
            ],
            "完了済みのタスク": [
                {"title": "TaskO", "description": " "},
            ],
        }

        # レイアウト作成
        layout = QHBoxLayout()

        # セクション作成
        current_section = self._create_section(
            "現在のタスク", QColor(200, 255, 200), self.tasks["現在のタスク"]
        )
        current_section.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(current_section, 2)

        done_section = self._create_section(
            "完了済みのタスク", QColor(200, 200, 255), self.tasks["完了済みのタスク"]
        )
        done_section.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(done_section, 1)

        self.setLayout(layout)

        # Connect signals to perform operations in the UI thread
        self.request_add_task.connect(self.add_task)
        self.request_delete_task.connect(self.delete_task)
        self.request_move_task.connect(self.move_task)

    def add_task(self, title: str, description: str = "") -> bool:
        """タイトルと説明で "現在のタスク" に追加して UI を更新する。"""
        if title is None:
            return False
        t = title.strip()
        if not t:
            return False
        d = description if description is not None else ""
        if "現在のタスク" not in self.tasks or not isinstance(self.tasks["現在のタスク"], list):
            self.tasks["現在のタスク"] = []
        self.tasks["現在のタスク"].append({"title": t, "description": d})
        try:
            self.refresh_ui()
        except Exception:
            pass
        return True

    def delete_task(self, title: str) -> bool:
        """タイトルで最初に一致するタスクをどちらかのセクションから削除し UI を更新する。"""
        if not title:
            return False
        for section in ["現在のタスク", "完了済みのタスク"]:
            tasks_list = self.tasks.get(section, [])
            for idx, task in enumerate(list(tasks_list)):
                if task.get("title") == title:
                    try:
                        del tasks_list[idx]
                    except Exception:
                        return False
                    try:
                        self.refresh_ui()
                    except Exception:
                        pass
                    return True
        return False

    def move_task(self, title: str, destination: str) -> bool:
        """タイトルでタスクを探し destination("現在のタスク" or "完了済みのタスク") へ移動する。"""
        if destination not in ("現在のタスク", "完了済みのタスク"):
            return False
        if not title:
            return False
        # Ensure destination list exists
        if destination not in self.tasks or not isinstance(self.tasks[destination], list):
            self.tasks[destination] = []
        # Search both sections
        for section in ["現在のタスク", "完了済みのタスク"]:
            tasks_list = self.tasks.get(section, [])
            for idx, task in enumerate(list(tasks_list)):
                if task.get("title") == title:
                    # If already in destination just return True (no duplicate move)
                    if section == destination:
                        return True
                    # Move
                    try:
                        moved = tasks_list.pop(idx)
                    except Exception:
                        return False
                    self.tasks[destination].append(moved)
                    try:
                        self.refresh_ui()
                    except Exception:
                        pass
                    return True
        return False

    def _create_section(self, title, color, tasks):
        section_layout = QVBoxLayout()

        title_label = QLabel(title)
        title_label.setAutoFillBackground(True)
        title_label.setPalette(self._create_palette(color))
        title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        title_label.setStyleSheet("QLabel { color : #101010; font-size : 28px; padding: 0px; }")
        title_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        section_layout.addWidget(title_label, 0, Qt.AlignmentFlag.AlignHCenter)

        if title == "現在のタスク":
            current_grid = QGridLayout()
            section_layout.addLayout(current_grid)
            row = 0
            col = 0
            for task in tasks:
                task_frame = QFrame()
                task_frame.setFrameShape(QFrame.Shape.Box)
                task_frame.setLineWidth(1)

                task_layout = QVBoxLayout()
                task_title_label = QLabel(task["title"])
                task_title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
                task_title_label.setStyleSheet("QLabel { font-weight: bold; color : #101010; font-size : 18px;}")
                task_title_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
                task_layout.addWidget(task_title_label)

                if task["description"]:
                    task_content_label = QLabel(task["description"])
                    task_content_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
                    task_content_label.setStyleSheet("QLabel { color : #101010; }")
                    task_layout.addWidget(task_content_label)

                task_frame.setLayout(task_layout)
                current_grid.addWidget(task_frame, row, col)
                col += 1
                if col >= 2:
                    col = 0
                    row += 1
        else:
            for task in tasks:
                task_frame = QFrame()
                task_frame.setFrameShape(QFrame.Shape.Box)
                task_frame.setLineWidth(1)

                task_layout = QVBoxLayout()
                task_title_label = QLabel(task["title"])
                task_title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
                task_title_label.setStyleSheet("QLabel { font-weight: bold; color : #101010; font-size : 18px;}")
                task_title_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
                task_layout.addWidget(task_title_label)

                if task["description"]:
                    task_content_label = QLabel(task["description"])
                    task_content_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
                    task_content_label.setStyleSheet("QLabel { color : #101010; }")
                    task_layout.addWidget(task_content_label)

                task_frame.setLayout(task_layout)
                section_layout.addWidget(task_frame)

        section_widget = QWidget()
        section_widget.setLayout(section_layout)
        section_widget.setAutoFillBackground(True)
        section_widget.setPalette(self._create_palette(color))
        return section_widget

    def _create_palette(self, color):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, color)
        return palette

    def _clear_layout(self, layout):
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
            elif child_layout is not None:
                self._clear_layout(child_layout)

    def refresh_ui(self):
        main_layout = self.layout()
        if main_layout is None:
            main_layout = QHBoxLayout()
            self.setLayout(main_layout)
        else:
            self._clear_layout(main_layout)

        current_section = self._create_section(
            "現在のタスク", QColor(200, 255, 200), self.tasks.get("現在のタスク", [])
        )
        current_section.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_layout.addWidget(current_section)

        done_section = self._create_section(
            "完了済みのタスク", QColor(200, 200, 255), self.tasks.get("完了済みのタスク", [])
        )
        done_section.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_layout.addWidget(done_section)

        self.update()


class Task(typing.TypedDict):
    title: str
    description: str


def _console_loop(win: Shibarania):
    while True:
        try:
            mode = input("command [add/delete/move/quit]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break
        if mode == "add":
            td = input("title and description:").split(maxsplit=1)
            if len(td) == 0:
                print("タイトルが必要です")
                continue
            title = td[0]
            desc = td[1] if len(td) > 1 else ""
            win.request_add_task.emit(title, desc)
            print("追加要求を送信しました")
        elif mode == "delete":
            title = input("title to delete: ").strip()
            if not title:
                print("タイトルが空です")
                continue
            win.request_delete_task.emit(title)
            print("削除要求を送信しました")
        elif mode == "move":
            title = input("title to move: ").strip()
            if not title:
                print("タイトルが空です")
                continue
            dest = input("destination [現在のタスク/完了済みのタスク]: ").strip()
            if dest not in ("現在のタスク", "完了済みのタスク"):
                print("destination が不正です")
                continue
            win.request_move_task.emit(title, dest)
            print("移動要求を送信しました")
        elif mode == "quit":
            inst = QApplication.instance()
            if inst is not None:
                inst.quit()
            break
        else:
            print("不明なコマンドです: add/delete/move/quit から選んでください")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    window = Shibarania()
    window.show()

    # Start console loop in a daemon thread so closing the window ends the process
    threading.Thread(target=_console_loop, args=(window,), daemon=True).start()

    sys.exit(app.exec())
