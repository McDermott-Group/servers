from PyQt4 import QtGui, QtCore
from MWeb import web
import MGrapher
from MReadout import MReadout
import math
from functools import partial
import traceback
from pprint import pprint
import numpy as np
class MDeviceContainerWidget(QtGui.QFrame):

    def __init__(self, device, parent = None):
        QtGui.QWidget.__init__(self, parent)
        device.updateSignal.connect(self.update)

        device.setContainer(self)
        
        self.nicknameLabels = []
        self.unitLabels = []
        self.lcds = []
        self.device = device
        self.dc = None
        
        grid = QtGui.QGridLayout()
        self.grid = grid
        self.setLayout(grid)
        
        self.frameSizePolicy = QtGui.QSizePolicy()
        self.frameSizePolicy.setVerticalPolicy(4)
        self.frameSizePolicy.setHorizontalPolicy(QtGui.QSizePolicy.Preferred)
        self.setSizePolicy(self.frameSizePolicy)
        self.setStyleSheet("background: rgb(52, 73, 94)")
        self.setFrameShape(QtGui.QFrame.Panel)
        self.setFrameShadow(QtGui.QFrame.Plain)
        self.setLineWidth(web.ratio)
        grid.setSpacing(10)
        grid.setColumnStretch(0,1)
        
        self.font = QtGui.QFont()
        self.font.setBold(False)
        self.font.setWeight(50)
        self.font.setKerning(True)
        self.font.setPointSize(12)
        
        self.fontBig = QtGui.QFont()
        self.fontBig.setBold(False)
        self.fontBig.setWeight(50)
        self.fontBig.setKerning(True)
        self.fontBig.setPointSize(18)

        self.isRed = False
        titleWidget = QtGui.QLabel(device.getFrame().getTitle())
        titleWidget.setFont(self.fontBig)
        titleWidget.setStyleSheet("color:rgb(189, 195, 199);")
        grid.addWidget(titleWidget,0,0)
        
        buttonLayout = QtGui.QHBoxLayout()
        buttons = device.getFrame().getButtons()
        
        self.hidden = False
        
        for button in buttons:
            if button != []:

                button.append(QtGui.QPushButton(button[0], self))
                button[-1].setStyleSheet("color:rgb(189, 195, 199); "
                            "background:rgb(70, 80, 88)")
                button[-1].setFont(self.font)   
                buttonLayout.addWidget(button[-1])
                button[-1].clicked.connect(partial(device.prompt, button))

        grid.addLayout(buttonLayout, 0, 1, 1 , 2)
        
        self.nicknames = device.getFrame().getNicknames()
        for i, nickname in enumerate(self.nicknames):
            if nickname != None:
                y = i+1
                label = QtGui.QLabel(nickname, self)
                label.setFont(self.font)
                label.setWordWrap(True)
                label.setStyleSheet("color:rgb(189, 195, 199);")
                grid.addWidget(label, y, 0)
                self.nicknameLabels.append(label)
                
              
                units = QtGui.QLabel('')
                grid.addWidget(units, y, 2)
                units.setFont(self.fontBig)
                self.unitLabels.append(units)
                
                #lcd = QtGui.QLCDNumber(self)
                lcd = MReadout(self)
                self.lcds.append(lcd)
                lcd.getLCD().setNumDigits(11)
                lcd.getLCD().setSegmentStyle(QtGui.QLCDNumber.Flat)
                lcd.getLCD().display("-")
                lcd.getLCD().setFrameShape(QtGui.QFrame.Panel)
                lcd.getLCD().setFrameShadow(QtGui.QFrame.Plain)
                lcd.getLCD().setLineWidth(web.ratio)
                lcd.getLCD().setMidLineWidth(100)
                lcd.getLCD().setStyleSheet("color:rgb(189, 195, 199);\n")
                lcd.getLCD().setFixedHeight(web.scrnHeight / 30)
                lcd.getLCD().setMinimumWidth(web.scrnWidth / 7)
                lcd.setLabelSize(20)
                lcdHBox = QtGui.QHBoxLayout()
                lcdHBox.addStretch(0)
                lcdHBox.addWidget(lcd)

                grid.addLayout(lcdHBox, y, 1)
        self.topHBox = QtGui.QHBoxLayout()
        yPos = len(self.nicknames)
        grid.addLayout(self.topHBox, yPos+1, 0, yPos+1, 3)
        if device.getFrame().isPlot():
            self.dc = MGrapher.mGraph(device)
            yPos = len(self.nicknames)+2
            device.getFrame().setPlot(self.dc)
            grid.addWidget(self.dc, yPos,0,yPos,3)
        
        self.bottomHBox = QtGui.QHBoxLayout()
      
          
        grid.addLayout(self.bottomHBox, yPos+1, 0, yPos+1, 3)
        
    def getBottomHBox(self):
        return self.BottomHBox
    def getTopHBox(self):
        return self.topHBox
    def addParameter(self, param):
        label = QtGui.QLabel('Untitled', self)
        lcd = QtGui.QLCDNumber(self)
        units = QtGui.QLabel('')
        if (not self.device.getFrame().isParamVisible(param)):
            lcd.hide()
            label.hide()
            units.hide()
        label.setFont(self.font)
        label.setWordWrap(True)
        label.setStyleSheet("color:rgb(189, 195, 199);")
        self.grid.addWidget(label,self.grid.rowCount(), 0)
        self.nicknameLabels.append(label)
        
      
       
        self.grid.addWidget(units, self.grid.rowCount()-1, 3)
        
        units.setFont(self.fontBig)
        self.unitLabels.append(units)
     
        self.lcds.append(lcd)
        lcd.setNumDigits(11)
        lcd.setSegmentStyle(QtGui.QLCDNumber.Flat)
        lcd.display("-")
        lcd.setFrameShape(QtGui.QFrame.Panel)
        lcd.setFrameShadow(QtGui.QFrame.Plain)
        lcd.setLineWidth(web.ratio)
        lcd.setMidLineWidth(100)
        lcd.setStyleSheet("color:rgb(189, 195, 199);\n")
        lcd.setFixedHeight(web.scrnHeight / 30)
        lcd.setMinimumWidth(web.scrnWidth / 7)
        lcdHBox = QtGui.QHBoxLayout()
        lcdHBox.addStretch(0)
        lcdHBox.addWidget(lcd)

        self.grid.addLayout(lcdHBox, self.grid.rowCount()-1, 1)

        if self.dc != None:
            self.grid.removeWidget(self.dc)
            self.grid.addWidget(self.dc, self.grid.rowCount(), 0, 1, 3)
        
    def visible(self, show = None):
        if self.hidden:
            self.show()
            self.hidden = False
            #print "showing"
        else:
            self.hide()
            self.hidden = True
            #print "hidden"
    def update(self):
        #print "updating container of", self.device
        frame = self.device.getFrame()
        
        #print "updating data 1",self.device.getFrame().getTitle()

        #print "updating data 2",self.device.getFrame().getTitle()
        if self.device.getFrame().getPlot() == None and\
                self.device.getFrame().isPlot():
            self.dc = MGrapher.mGraph(self.device)
            yPos = len(self.nicknames)+2
            self.device.getFrame().setPlot(self.dc)
            self.grid.addWidget(self.dc, yPos,0,yPos,3)
            
        if self.device.getFrame().isPlot() and \
                self.device.getFrame().getDataSet() != None and\
                self.device.getFrame().getPlot() != None:
           
            #print "device container: device:", self.device
            self.device.getFrame().getPlot().plot(time = 'last_valid')
        if not frame.isError():
           
               
                nicknames = self.device.getNicknames()
                parameters = self.device.getParameters()
                while len(nicknames) > len(self.lcds):
                        #print "device:", self.device
                       #print "readings:", readings
                        #print "len(self.lcds:)", len(self.lcds)
                        #print "nicknames:", self.device.getFrame().nicknames
                        difference = len(readings)- len(self.lcds)
                        #print "difference:", difference
                        self.addParameter(self.device.getFrame().nicknames[-difference])
                        
                
                #print "nicknames:", self.device.getFrame().nicknames
              
                for y, key in enumerate(self.device.getFrame().getParameters().keys()):
                    param = self.device.getFrame().getParameter(key)
                    #pprint(param)
                    #print "setting yellow"
                    #self.lcds[y].setStyleSheet("color:rgb(189, 100, 5);\n")
                    if (self.device.getFrame().isParamVisible(key)):
                        #print self.device.isOutOfRange(key)
                        if self.device.isOutOfRange(key) and not self.isRed:
                            #print "turning it red", self.device, key
                            self.lcds[y].getLCD().setStyleSheet("color:rgb(210, 100, 10);\n")
                            self.isRed = True
                        elif self.isRed:
                            #print "turning it white"
                            self.lcds[y].getLCD().setStyleSheet("color:rgb(189, 195, 199);")
                            self.isRed = False
                        try:
                            precision = self.device.getPrecision(key)
                            #print self.device, key, "precision:", precision
                            
                            #print "precision:", precision
                            if precision is not None:
                                format = "%." + str(int(precision)) + "f"
                            else:
                                format = "%f"
                            #print "readings:",param['reading']
                            if type(param['reading']) is float or \
                               type(param['reading']) is np.float64:
                                   
                                #print "it is a float"
                                
                                if not math.isnan(param['reading']):
                                    self.lcds[y].display(format % param['reading'])
                            else:
                                #print "not a float", type(param['reading'])
                                self.lcds[y].display(param['reading'])
                        except:
                            traceback.print_exc()
                        if len(self.unitLabels)>y:
                            unit = frame.getUnit(key)
                            #print "DEVICE CONTAINER WIDGET:", unit
                            if unit != None:
                                self.unitLabels[y].setText(str(unit))
                    else:
                        self.lcds[y].hide()
                        self.nicknameLabels[y].hide()
                        self.unitLabels[y].hide()

