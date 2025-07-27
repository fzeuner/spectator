from numpy import random
from pyqtgraph import ImageItem,setConfigOptions,LinearRegionItem, InfiniteLine,PlotWidget,ViewBox

# Custom widget which render the plot
class SPECtator(PlotWidget):
    """
    A class that extends PlotWidget and provides functionality for displaying an image with interactive lines.
    - __init__(): Initializes the SPECtator object with necessary configurations and adds image and lines to the plot.
    - getImage(): Returns the image associated with the object.
    - getLine(): Returns the horizontal line.
    - getVerticalLine(): Returns the vertical line.
    - getPlot(): Returns the plot object.
    - setData(data): Sets the data for the image.
    - getPlotData(): Returns the data associated with the plot.
    """
    
    def __init__(self):
        """
        Initialize the class with specific configurations and attributes for plotting.
        - Set the background color to white at row 0, column 0 with a column span of 1 and row span of 1.
        - Generate dummy data of size (200, 100).
        - Set configuration options for the image axis order.
        - Set the data attribute to the dummy data.
        - Get the plot item and set its limits based on the data shape.
        - Automatically adjust the range of the plot with no padding.
        - Create an ImageItem with the dummy data and add it to the plot.
        - Set the minimum height of the plot to 100 and enable auto visibility on the y-axis.
        - Set the default padding to 0.
        """
        super().__init__(row=0, col=0,colspan=1,rowspan=1 )
        dummy_data = random.normal(size=(200, 100))
        self.setConfigOptions=setConfigOptions(imageAxisOrder='row-major')
        self.data=dummy_data
        self.plot = self.getPlotItem()
        self.plot.setLimits(xMin=0, xMax=self.data.shape[1], yMin=0, yMax=self.data.shape[0])
        self.plot.autoRange(padding=0)
        self.img=ImageItem(self.data)
        self.plot.addItem(self.img)
        self.plot.setMinimumHeight(100)
        self.plot.setAutoVisible(y=True)
        self.setDefaultPadding(0)
        self.plot.getViewBox().setMouseMode(ViewBox.RectMode)
        self.linearRegion = LinearRegionItem(values=((self.data.shape[0]/2)+(self.data.shape[0]/10),(self.data.shape[0]/2)-(self.data.shape[0]/10)),orientation='horizontal',movable=True,clipItem=self.img,pen='b',swapMode="sort")
        self.linearRegion.hide()
        self.horizontalLine = InfiniteLine(pos=self.data.shape[0]/2,angle=0,pen='b',movable=True)
        self.verticalLine = InfiniteLine(pos=self.data.shape[1]/2,angle=90,pen='b',movable=False)
        self.addItem(self.horizontalLine)
        self.addItem(self.verticalLine)
        self.addItem(self.linearRegion)
        
    def getImage(self):
        """
        Return the image associated with this object.
        @return The image
        """
        return self.img
    
    def getLine(self):
        """
        Retrieve the horizontal line from the class instance.
        @return The horizontal line.
        """
        return self.horizontalLine
    
    def getVerticalLine(self):
        """
        Retrieve the vertical line attribute from the class instance.
        @return The vertical line attribute of the class instance.
        """
        return self.verticalLine
    
    def getLinearRegion(self):
        """
        Retrieve the horizontal line from the class instance.
        @return The horizontal line.
        """
        return self.linearRegion
    
    def getPlot(self):
        """
        Retrieve the plot from the class instance.
        @return The plot stored in the class instance.
        """
        return self.plot
    
    def setData(self,data):
        """
        Set the data attribute of the class to the provided data.
        @param data - the data to set
        @return None
        """
        self.data = data
    
    def getPlotData(self):
        """
        Retrieve the data for plotting.
        @return The data for plotting.
        """
        return self.data
    
    
    