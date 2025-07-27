from pyqtgraph import HistogramLUTWidget

class histogramWidget(HistogramLUTWidget):
    """
    Create a custom histogram widget that inherits from HistogramLUTWidget and initializes it with an image.
    @param image - The image to be referred in the histogram widget.
    """
    def __init__(self, image):
        super().__init__(None, image)