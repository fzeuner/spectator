from scipy.io import readsav
class datReader:
    """
    A class for reading .dat files and extracting information from them.
    @param path - The path to the .dat file
    @param python_dict - Whether to convert the .dat file to a Python dictionary
    @param verbose - Whether to display verbose output during reading
    Methods:
    - getDat: Returns the entire content of the .dat file
    - getDatInfo: Returns the 'info' section of the .dat file
    - getDatImagesArray: Returns an array of images from the .dat file
    """
    def __init__(self, path = "", python_dict=True, verbose=False):
        self.path = path
        self.verbose = verbose
        self.python_dict = python_dict
        self.dat = readsav(self.path,None,self.python_dict,None,self.verbose)

    def getDat(self):
        return self.dat
    
    def getDatInfo(self):
        return self.dat['info']
    
    def getDatImagesArray(self):
        images = []
        for image in self.dat:
            if(image != "info"):
                images.append(self.dat[image])
        return images