from pyqtgraph import PlotWidget,setConfigOptions,InfiniteLine 
from numpy import array

class meanGraph(PlotWidget):
    """
    A class for creating a mean graph plot with specific configurations and attributes.
    @param PlotWidget - The base class for the meanGraph class.
    @method __init__ - Initialize the class instance with a spectator object and set up various attributes and configurations.
    @method getImage - Return the image associated with the current instance.
    @method getPlot - Retrieve the plot from the class instance.
    @method setData - Set the data attribute of the object to the provided data.
    @method getPlotData - Retrieve the plot data stored in the object.
    @method getVerticalLine - Retrieve the vertical line attribute from the class instance.
    @method drawPlot - Draw a plot with specific data and a horizontal line at a given y-coordinate.
    """
    def __init__(self,spectator):
        """
        Initialize a class instance with a spectator object and set up various attributes and configurations.
        @param spectator - the spectator object
        @return None
        """
        super().__init__(row=0, col=0,colspan=1,rowspan=1 )
        
        self.spectator=spectator
        spectatorHorizontalLineY = spectator.getLine().y()
        spectatorPlotData = self.spectator.getPlotData()
        self.setConfigOptions=setConfigOptions(imageAxisOrder='row-major')
        self.data= array([[0, 1, 2, 3, 4, 5, 6, 7]])
        self.plot = self.getPlotItem()   
        
        
        self.verticalLine = InfiniteLine(pos=50,angle=90,pen='b',movable=False)
        self.addItem(self.verticalLine)
        
        self.drawPlot(spectatorPlotData,spectatorHorizontalLineY)

        self.plot.setMinimumHeight(100)
        self.plot.setAutoVisible(y=True)
        self.setDefaultPadding(0)
        
    def getImage(self):
        """
        This method returns the image associated with the current instance.
        @return The image associated with the current instance.
        """
        return self.img
    
    def getPlot(self):
        """
        Retrieve the plot from the class instance.
        @return The plot stored in the class instance.
        """
        return self.plot
    
    def setData(self,data):
        """
        Set the data attribute of the object to the provided data.
        @param data - the data to set
        @return None
        """
        self.data = data
    
    def getPlotData(self):
        """
        Retrieve the plot data stored in the object.
        @return The plot data stored in the object.
        """
        return self.data   
    
    def getVerticalLine(self):
        """
        Retrieve the vertical line attribute from the class instance.
        @return The vertical line attribute of the class instance.
        """
        return self.verticalLine
    
    def drawPlot(self, plotData, lineY=-1, region=[]):
        """
        Draw a plot with specific data and a horizontal line at a given y-coordinate.
        @param plotData - the data to be plotted
        @param lineY - the y-coordinate for the horizontal line
        @return None
        """
        if(lineY != -1):
            filteredPlotData = plotData[int(lineY),:]
        elif(region != []):
            filteredPlotData = plotData[int(region[0]):int(region[1]),:].mean(axis=0)
            
        self.setData(filteredPlotData)
        self.plot.plot(filteredPlotData, clear=True)
        self.setLimits(xMin=0, xMax=plotData.shape[1], yMin=filteredPlotData.min()-(filteredPlotData.min()*0.1), yMax=filteredPlotData.max()+(filteredPlotData.max()*0.1))
        self.addItem(self.verticalLine)
        self.autoRange(padding=0)