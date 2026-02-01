import sys
from PyQt6.QtWidgets import QApplication
import gui  # Imports the new PyQt gui file

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = gui.DetectorWindow()
    window.show()
    sys.exit(app.exec())