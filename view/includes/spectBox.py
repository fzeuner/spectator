from PyQt5.QtWidgets import QGroupBox,QHBoxLayout,QWidget
from view.includes.spectator import SPECtator
from view.includes.histogram import histogramWidget
from view.includes.meanGraph import meanGraph

class spectBox(QGroupBox):
    """
    Create a custom QGroupBox for displaying spectroscopy data.
    @param title - The title of the QGroupBox
    @return A QGroupBox with spectroscopy data visualization widgets.
    """
    def __init__(self,title):
        super().__init__(title)
        layout = QHBoxLayout()
        self.plotWidget = SPECtator()
        self.spectrumWidget = histogramWidget(self.plotWidget.getImage())
        self.graphWidget = meanGraph(self.plotWidget)
        
        
        layout.addWidget(self.plotWidget)
        layout.addWidget(self.spectrumWidget)
        layout.addWidget(self.graphWidget)
        
        layout.setSpacing(0)
        layout.setContentsMargins(10, 10, 10, 10)

        self.setLayout(layout)
