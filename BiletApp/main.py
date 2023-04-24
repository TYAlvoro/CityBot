import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5 import uic
import sqlite3
 

class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('BiletApp/main.ui', self)
        self.check_button.clicked.connect(self.check)

    def check(self):
        id = self.id_line.text()
        con = sqlite3.connect('templates/db/city_bot.db')
        cur = con.cursor()
        query = "SELECT text FROM members_of_event"
        ids = cur.execute(query).fetchall()
        for m in ids:
            if m[0] == int(id):
                self.error_label.setText("ID совпадает")
                break
        else:
            self.error_label.setText("Пользователь с таким id не зарегистрирован!")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec_())