from controller.spectatorController import spectatorController
from PyQt5.QtWidgets import QApplication
import sys
import qdarkstyle
#from getWidgetColors import getWidgetColors  self.setBackground(getWidgetColors.BG_NORMAL)  ???


if __name__ == '__main__':
    """
    Initialize the application, set the style to 'Fusion', create a spectator controller, get the window from the controller, center the window, show the window, and start the application event loop.
    If the script is executed as the main program:
    - Initialize the application
    - Set the application style to 'Fusion'
    - Create a spectator controller
    - Get the window from the controller
    - Center the window
    - Show the window
    - Start the application event loop
    """
    app = QApplication(sys.argv) #generate application (to be show and run below)
    #app.setStyle('Fusion')
    dark_stylesheet=qdarkstyle.load_stylesheet_from_environment(is_pyqtgraph=True)
    app.setStyleSheet(dark_stylesheet)
    controller = spectatorController(sys.argv)
    
    window = controller.getWindow()
    window.center()
    window.show()
    
    sys.exit(app.exec())
    