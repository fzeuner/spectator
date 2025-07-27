from PyQt5.QtCore import QSortFilterProxyModel
from PyQt5.QtCore import Qt

class DirProxyModel(QSortFilterProxyModel):
    def __init__(self, fsModel):
        super().__init__()
        self.fsModel = fsModel
        self.setSourceModel(fsModel)

    def lessThan(self, left, right):
        # QFileSystemModel populates its entries with some delay, which results 
        # in the proxy model not able to do the proper sorting (usually showing 
        # directories first) since the proxy does not always "catch up" with the 
        # source sorting; so, this has to be manually overridden by 
        # force-checking the entry type of the index.
        leftIsDir = self.fsModel.fileInfo(left).isDir()
        if leftIsDir != self.fsModel.fileInfo(right).isDir():
            return leftIsDir
        return super().lessThan(left, right)

    def flags(self, index):
        flags = super().flags(index)
        # map the index to the source and check if it's a directory or not
        if not self.fsModel.fileInfo(self.mapToSource(index)).isDir():
            # if it is a directory, remove the enabled flag
            flags &= ~Qt.ItemIsEnabled
        return flags