from PyQt4 import QtGui, QtCore
import sys
import time
import gc
from functools import partial
from MNodes.MVirtualDeviceNode import MVirtualDeviceNode
from MNodes.MCompare import MCompare

app = QtGui.QApplication([])


class NodeGui(QtGui.QDialog):
    pipes = []
    scene = None
    def __init__(self, devices, tree, parent = None):
        super(NodeGui, self).__init__(parent)
        self.setMouseTracking(True)
        mainLayout = QtGui.QVBoxLayout()
        lbl = QtGui.QLabel()
        lbl.setText("Logic Editor")
        mainLayout.addWidget(lbl)
        
        #self.scene = QtGui.QGraphicsScene()
        if(not tree.getScene()is None):
            self.scene = tree.getScene()
        else:
            self.scene = QtGui.QGraphicsScene()
            tree.setScene(self.scene)
        self.devices = devices
        self.tree = tree
        view = QtGui.QGraphicsView(self.scene)
        view.ViewportUpdateMode(0)
        view.setInteractive(True)
        self.backgroundBrush = QtGui.QBrush(QtGui.QColor(70, 80, 88))
        view.setBackgroundBrush(self.backgroundBrush)
        
        # for device in self.devices:
            # self.scene.addItem(MNode(device, self.scene, mode = 'labrad_device'))
            # self.scene.addItem(MNode(device, self.scene, mode = 'output'))
        mainLayout.addWidget(view)
        addVirtualDeviceButton = QtGui.QPushButton("New Virtual Device")
        addVirtualDeviceButton.clicked.connect(self.addVirtualDevice)
        mainLayout.addWidget(addVirtualDeviceButton)
        
        addComparatorButton = QtGui.QPushButton("New Comparator")
        addComparatorButton.clicked.connect(self.addComparator)
        mainLayout.addWidget(addComparatorButton)
        self.setLayout(mainLayout)
    def addVirtualDevice(self):
        self.tree.addNode(MVirtualDeviceNode())
    def addComparator(self):
        self.tree.addNode(MCompare())
       # view.show()
    