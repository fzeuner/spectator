from view.includes.spectBox import spectBox
from PyQt5.QtWidgets import QLabel, QGroupBox, QVBoxLayout, QPushButton
from numpy import zeros_like


"""
   Create a custom widget for displaying spectrum boxes with polarisation data.
   @param title - The title of the widget
   @method getSpectBoxes - Retrieve the spectrum boxes associated with an instance of the class.
   @method createSpectBoxes - Create spectrum boxes for displaying different types of polarisation.
   @method setSelfBoxesDat - Set the data for the spectrum boxes based on the provided data images array.
   @param datImagesArray - The array of data images
   @method setLabelText - Set the text of a label with formatted values for x, y, IValue, QValue, UValue, and VValue.
"""
class spectatorWidget(QGroupBox):
    def __init__(self,title) -> None:
        """
        Initialize the spectator widget with a given title and set up its layout and components.
        @param title - The title of the widget
        @return None
        """
        super(spectatorWidget,self).__init__(title)
        self.setMinimumWidth(1400)
        self.spectBoxes = []
        self.spectBoxesLayout = QVBoxLayout()

        self.createSpectBoxes()
        self.label = QLabel()
        self.setLabelText()
        self.spectBoxesLayout.addWidget(self.label)  
        
        self.button = QPushButton("Switch to Average Region", self)
        self.spectBoxesLayout.addWidget(self.button)
        
        self.spectBoxesLayout.setContentsMargins(5, 5, 5, 5)       
        self.setLayout(self.spectBoxesLayout)

    def getSpectBoxes(self):
        """
        Retrieve the spectrum boxes associated with an instance of a class.
        @return The spectrum boxes.
        """
        return self.spectBoxes
    
    def createSpectBoxes(self):
        """
        Create spectrum boxes for displaying different types of polarisation.
        @return None
        """
        titles = ["Intensity","Q/I", "U/I", "V/I"]
        for x in range(4):
            self.spectBoxes.append(spectBox(titles[x]))
            self.spectBoxesLayout.addWidget(self.spectBoxes[x])  
    
    def setSelfBoxesDat(self, datImagesArray):
        """
        Set the data for the self boxes based on the provided data images array.
        @param self - the object itself
        @param datImagesArray - the array of data images
        @return None
        """
        for idx, spectBox in enumerate(self.spectBoxes):
            if(datImagesArray[idx].shape!=datImagesArray[0].shape):
                datImagesArray[idx] = zeros_like(datImagesArray[0])
            spectBox.plotWidget.setData(datImagesArray[idx])
            spectBox.plotWidget.img.setImage(datImagesArray[idx])
            spectBox.plotWidget.plot.setLimits(xMin=0, xMax=datImagesArray[idx].shape[1], yMin=0, yMax=datImagesArray[idx].shape[0])
            spectBox.plotWidget.plot.autoRange(padding=0)
            
            spectBox.plotWidget.getVerticalLine().setPos(datImagesArray[idx].shape[1]/2)            
            spectBox.plotWidget.getLine().setPos(datImagesArray[idx].shape[0]/2)
            spectBox.plotWidget.getLine().setBounds([0,datImagesArray[idx].shape[0]-0.001])
            
            spectBox.plotWidget.getLinearRegion().setRegion([(datImagesArray[idx].shape[0]/2)+(datImagesArray[idx].shape[0]/10),(datImagesArray[idx].shape[0]/2)-(datImagesArray[idx].shape[0]/10)])
            spectBox.plotWidget.getLinearRegion().setBounds([0,datImagesArray[idx].shape[0]-0.001])
            
            spectBox.graphWidget.drawPlot(datImagesArray[idx],spectBox.plotWidget.getLine().y())
            
    def setLabelText(self,x=0.00,y=0.00,IValue=00.00,QValue=00.00,UValue=00.00,VValue=00.00):
        """
        Set the text of a label with formatted values for x, y, IValue, QValue, UValue, and VValue.
        @param self - the object itself
        @param x - the x value
        @param y - the y value
        @param IValue - the I value
        @param QValue - the Q value
        @param UValue - the U value
        @param VValue - the V value
        """
        if(isinstance(y,float)):
            string = "X: {:.1f}\nY: {:.1f}\nI: {:.8f} Q/I: {:.8f} U/I: {:.8f} V/I: {:.8f}"
        else:
            string = "X: {:.1f}\nY: {:}\nI: {:.8f} Q/I: {:.8f} U/I: {:.8f} V/I: {:.8f}"
        self.label.setText(string.format(x,y,IValue,QValue,UValue,VValue))
