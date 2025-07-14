import sys
import typing
from PyQt6.QtWidgets import QApplication, QLabel, QHBoxLayout, QVBoxLayout, QWidget, QFrame, QSizePolicy
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout

class Shibarania(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Shibarania")
        self.setGeometry(100, 100, 800, 480)
        
        self.tasks = {
            "現在のタスク": [
                {"title": "Task B", "description": " "},
                {"title": "Task D", "description": " "},
                {"title": "Task E", "description": " "},
                {"title": "Task F", "description": " "},
                {"title": "Task G", "description": "Omochikun!?!?"}
            ],
            "完了済みのタスク": [
                {"title": "Task O", "description": " "}
            ]
        }

        # レイアウト作成
        layout = QHBoxLayout()

        # セクション作成
        # 「現在のタスク」セクション（幅2）
        current_section = self._create_section(
            "現在のタスク",
            QColor(200, 255, 200),
            self.tasks["現在のタスク"]
        )
        current_section.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(current_section, 2)

        # 「完了済みのタスク」セクション（幅1）
        done_section = self._create_section(
            "完了済みのタスク",
            QColor(200, 200, 255),
            self.tasks["完了済みのタスク"]
        )
        done_section.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(done_section, 1)
        
        self.setLayout(layout)
    
    def edit_task(self, section, old_title, new_title, new_description):
        if section in self.tasks:
            for task in self.tasks[section]:
                if task["title"] == old_title:
                    task["title"] = new_title
                    task["description"] = new_description
                    return True
        return False

    def _create_section(self, title, color, tasks):
        # セクション全体のレイアウト
        section_layout = QVBoxLayout()

        # タイトルラベル
        title_label = QLabel(title)
        title_label.setAutoFillBackground(True)
        title_label.setPalette(self._create_palette(color))
        title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        title_label.setStyleSheet("QLabel { color : #101010; font-size : 28px; padding: 0px; }")
        title_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        section_layout.addWidget(title_label, 0, Qt.AlignmentFlag.AlignHCenter)

        # タスクごとのフレームを追加
        for task in tasks:
            task_frame = QFrame()
            task_frame.setFrameShape(QFrame.Shape.Box)
            task_frame.setLineWidth(1)

            # 2カラムレイアウト用のQGridLayoutを現在のタスク用に用意
            if title == "現在のタスク":
                if not hasattr(self, "_current_tasks_grid"):
                    self._current_tasks_grid = QGridLayout()
                    section_layout.addLayout(self._current_tasks_grid)
                    self._current_task_row = 0
                    self._current_task_col = 0

                task_layout = QVBoxLayout()
                # 以下は元のコード
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
                self._current_tasks_grid.addWidget(task_frame, self._current_task_row, self._current_task_col)
                self._current_task_col += 1
                if self._current_task_col >= 2:
                    self._current_task_col = 0
                    self._current_task_row += 1
                continue  # 既に追加したので下の処理はスキップ

            # それ以外のセクションは従来通り
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

        # セクションウィジェット
        section_widget = QWidget()
        section_widget.setLayout(section_layout)
        section_widget.setAutoFillBackground(True)
        section_widget.setPalette(self._create_palette(color))

        return section_widget

    def _create_palette(self, color):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, color)
        return palette

class Task(typing.TypedDict):
    title:str
    description:str

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Shibarania()
    window.show()
    while True:
        s,ot = input("section, old title:").split()
        t,d = input("new title and description:").split()
        Shibarania.edit_task(Shibarania, s,ot,t,d)
    app.exec()
