from controller.includes.dirProxyModel import DirProxyModel
from view.mainWindow import MainWindow
from model.datReader import datReader
from PyQt5.QtWidgets import QFileDialog, QAbstractItemView, QFileSystemModel, QComboBox
from PyQt5.QtCore import QDir


class spectatorController():
    """
    This code defines a class `spectatorController` that manages the interaction between a GUI and various widgets. 
    It initializes the class with given arguments, sets up event handlers, and connects signals and slots for 
    different interactions with the GUI elements. It also includes methods to handle events like clicking on a 
    list view item, moving a line on a plot, updating the vertical line position on all plots, aligning X and Y
    ranges on all plots, and updating the y-axis range of the graph items in the spectrogram boxes based on histogram levels.
    """
    def __init__(self, arguments):
        """
        Initialize the class with the given arguments.
        @param arguments - The arguments to initialize the class with. 
        This method sets up the main window, connects signals and slots for various widgets, 
        and sets up event handlers for different interactions with the GUI elements. 
        It also checks the number of arguments and sets the path in the file widget accordingly.
        """
        self.window = MainWindow()
        #self.window.resize(QDesktopWidget().availableGeometry(self.window).size() * 0.7)
        
        self.lineShow = True
        
        self.filesWidget = self.window.getListView()
        self.spectBoxWidget = self.window.getSpectBoxesWidget()
        
        self.filesWidget.listview.doubleClicked.connect(self.listview_clicked)
        self.filesWidget.button.clicked.connect(self.filesWidgetButton_clicked)
        self.spectBoxWidget.button.clicked.connect(self.spectatorWidgetButton_clicked)
        
        self.spectBoxes = self.spectBoxWidget.getSpectBoxes()
        for spectBox in self.spectBoxes:
            spectBox.plotWidget.getLine().sigPositionChanged.connect(self.line_moved)
            spectBox.plotWidget.getLinearRegion().sigRegionChanged.connect(self.linearRegion_moved)
            spectBox.plotWidget.scene().sigMouseMoved.connect(self.spectatorPlotMouseOver)
            spectBox.plotWidget.getPlotItem().sigRangeChanged.connect(self.plotRangeChange)
            plotWidgetViewbox = spectBox.plotWidget.getPlotItem().getViewBox()
            graphWidgetViewBox = spectBox.graphWidget.getPlotItem().getViewBox()
            graphWidgetViewBox.setXLink(plotWidgetViewbox)
            spectBox.spectrumWidget.item.sigLevelChangeFinished.connect(self.histogramRangeChanged)
        
        if(len(arguments)-1==0):
            self.directoryDialog()
        elif(QDir(arguments[1]).exists()):
            self.filesWidget.setPath(arguments[1])
            self.filesWidget.setTitle(QDir(arguments[1]).absolutePath())

    def getWindow(self):
        """
        Get the window attribute of an object.
        @return The window attribute of the object
        """
        return self.window
    
    def directoryDialog(self):
        """
        Open a dialog to allow the user to select a directory and update the path and title of the files widget accordingly.
        @return None
        """
        path = ""
        dialog = QFileDialog(self.filesWidget, windowTitle='Select directory')
        dialog.setFileMode(dialog.Directory)
        dialog.setOptions(dialog.DontUseNativeDialog)

        # find the underlying model and set our own proxy model for it
        for view in self.filesWidget.findChildren(QAbstractItemView):
            if isinstance(view.model(), QFileSystemModel):
                proxyModel = DirProxyModel(view.model())
                dialog.setProxyModel(proxyModel)
                break

        # try to hide the file filter combo
        fileTypeCombo = dialog.findChild(QComboBox, 'fileTypeCombo')
        if fileTypeCombo:
            fileTypeCombo.setVisible(False)
            dialog.setLabelText(dialog.FileType, '')

        if dialog.exec_():
            path = dialog.selectedFiles()[0]
        
        self.filesWidget.setPath(path)
        self.filesWidget.setTitle(path)
    
    def listview_clicked(self, index):
        """
        Handle the click event on a list view item. Retrieve the file path from the clicked index, read the DAT images array from the file, set the DAT images array to the spectral boxes widget, and update the title of the spectral boxes widget.
        @param self - the object itself
        @param index - the index of the clicked item in the list view
        @return None
        """
        path = self.filesWidget.fileModel.fileInfo(index).absoluteFilePath()
        datImagesArray = datReader(path).getDatImagesArray()
        spectBoxesWidget = self.getWindow().getSpectBoxesWidget()
        spectBoxesWidget.setSelfBoxesDat(datImagesArray)
        spectBoxesWidget.setTitle(self.filesWidget.fileModel.fileInfo(index).fileName())
        
    def filesWidgetButton_clicked(self):
        """
        Define a method that is called when a button is clicked. This method calls another method named `directoryDialog` on the current object.
        @return None
        """
        self.directoryDialog()
        
    def spectatorWidgetButton_clicked(self, event):
        """
        Define a method that is called when a button is clicked. This method calls another method named `directoryDialog` on the current object.
        @return None
        """
        self.lineToRegionToggle()
    
    def lineToRegionToggle(self):
        self.lineShow = not self.lineShow
        spectBoxes = self.spectBoxWidget.getSpectBoxes()
        if(self.lineShow):
            for spectBox in spectBoxes:
                spectBox.plotWidget.getLine().show()
                spectBox.plotWidget.getLinearRegion().hide()
        else:
            for spectBox in spectBoxes:
                spectBox.plotWidget.getLine().hide()
                spectBox.plotWidget.getLinearRegion().show()
        

    
    def line_moved(self,line):
        """
        Update the position of a line on a plot and redraw the plot with the new line position.
        @param line - the line being moved.
        """
        spectBoxes = self.getWindow().getSpectBoxesWidget().getSpectBoxes()
        for spectBox in spectBoxes:
            otherline = spectBox.plotWidget.getLine()
            graphWidgetPlot = spectBox.graphWidget
            plotData = spectBox.plotWidget.getPlotData()
            plotWidgetViewbox = spectBox.plotWidget.getPlotItem().getViewBox()
            currentRange = plotWidgetViewbox.viewRange()
            rangeValues = plotData[int(currentRange[1][0]):int(currentRange[1][1]),int(currentRange[0][0]):int(currentRange[0][1])+1]
            
            lineY = int(line.y())
            if otherline != line:
                otherline.setY(lineY)
            graphWidgetPlot.drawPlot(rangeValues,lineY=lineY-int(currentRange[1][0]))
        
        self.histogramRangeChanged()
        
        
    def linearRegion_moved(self,region):
        """
        Update the position of all the regions and redraw the plot with the new line position.
        @param region - the region being moved.
        """
        spectBoxes = self.getWindow().getSpectBoxesWidget().getSpectBoxes()
        for spectBox in spectBoxes:
            otherRegion = spectBox.plotWidget.getLinearRegion()
            graphWidgetPlot = spectBox.graphWidget
            plotData = spectBox.plotWidget.getPlotData()
            plotWidgetViewbox = spectBox.plotWidget.getPlotItem().getViewBox()
            currentRange = plotWidgetViewbox.viewRange()
            rangeValues = plotData[int(currentRange[1][0]):int(currentRange[1][1]),int(currentRange[0][0]):int(currentRange[0][1])+1]
            
            linearRegion = region.getRegion()
            if(region.getRegion()[1]-region.getRegion()[0]<2):
                linearRegion = [region.getRegion()[0],region.getRegion()[1]+2]
            else:
                linearRegion = region.getRegion()
                
            if otherRegion != region:
                otherRegion.setRegion(linearRegion)
                
            graphWidgetPlot.drawPlot(rangeValues,region=linearRegion)
        
        self.histogramRangeChanged()
        
    def spectatorPlotMouseOver(self,pos):
        """
        Update the vertical line position on all the plots. Update the label at the bottom of the page accordingly.
        @param pos - the position of the mouse
        @return None
        """
        spectBoxes = self.getWindow().getSpectBoxesWidget().getSpectBoxes()
        spectBoxesWidget = self.getWindow().getSpectBoxesWidget()
        mousePos = spectBoxes[0].plotWidget.plot.vb.mapSceneToView(pos)
        for spectBox in spectBoxes:
            spectactorVerticalLine = spectBox.plotWidget.getVerticalLine()
            graphVerticalLine = spectBox.graphWidget.getVerticalLine()
            spectactorVerticalLine.setX(mousePos.x())
            graphVerticalLine.setX(mousePos.x())
        if(self.lineShow):
            spectBoxesWidget.setLabelText(x=mousePos.x(),
                                      y=spectBoxes[0].plotWidget.getLine().y(),
                                      IValue=spectBoxes[0].plotWidget.getPlotData()[int(spectBoxes[0].plotWidget.getLine().y())][int(mousePos.x())],
                                      QValue=spectBoxes[1].plotWidget.getPlotData()[int(spectBoxes[1].plotWidget.getLine().y())][int(mousePos.x())],
                                      UValue=spectBoxes[2].plotWidget.getPlotData()[int(spectBoxes[2].plotWidget.getLine().y())][int(mousePos.x())],
                                      VValue=spectBoxes[3].plotWidget.getPlotData()[int(spectBoxes[3].plotWidget.getLine().y())][int(mousePos.x())]
                                    )
        else:
            spectBoxesWidget.setLabelText(x=mousePos.x(),
                                    y=spectBoxes[0].plotWidget.getLinearRegion().getRegion(),
                                    IValue=spectBoxes[0].plotWidget.getPlotData()[int(spectBoxes[0].plotWidget.getLinearRegion().getRegion()[0]):int(spectBoxes[0].plotWidget.getLinearRegion().getRegion()[1]),int(mousePos.x())].mean(axis=0),
                                    QValue=spectBoxes[1].plotWidget.getPlotData()[int(spectBoxes[1].plotWidget.getLinearRegion().getRegion()[0]):int(spectBoxes[1].plotWidget.getLinearRegion().getRegion()[1]),int(mousePos.x())].mean(axis=0),
                                    UValue=spectBoxes[2].plotWidget.getPlotData()[int(spectBoxes[2].plotWidget.getLinearRegion().getRegion()[0]):int(spectBoxes[2].plotWidget.getLinearRegion().getRegion()[1]),int(mousePos.x())].mean(axis=0),
                                    VValue=spectBoxes[3].plotWidget.getPlotData()[int(spectBoxes[3].plotWidget.getLinearRegion().getRegion()[0]):int(spectBoxes[3].plotWidget.getLinearRegion().getRegion()[1]),int(mousePos.x())].mean(axis=0)
                                )

    def plotRangeChange(self,affectedViewBox):
        """
        Align X and Y ranges on all the plots when zoom or range is changed.
        @param affectedViewBox - the view box that is affected by the change
        @return None
        """
        spectBoxes = self.getWindow().getSpectBoxesWidget().getSpectBoxes()
        spectBoxesWidget = self.getWindow().getSpectBoxesWidget()
        spectBoxesWidget.setLabelText(y=spectBoxes[0].plotWidget.getLine().y())
        for spectBox in spectBoxes:
            plotWidgetViewbox = spectBox.plotWidget.getPlotItem().getViewBox()
            graphWidgetViewBox = spectBox.graphWidget.getPlotItem().getViewBox()
            if affectedViewBox != plotWidgetViewbox or affectedViewBox != graphWidgetViewBox:
                plotWidgetViewbox.setRange(xRange=affectedViewBox.viewRange()[0],yRange=affectedViewBox.viewRange()[1],update=False,padding=0)
            yRangeValues = spectBox.plotWidget.getPlotData()[0][int(affectedViewBox.viewRange()[0][0]):int(affectedViewBox.viewRange()[0][1])]
            graphWidgetViewBox.setYRange(min=yRangeValues.min(),max=yRangeValues.max(),padding=0)
        
        self.histogramRangeChanged()
            
    def histogramRangeChanged(self):
        """
        Update the y-axis range of the graph items in the spectrogram boxes based on the histogram levels.
        This method is triggered when the histogram range is changed.
        @param self - the instance of the class
        @return None
        """
        spectBoxes = self.getWindow().getSpectBoxesWidget().getSpectBoxes()
        for spectBox in spectBoxes:
            graphWidgetItem = spectBox.graphWidget.getPlotItem()
            histogram = spectBox.spectrumWidget.item
            graphWidgetItem.setYRange(min=histogram.getLevels()[0],max=histogram.getLevels()[1],padding=0)