# Copyright (C) 2016 Noah Meltzer
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


"""
### BEGIN NODE INFO
[info]
name = Leiden Vitals Gui
version = 1.1.0
description = Monitors Leiden Devices

### END NODE INFO
"""
import NGui				# Handles all gui operations. Independent of labrad.

#from PyQt4 import QtCore, QtGui

from Device import Device
from multiprocessing.pool import ThreadPool
import threading
import labrad
import labrad.units as units
from dataChestWrapper import *
class nViewer:
	gui = None
	devices =[]
	def __init__(self, parent = None):
		# Establish a connection to labrad
		try:
			cxn = labrad.connect();
		except:
			print("Please start the labrad manager")
		##################################################################
		# How to Use nViewer:	 
		################################################################
		#	nViewer can be used with any labrad server, and given a new device class (it must have a "prompt" function), anything else.
		#	It is meant to be a tool which allows much, much easier creation of straightforward gui's.
		#	To create you own, make a new class in which you establish a connection to labrad, create new
		#	device instances, and start the gui.
		#
		#
		# Here are the steps to create your own gui.
		# 1. Establish LabRad connection
		#		cxn = labrad.connect()
		#
		# 2. Create Device
		#		 ex = Device("NAME OF LABRAD SERVER", 
		#						 "TITLE TO BE SHOWN ON GUI", 
		#						 [LIST OF FIELDS TO BE DISPLAYED ON GUI],
		#						 [LIST OF THOSE FIELDS' CORRESPONDING SERVER SETTINGS], 
		#						 [ARGUMENTS TO BE PASSED TO THOSE SETTINGS]
		#						 CONNECTION REFERENCE,
		#						 ["LIST","OF","BUTTONS"], 
		#						 ["SETTINGS", "ACTIVATED", "BY BUTTONS"], 
		#						 ["ALERT TO BE DISPLAYED WITH EACH BUTTON PRESS", "NONE IF NO MESSAGE"]
		#						 ["ARGUMENTS PASSED TO THE SETTINGS TRIGGERED BY THE BUTTONS"]
		#						 "SELECT DEVICE COMMAND (OPTIONAL FOR SERVERS THAT DO NOT REQUIRE DEVICE SELECTION)", 
		#						 "DEVICE NUMBER")
		# 3. Start nGui and name the window
		# 		self.gui = NGui.NGui()
		#		self.gui.startGui(self.devices, Window title)
		#
		# 4. Initialize nViewer OUTSIDE OF THE CLASS
		#		viewer = nViewer()	
		#		viewer.__init__()
		###################################################################
		
		# This is my test server
		testDevice = Device("my_server", "Random Number Generator", ["Random Pressure", "Random Temperature"], ["pressure", "temperature"], [None, None], cxn, ["Pressure","Temperature"], ["pressure", "temperature"], ["You are about to get a random pressure", None],[None,None])
		self.devices.append(testDevice)
		#Compressor = Device("cp2800_compressor", "Compressor",[)
		# Omega Temperature Monitor server
		Temperature = Device("omega_temp_monitor_server","External Water Temperature",["Temperature"], ["get_temperature"],[None], cxn, None, None, None, [None],"select_device", 0)
		self.devices.append(Temperature)
		# Omega Flow Meter
		Flow = Device("omega_ratemeter_server","External Water Flow Rate", ["Flow Rate"], ["get_rate"], [None], cxn, None, None, None, "select_device", 0)
		self.devices.append(Flow)
		# Pfeiffer Vacuum Monitor
		testDevice = Device("pfeiffer_vacuum_maxigauge", "Pressure Monitor", [None, None, None, "Pressure OVC","Pressure IVC", "Still Pressure"], ["get_pressures"], [None], cxn, None, None, None,[None],"select_device", 0)
		self.devices.append(testDevice)
		
		# Start the datalogger. This line can be commented out if no datalogging is required.
		self.chest = dataChestWrapper(self.devices)
		
		# Create the gui
		self.gui = NGui.NGui()
		self.gui.startGui(self.devices, 'Leiden Gui', 'Leiden Data')
		
		
# In phython, the main class's __init__() IS NOT automatically called
viewer = nViewer()	
viewer.__init__()
