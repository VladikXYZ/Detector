import sys
from PyQt6.QtWidgets import QApplication
import gui2  # Imports the new PyQt gui file

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = gui2.DetectorWindow()
    window.show()
    sys.exit(app.exec())