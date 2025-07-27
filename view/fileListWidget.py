from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QListView, QPushButton, QFileSystemModel
from PyQt5.QtCore import QDir

class FileListWidget(QGroupBox):
    """
    A custom widget that displays a list of files in a specified path and allows the user to open a new folder.
    @param *args - Variable length argument list.
    @param **kwargs - Arbitrary keyword arguments.
    @return A QVBoxLayout containing a listview and a button for opening a new folder.
    """
    def __init__(self, *args, **kwargs):
        """
        Initialize the class with a maximum width of 300. Set up a vertical layout and add a list view and a button to open a new folder. Set the initial path to the home directory. Create a file system model, filter out directories and show only files with a .dat extension in the list view. Set the root index of the list view to the path. 
        @param args - positional arguments
        @param kwargs - keyword arguments
        """
        super().__init__(*args, **kwargs)
        self.setMaximumWidth(300)
        #self.setGeometry(QRect(0,0,300,500))
        hlay = QVBoxLayout(self)
        self.listview = QListView()
        hlay.addWidget(self.listview)
        self.button = QPushButton("Open new folder", self)
        hlay.addWidget(self.button)
        
        
        path = QDir.homePath()

        self.fileModel = QFileSystemModel()
        self.fileModel.setFilter(QDir.NoDotAndDotDot |  QDir.Files)
        self.fileModel.setNameFilters(['*.dat'])
        self.fileModel.setNameFilterDisables(False)
        self.listview.setModel(self.fileModel)
        self.listview.setRootIndex(self.fileModel.setRootPath(path))
        
    def setPath(self,path):
        """
        Set the path for the file model and update the root index of the list view.
        @param path - The new path to set
        @return None
        """
        self.listview.setRootIndex(self.fileModel.setRootPath(path))