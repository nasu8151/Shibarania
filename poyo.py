import sys
from PyQt6.QtWidgets import QApplication,QWidget,QMessageBox,QPushButton

class Madoka(QWidget):
    def __init__(self):
        super().__init__()
        
    
    def closeEvent(self,e):
        yesno = QMessageBox.question(self,'','別に、コレを閉じてしまっても構わんのだろう？')
        if yesno == QMessageBox.StandardButton.Yes:
            e.accept() # yesと答えたら閉じる
        else:
            e.ignore() # noと答えたら何も起きない

if __name__ == "__main__":
    qAp = QApplication(sys.argv)
    mado = Madoka()
    mado.show()
    qAp.exec()