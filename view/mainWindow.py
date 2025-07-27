from .fileListWidget import FileListWidget
from .spectatorWidget import spectatorWidget
from PyQt5.QtWidgets import QMainWindow, QHBoxLayout, QWidget, QDesktopWidget
class MainWindow(QMainWindow):
    """
    A class representing the main window of the SPECtator app.
    @param QMainWindow - The main window class in PyQt.
    @method __init__ - Initializes the main window with a layout, sets the window title, creates a list view and a spectator widget, and sets the central widget.
    @method getListView - Returns the list view widget.
    @method getSpectBoxesWidget - Returns the spectator boxes widget.
    @method center - Centers the main window on the screen.
    """
    def __init__(self, *args, **kwargs):
        """
        Initialize the SPECtator application with a file list widget and a spectator widget.
        @param *args - Variable length argument list.
        @param **kwargs - Arbitrary keyword arguments.
        @return None
        """
        super().__init__(*args, **kwargs)
        layout = QHBoxLayout()
        self.setWindowTitle('SPECtator app')
        self.listview = FileListWidget(' ')
        self.spectBoxesWidget = spectatorWidget(' ')
        
        layout.addWidget(self.listview)
        layout.addWidget(self.spectBoxesWidget)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        widget = QWidget()
        widget.setLayout(layout)
        #widget.setGeometry(0,0,700,700)
        self.setCentralWidget(widget)
        self.center()
        self.show()
        
    def getListView(self):
        """
        Retrieve the list view associated with the current object.
        @return The list view object.
        """
        return self.listview
    
    def getSpectBoxesWidget(self):
        """
        Retrieve the SpectBoxesWidget associated with the current instance.
        @return The SpectBoxesWidget.
        """
        return self.spectBoxesWidget
    
    def center(self):
        """
        Center the window on the screen.
        @return None
        """
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())