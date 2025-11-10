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
                {"title": "TaskB", "description": " "},
                {"title": "TaskD", "description": " "},
                {"title": "TaskE", "description": " "},
                {"title": "TaskF", "description": " "},
                {"title": "TaskG", "description": "Omochikun!?!?"}
            ],
            "完了済みのタスク": [
                {"title": "TaskO", "description": " "}
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

    def add_task(self, section:str, title: str, description: str = "") -> bool:
        """タイトルと説明を受け取り、"現在のタスク" に新規タスクを追加してUIを更新します。

        戻り値: 追加に成功したら True、タイトルが空などで追加しなかった場合は False。
        """
        if title is None:
            return False
        t = title.strip()
        if not t:
            return False

        d = description if description is not None else ""

        # 現在のタスクリストがなければ作成
        if section not in self.tasks or not isinstance(self.tasks[section], list):
            self.tasks[section] = []

        self.tasks[section].append({"title": t, "description": d})

        # UI 再描画（失敗してもロジックは成功扱い）
        try:
            self.refresh_ui()
        except Exception:
            pass

        return True
    
    def delete_task(self, section: str, old_title: str) -> bool:
        """指定されたセクションからタイトルが old_title のタスクを削除してUIを更新します。

        戻り値: 削除に成功したら True、タスクが見つからなかった場合は False。
        """
        if section not in self.tasks or not isinstance(self.tasks[section], list):
            return False

        for i, task in enumerate(self.tasks[section]):
            if task["title"] == old_title:
                del self.tasks[section][i]

                # UI 再描画（失敗してもロジックは成功扱い）
                try:
                    self.refresh_ui()
                except Exception:
                    pass

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
        if title == "現在のタスク":
            # 2カラムのグリッドをローカルに作る（再描画時の古い参照を残さない）
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

    def _clear_layout(self, layout):
        """Recursively remove widgets and child layouts from a layout."""
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
        """Rebuild the main sections from self.tasks and request a repaint.

        This keeps the top-level layout object if present, clears its contents,
        and re-adds the two sections based on current task data.
        """
        main_layout = self.layout()
        if main_layout is None:
            main_layout = QHBoxLayout()
            self.setLayout(main_layout)
        else:
            # remove existing widgets/layouts from the main layout
            self._clear_layout(main_layout)

        # Recreate sections
        current_section = self._create_section(
            "現在のタスク", QColor(200, 255, 200), self.tasks.get("現在のタスク", [])
        )
        current_section.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_layout.addWidget(current_section)
        main_layout.setStretch(main_layout.indexOf(current_section), 2)

        done_section = self._create_section(
            "完了済みのタスク", QColor(200, 200, 255), self.tasks.get("完了済みのタスク", [])
        )
        done_section.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_layout.addWidget(done_section)
        main_layout.setStretch(main_layout.indexOf(done_section), 1)

        # Ensure widget updates
        self.update()

class Task(typing.TypedDict):
    title:str
    description:str

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Shibarania()
    window.show()
    try:
        while True:
            s_ot = input("section, old title:").split(maxsplit=1)
            if len(s_ot) < 2:
                print("入力例: 現在のタスク TaskB")
                continue
            s, ot = s_ot
            t_d = input("new title and description:").split(maxsplit=1)
            if len(t_d) < 2:
                print("入力例: example description")
                continue
            t, d = t_d
            if window.delete_task(s, ot):
                if window.add_task(s, t, d):
                    print("編集しました")
                else:
                    print("追加できませんでした")

            else:
                print("タスクが見つかりません")
    except KeyboardInterrupt:
        pass
    print("Exiting...")
    sys.exit(app.exec())
