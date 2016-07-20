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
version = 2.0.1
description = References a device
"""

# Import nGui tools
from MFrame import MFrame
import MPopUp

import labrad

import threading
import sys, traceback

sys.dont_write_bytecode = True
# The device class handles a labrad device

class Device:

	
	def __init__(self,name):
		#print("making device")
		# Get all the stuff from the constructor.
		# Has a the device made an appearance, this is so we dont alert the
		# user more than once if a device dissapears.
		self.foundDevice = False
		# self.cxn = cxn
		self.name = name
		# Nicknames of settings (the ones that show up on th Gui)
		self.nicknames=[]			
		# Device's frame
		# The device's labrad server		
		#self.serverName = serverName	
		# List of settings that the user wants run on their device
		settings=[]				
		# The actual names of the settings
		self.settingNames = []
		# Stores the actual reference to the labrad server		
		deviceServer = None	
		# True if device is functioning correctly
		self.isDevice = False			
		# Used for device.select_device(selectedDevice) setting
		self.selectedDevice = 0
		# stores the setting to select device (almost always 'select_device')
		self.setDeviceCmd = None	
		# Stores the buttons along with their parameters
		buttons = [[]]				
		# Arguments that should be passed to settings if necessary
		self.settingArgs =[]	
		self.settingResultIndices = []
		#print name, ":", yLabel
		self.frame = MFrame()
		self.frame.setYLabel(None)
		# Store the graph
		#self.plots = []
		#print "Now it is: ", self.frame.getYLabel()
		# Determine which buttons get messages
#		if(buttonMessages is not None):
		self.buttonMessages = []
		# Setup all buttons
		#if(buttonNames is not None):
		self.buttonNames = []
		self.buttonSettings = []
			#print(buttonArgs)
		self.buttons = []
			# # print "buttons before:  ", self.buttons
			# for i in range(0, len(self.buttonNames)):
				# # print(self.name)
				# # print()
				# # print(i)
				# # if(i is not 0):
				# self.buttons.append([])
				# # print(i)
				# # print(len(self.buttons))
				# self.buttons[i].append(self.buttonNames[i])
				# self.buttons[i].append(self.buttonSettings[i])
				# self.buttons[i].append(self.buttonMessages[i])
				# self.buttons[i].append(buttonArgs[i])
			# self.frame.setButtons(self.buttons)
			
			#print "Device: ", self.name
			
			#print "buttonNames: ", self.buttonNames
			#print "buttons: ", self.frame.getButtons()
		
	def setServerName(self, name):
		self.serverName = name
		
	def addParameter(self, parameter, setting, arg=None, index = None):
		if(index is None):
			index = len(self.nicknames)
		self.settingNames.append(setting)
		self.settingResultIndices.append(index)
		self.nicknames.append(parameter)
		self.settingArgs.append(arg)
		
	def connection(self, cxn):
		self.cxn = cxn
		
	def addButton(self, name, msg, setting, arg=None):
		self.buttons.append([])
		i = len(self.buttons)-1
		self.buttons[i].append(name)
		self.buttons[i].append(setting)
		self.buttons[i].append(msg)
		self.buttons[i].append(arg)
		self.frame.setButtons(self.buttons)
		#print(self.buttons)
		
	def setYLabel(self, yLbl, units = ''):
		self.frame.setYLabel(yLbl, units)
	
		
	def selectDeviceCommand(self, cmd, arg):
		self.selectedDevice = arg	
		self.setDeviceCmd = cmd	
	
	def begin(self):
		self.frame.setTitle(self.name)
		self.frame.setNicknames(self.nicknames)
		self.frame.setReadingIndices(self.settingResultIndices)
		# Connect to the device's server
		self.connect()
		# Each device NEEDS to run on a different thread 
		# than the main thread (which ALWAYS runs the gui)
		# This thread is responsible for querying the devices
		self.deviceThread = threading.Thread(target = self.Query, args=[])
		# If the main thread stops, stop the child thread
		self.deviceThread.daemon = True
		# Start the thread
		self.deviceThread.start()
		
	def addPlot(self, length = None):
		self.frame.addPlot(length)
	def connect(self):	
		'''Connect to the device'''
		#self.deviceServer = getattr(self.cxn, self.serverName)()
		try:
			# Attempt to connect to the server given the connection 
			# and the server name.
			#print(self.cxn)
		
			self.deviceServer = getattr(self.cxn, self.serverName)()
			
			# If the select device command is not none, run it.
			#print(self.deviceServer)
			if(self.setDeviceCmd is not None):
				getattr(self.deviceServer, self.setDeviceCmd)(
					self.selectedDevice)
		
			# True means successfully connected
			self.foundDevice= False
			print ("Found device: "+self.serverName)
			return True
		except labrad.client.NotFoundError, AttributeError:
			if( not self.foundDevice):
				self.foundDevice = True
				print("Unable to find device: "+self.serverName)
			self.frame.raiseError("Labrad issue")

		except:
			#print("error, server not found")
			# The nFrame class can pass an error along with a message
			self.frame.raiseError("Labrad issue")
			
			return False
		
	def getFrame(self):
		'''Return the device's frame'''
		return self.frame
		
	def prompt(self, button):
		'''If a button is clicked, handle it.'''
		try:
			# if the button has a warning message attatched
			if(self.frame.getButtons()[button][2] is not None):
				# Create a new popup
				self.warning = MPopUp.PopUp(self.frame.getButtons()
					[button][2])
				# Stop the main gui thread and run the popup
				self.warning.exec_()
				# If and only if the 'ok' button is pressed
				if(self.warning.consent):
					# If the setting associated with the button also 
					# has an argument for the setting
					if(self.frame.getButtons()[button][3] is not None):
						getattr(self.deviceServer, self.frame.getButtons()
							[button][1])(self.frame.getButtons()
							[button][4])
					# If just the setting needs to be run
					else:
						getattr(self.deviceServer, self.frame.getButtons()
							[button][1])
			# Otherwise if there is no warning message, do not make a popup
			else:
				# If there is an argument that must be passed to the setting
				if(self.frame.getButtons()[button][3] is not None):
					getattr(self.deviceServer, self.frame.getButtons()
						[button][1])(self.frame.getButtons()[button][4])
				# If not.
				else:
					getattr(self.deviceServer, self.frame.getButtons()
						[button][1])
		except:
			#print("Device not connected.")
			return
	def Query(self):
		'''Ask the device for readings'''
		# If the device is attatched.
		#print("Querying")
		
		if(not self.isDevice):
			# Try to connect again, if the value changes, then we know 
			# that the device has connected.
			if(self.connect() is not self.isDevice):
				#print("Connected to "+self.name)
				self.isDevice = True
		# Otherwise, if the device is already connected
		else:
			#print("Reading")
			try:
				readings = []	# Stores the readings
				units = []		# Stores the units
				for i in range(0, len(self.settingNames)):
					# If the setting needs to be passed arguments
					if(self.settingArgs[i] is not None):
						reading = getattr(self.deviceServer, self
							.settingNames[i])(self.settingArgs[i])
						#print type(reading)
					else:
						reading = getattr(self.deviceServer, self
							.settingNames[i])()
					# If the reading has a value and units
					if isinstance(reading, labrad.units.Value):
						#print "labrad value"
						#print reading
						# Some installations like _value, some like value
						try:
							readings.append(reading._value)
						except:
							readings.append(reading.value)
						#print(readings)
						units.append(reading.units)
					# If the reading is an array of values and units
					elif(isinstance(reading, labrad.units.ValueArray)):
						# loop through the array
						for i in range(0, len(reading)):
							if isinstance(reading[i], labrad.units.Value):
								try:
									readings.append(reading[i]._value)
								except:
									readings.append(reading[i].value)
								units.append(reading[i].units)
								
							else:
								readings.append(reading[i])
								units.append("")
					elif(type(reading) is list):
						
						for i in range(0, len(reading)):
							if(reading[i] is labrad.units.Value):
								try:
									readings.append(reading[i]._value)
								except:
									readings.append(reading[i].value)
								units.append(reading[i].units)
							else:
								readings.append(reading[i])
								units.append("")
					else:
						try:
							#print "Guessing device data type"
							readings.append(reading)
							units.append("")
						except:
							print("Problem with readings, type '"
								+type(reading)+"' cannot be displayed")
				# Pass the readings and units to the frame
				self.frame.setReadings(readings)
				self.frame.setUnits(units)
				# If there was an error, retract it.
				self.frame.retractError()
			except:
				#exc_type, exc_value, exc_traceback = sys.exc_info()
				#traceback.print_tb(exc_traceback)
				#print("Error")
				self.frame.raiseError("Problem communicating with "
					+self.name)
				self.frame.setReadings(None)
				self.isDevice = False
		# Query calls itself again, this keeps the thread alive.
		threading.Timer(1, self.Query).start()
		return 