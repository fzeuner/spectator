#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jan 19 20:36:59 2023

@author: zeuner

if error about wayland: 'XDG_SESSION_TYPE=x11' in terminal
if window is closing but ipython console dies, change ipython graphics backend to "inline" 

"<br/> y={0:05}<br/>" for breaks
"""

"""
This is a test file to replace z3showred with python.

First, install all necessary modules:
conda create -n spectator python=3.8 pyqtgraph=0.13.0 pyqt scipy qdarkstyle numpy
conda activate spectator

run with >> python spectator.py

Chose directory with .dat or .sav files

"""

import numpy as np

#from pyqtgraph import DataTreeWidget, FileDialog
#import pyqtgraph.metaarray as metaarray
#from pyqtgraph.flowchart import Flowchart
#from PyQt5.QtCore import pyqtSlot


from PyQt5 import QtWidgets, QtGui
from pyqtgraph import PlotWidget, plot, mkQApp
import pyqtgraph as pg
#import sys  # We need sys so that we can pass argv to QApplication
import os
from scipy.io import readsav

from getWidgetColors import getWidgetColors
import qdarkstyle


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()

        self.setWindowTitle("My App")
        layout = QtWidgets.QHBoxLayout()
        
        layout_spec = QtWidgets.QVBoxLayout()
       
        self.tablewidget=MyTableWidget()
        self.spectator=SPECtator("I")
        self.setGeometry(300, 300, 1200, 500)
        
        layout.addWidget(self.tablewidget,1)
        layout_spec.addWidget(self.spectator,4)
        self.xylabel=QtWidgets.QLabel()
        self.xylabel.setText("test.......")
       
        layout_spec.addWidget(self.spectator,4)
        layout_spec.addWidget(self.xylabel)
        layout.addLayout(layout_spec)
        container = QtWidgets.QWidget()
        container.setLayout(layout)
    
        self.mouseProxy = pg.SignalProxy(self.spectator.img.scene().sigMouseMoved,
                                          rateLimit=60, slot=self.mouse_moved)
             
        self.setCentralWidget(container)
        
        self.tablewidget.tab1.listWidget.itemClicked.connect(self.clicked)
             
    def clicked(self, item):
               #complicated re-finding file name
               item_number=int(((item.text().split(' '))[0]).split('.')[0])-1
               file_name=(item.text().split(' '))[1]
               data=load_zimpol_data(self.tablewidget.tab1.selected_directories[item_number]+
                                     '/'+file_name)
              
               self.spectator.data=data
               self.spectator.updateData()
               #print(self.tablewidget.tab1.selected_directories[item_number])
               #QtWidgets.QMessageBox.information(self, "ListWidget", 
               #"ListWidget: " + file_name)
               
    def mouse_moved(self, evt):
             """Update crosshair when mouse is moved"""
             pos = evt[0]
             if self.spectator.img.sceneBoundingRect().contains(pos):
                 mousePoint = self.spectator.p1.vb.mapSceneToView(pos)
                 if int(mousePoint.x()) > 0 and int(mousePoint.y()) > 0:
                  self.xylabel.setText(
                     "x={0:05}".format(int(mousePoint.x())) +
                     " y={0:05} ".format(int(mousePoint.y())) +
                     self.spectator.title+"={0:05.5f}".format(\
                         self.spectator.data[ int(mousePoint.y()-1),int(mousePoint.x()-1) ] )     
                 )
                 self.spectator.vLine.setPos(mousePoint.x())
                 self.spectator.hLine.setPos(mousePoint.y())
        
 
        
        
def load_zimpol_data(file) :
          s = readsav(file, verbose=False,python_dict=True)
          info = s['info']
          si=s['si']
          return(si)
        
class MyTableWidget(QtWidgets.QWidget):

    def __init__(self):

        super().__init__()

        self.setWindowTitle("QTabWidget Example")

        self.resize(270, 110)

        # Create a top-level layout

        layout = QtWidgets.QVBoxLayout()

        self.setLayout(layout)

        # Create the tab widget with two tabs

        tabs = QtWidgets.QTabWidget()
        
        self.tab1=self.generalTabUI()

        tabs.addTab(self.tab1, "General")
        tabs.addTab(self.networkTabUI(), "Network")

        layout.addWidget(tabs)


    def generalTabUI(self):

        """Create the General page UI."""

        generalTab = Files()

        return generalTab


    def networkTabUI(self):

        """Create the Network page UI."""

        networkTab = QtWidgets.QWidget()

        layout = QtWidgets.QVBoxLayout()

        layout.addWidget(QtWidgets.QCheckBox("Network Option 1"))
        layout.addWidget(QtWidgets.QCheckBox("Network Option 2"))

        networkTab.setLayout(layout)

        return networkTab
        
        
class Files(QtWidgets.QWidget):
    
    directory=['']
    selected_directories=['']
    must_be_in_directory="reduced"
    excluded_file_types=["cal","dark", "ff"]
    
    def __init__(self):
        super().__init__()
        self.button = QtWidgets.QPushButton('Choose Directory')
        self.button.clicked.connect(self.handleChooseDirectories)
        self.listWidget = QtWidgets.QListWidget()
        self.directorylabel=QtWidgets.QLabel()
        self.fileinfolabel1=QtWidgets.QLabel()
        self.fileinfolabel2=QtWidgets.QLabel()
        self.directorylabel.setText('Current directory: '+self.directory[0])
        self.directorylabel.setWordWrap(True)
        self.fileinfolabel1.setText('Files sub-directory: '+self.must_be_in_directory)
        
        file_type_string=""
        for i in range(len(self.excluded_file_types)):
            file_type_string=file_type_string+" "+self.excluded_file_types[i]
        self.fileinfolabel2.setText('Excluded files: '+file_type_string)
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.listWidget)
        layout.addWidget(self.button)
        layout.addWidget(self.directorylabel)
        layout.addWidget(self.fileinfolabel1)
        layout.addWidget(self.fileinfolabel2)

    def handleChooseDirectories(self):
        list_dirs=['']
        dialog = QtWidgets.QFileDialog(self)
        dialog.setWindowTitle('Choose a directory')
        dialog.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)
        dialog.setFileMode(QtWidgets.QFileDialog.DirectoryOnly)
        for view in dialog.findChildren(
            (QtWidgets.QListView, QtWidgets.QTreeView)):
            if isinstance(view.model(), QtWidgets.QFileSystemModel):
                view.setSelectionMode(
                    QtWidgets.QAbstractItemView.ExtendedSelection)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.listWidget.clear()
            
            list_files,list_dirs=self.all_sav_files(dialog.selectedFiles(),
                                                    excludes= self.excluded_file_types,
                                                    in_dir=self.must_be_in_directory)
            show_file_list=[]
            for n,file in enumerate(list_files): # number files
                show_file_list.append(str(n+1)+'. '+file)
            self.listWidget.addItems(show_file_list)
    
        self.directory= dialog.selectedFiles()
        self.directorylabel.setText('Current directory:'+self.directory[0])
        self.selected_directories=list_dirs
        dialog.deleteLater()

        
    def all_sav_files(self, directories,excludes=[],in_dir=must_be_in_directory):
        list_of_files = []
        list_of_directories = []
        
        for root, dirs, files in os.walk(directories[0]):       
                for file in files:
                  if in_dir in root:
                      use=True
                      for exclude in excludes:
                          if exclude in file:
                              use=False
                              break
                      if use:
                            list_of_files.append(file)#os.path.join(root,file))
                            list_of_directories.append(root)
                 
        return(list_of_files,list_of_directories)     

        
        
        
class SPECtator(pg.GraphicsLayoutWidget):
    
   dummy_data = np.random.normal(size=(200, 100))
   
   #data[20:80, 20:80] += 2.
   #data = pg.gaussianFilter(data, (3, 3))
   #data += np.random.normal(size=(200, 100)) * 0.1
    
   def __init__(self, title_string):
        
       super().__init__()

   # Interpret image data as row-major instead of col-major
       self.setConfigOptions=pg.setConfigOptions(imageAxisOrder='row-major')
       self.resize(1000, 400)
       
       self.title=title_string
       self.data=self.dummy_data
   # A plot area (ViewBox + axes) for displaying the image
       self.p1 = self.addPlot(row=0, col=0,title=self.title,colspan=1,rowspan=1)
       self.p1.setLimits(xMin=0, xMax=self.data.shape[1], yMin=0, yMax=self.data.shape[0])
       self.setBackground(getWidgetColors.BG_NORMAL)
     #  self.p1.vb.setMouseEnabled(y=False) # makes user interaction a little easier
   # Item for displaying image data
       self.img=pg.ImageItem(self.data)
       self.p1.addItem(self.img)
       self.p1.setMinimumHeight(150)

   # Custom ROI for selecting an image region
       # self.roi = pg.ROI([0, 14], [6, 10])
       # #self.roi.setLimits(xMin=0, xMax=self.data.shape[1])
       # self.roi.addScaleHandle([0.5, 1], [0.5, 0.5])
       # self.roi.addScaleHandle([0, 0.5], [0.5, 0.5])
       # self.p1.addItem(self.roi)
       # self.roi.setZValue(10)  # make sure ROI is drawn above image
       
       self.lr = pg.LinearRegionItem([1, 30], bounds=[0,self.data.shape[0]], 
                                     orientation='horizontal',movable=True)
       self.p1.addItem(self.lr)
       self.center_line = pg.InfiniteLine(0.5*(self.lr.getRegion()[1]+
                                               self.lr.getRegion()[0]),angle=0, movable=False)
       self.p1.addItem(self.center_line)
       

   # # Isocurve drawing
       # self.iso = pg.IsocurveItem(level=0.8, pen='g')
       # self.iso.setParentItem(self.img)
       # self.iso.setZValue(5)

   # # Contrast/color control
       self.hist = pg.HistogramLUTItem()
       self.hist.setImageItem(self.img)
       self.hist.setMinimumHeight(250)
       self.hist.setMaximumHeight(250)
       self.hist.setMinimumWidth(30)
       self.hist.setMaximumWidth(30)
       self.addItem(self.hist)

   # # Draggable line for setting isocurve level
       # self.isoLine = pg.InfiniteLine(angle=0, movable=True, pen='g')
       # self.hist.vb.addItem(self.isoLine)
       # self.hist.vb.setMouseEnabled(y=False) # makes user interaction a little easier
       # self.isoLine.setValue(0.8)
       # self.isoLine.setZValue(1000) # bring iso line above contrast controls

   # # Another plot area for displaying ROI data
       #self.nextRow()
       self.p2 = self.addPlot(row=0, col=2,colspan=1,rowspan=1)
       self.p2.setMaximumHeight(250)
       self.p2.setMinimumHeight(10)
       self.p2.setLimits(xMin=0, xMax=self.data.shape[1])
    
       #self.resize(1000, 800)
       #self.roi.sigRegionChanged.connect(self.updatePlot)
       self.lr.sigRegionChanged.connect(self.updatePlot)


       self.hist.setLevels(self.data.min(), self.data.max())

   # # build isocurves from smoothed data
       # self.iso.setData(pg.gaussianFilter(self.data, (2, 2)))

   # # set position and scale of image
       #self.tr = QtGui.QTransform()
      # self.setTransform(self.tr.scale(0.2, 0.2).translate(-50, 0))

   
       self.updatePlot()
       # self.isoLine.sigDragged.connect(self.updateIsocurve)
       #pg.dbg()
       self.p1.setAutoVisible(y=True)
       
       #cross hair
       
       self.label = pg.LabelItem(justify='right')
       self.addItem(self.label,row=1, col=1,colspan=1,rowspan=1)

       # Create crosshair
       self.vLine = pg.InfiniteLine(angle=90, movable=False)
       self.vLine.setZValue(100)
       
       self.mirrored_vLine = pg.InfiniteLine(angle=90, movable=False)
       self.mirrored_vLine.setZValue(100)
       self.hLine = pg.InfiniteLine(angle=0, movable=False)
       self.hLine.setZValue(100)
       self.p1.addItem(self.vLine, ignoreBounds=True)
       self.p1.addItem(self.hLine, ignoreBounds=True)
       self.p2.addItem(self.mirrored_vLine, ignoreBounds=True)
       self.mouseProxy = pg.SignalProxy(self.img.scene().sigMouseMoved,
                                         rateLimit=60, slot=self.mouse_moved)

  
   def mouse_moved(self, evt):
        """Update crosshair when mouse is moved"""
        pos = evt[0]
        if self.img.sceneBoundingRect().contains(pos):
            mousePoint = self.p1.vb.mapSceneToView(pos)
            if int(mousePoint.x()) > 0 and int(mousePoint.y()) > 0:
             self.label.setText(
                # "x={0:05}".format(int(mousePoint.x())) +
                # "<br/> y={0:05}<br/> ".format(int(mousePoint.y())) +
                # self.title+"={0:05.5f}".format(self.data[ int(mousePoint.y()-1),int(mousePoint.x()-1) ] )     
                "x={0:05}".format(int(mousePoint.x())) +
                " y={0:05} ".format(int(mousePoint.y())) +
                self.title+"={0:05.5f}".format(self.data[ int(mousePoint.y()-1),int(mousePoint.x()-1) ] )     
            )
            self.vLine.setPos(mousePoint.x())
            self.mirrored_vLine.setPos(mousePoint.x())
            self.hLine.setPos(mousePoint.y())
            
   # # Callbacks for handling user interaction
   def updatePlot(self):
         #self.selected = self.roi.getArrayRegion(self.data, self.img)
         self.selected = self.lr.getRegion()
         _roi=[int(self.selected[0]),int(self.selected[1])]
         if _roi[0]-_roi[1] < 1.5: # do not average over less than one pixel
             _roi[0] = 1*_roi[1]-1
         if _roi[1] < 1.5:
             _roi[1] = 2   
         self.p2.plot(self.data[_roi[0]:_roi[1],:].mean(axis=0), clear=True)
         self.center_line.setPos(0.5*(self.lr.getRegion()[1]+
                                                 self.lr.getRegion()[0]))
         
   def updateIsocurve(self):
        self.iso.setLevel(self.isoLine.value())
        
   def updateData(self):
       # Item for displaying image data
           self.img.setImage(self.data)
           self.p1.setLimits(xMin=0, xMax=self.data.shape[1], yMin=0, yMax=self.data.shape[0])
           self.p1.autoRange() 
           self.p2.setLimits(xMin=0, xMax=self.data.shape[1])
       

       

def run_SPECtator():
        app = pg.mkQApp()
        main = MainWindow()#SPECtator2()
        
        # setup stylesheet
        #dark_stylesheet = qdarkstyle.load_stylesheet_pyqt5()
        dark_stylesheet=qdarkstyle.load_stylesheet_from_environment(is_pyqtgraph=True)
        app.setStyleSheet(dark_stylesheet)
        main.show()
        app.exec()

if __name__ == '__main__':
    run_SPECtator()

