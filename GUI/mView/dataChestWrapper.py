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

# Utilities libraries.

"""
version = 1.2.1
description = Handles datalogging using DataChest
"""

from PyQt4 import QtCore, QtGui

from dateStamp import *
from dataChest import *

import sys
sys.dont_write_bytecode = True
import os

import datetime
import numpy
import re, string

import atexit
import threading
class dataChestWrapper:
	'''The dataChestWrapper class handles all datalogging. An instance 
	of dataChestWrapper should be created in the main class in order to
	begin datalogging.'''
	def __init__(self, devices):
		'''Initiallize the dataChest'''
		# Define the current time
		now = datetime.datetime.now()
		# Create a devices reference that can be accessed outside of this scope.
		self.devices = devices
		# These arrays will hold all dataChest data sets.
		self.dataSets = []
		self.hasData = []
		#self.hasValue = False
		# The done function must be called when the GUI exits
		atexit.register(self.done)
		# The datalogging is executed on its own thread
		self.deviceThread = threading.Thread(target = 
			self.save, args=[])
		# If the main thread stops, stop the child thread
		self.deviceThread.daemon = True
		# Start the thread
		self.deviceThread.start()
		for i in range(0, len(self.devices)):
			# Append a new dataChest object to the end
			# of the datasets array. Note, no dataset is being created.
			self.dataSets.append(dataChest(str(
				now.year)))
			self.hasData.append(False)
			
	def configureDataSets(self, i):
		'''Initialize the datalogger, if datasets already 
		exist, use them. Otherwise create new ones.'''
		now = datetime.datetime.now()
		self.hasData[i] = True
		# Generate a title for the dataset. NOTE: if 
		# the title of the device is changed in the device's constructor
		# in the main class, then a different data set will be created. 
		# This is because datasets are stored using the name of the device,
		# which is what the program looks for when checking if there are
		# data files that already exist.
		title = str(self.devices[i].getFrame().getTitle()).replace(" ", "")
		# Datasets are stored in the folder 'DATA_CHEST_ROOT\year\month\'
		# Try to access the current month's folder, if it does not exist, 
		# make it.
		try:
			self.dataSets[i].cd(str(now.month))
		except:
			self.dataSets[i].mkdir(str(now.month))
			self.dataSets[i].cd(str(now.month))
		# Look at the names of all existing datasets and check if the 
		# name contains the title of the current device. 
		existingFiles = self.dataSets[i].ls()
		# foundit becomes true if a dataset file already exists
		foundit = False
		# Go through all existing dataset files
		for y in range(0, len(existingFiles[0])):
			# If the name of the file contains the (persistant) title 
			# generated by the code, open that dataset and use it.
			print existingFiles[0]
			if(title in existingFiles[0][y]):
				self.dataSets[i].openDataset(existingFiles[0][y], 
					modify = True)
				foundit = True
		if(foundit):
			print("Previously existing data set found for "+title)
		# If the dataset does not already exist, we must create it.
		else:
			print("Creating dataset for "+title)
			#self.createNewDataset(i)

			
			# Name of the parameter. This is the name of the parameter
			# displayed on the gui except without spaces or 
			# non-alphanumerical characters.
			paramName = None
			# Arrays to hold any variables
			depvars = []
			indepvars = []
			# For each device, assume it is not connected and we should not log
			# data until the gui actually gets readings.
			# Loop through all parameters in the device
			for y in range (0, len(self.devices[i].getFrame().getNicknames())):
				# If the name of the parameter has not been defined as None 
				# in the constructor, then we want to log it.
				if(self.devices[i].getFrame().getNicknames()[y] is not None):
					# The name of the parameter in the dataset is the same 
					# name displayed on the GUI except without 
					# non-alphanumerical characters. Use regular expressions
					# to do this.
					paramName = str(self.devices[i].getFrame().getNicknames()
						[y]).replace(" ","")
					paramName = re.sub(r'\W+', '', paramName)
					# Create the tuple that defines the parameter.
					tup = (paramName, [1], "float64", str(self.devices[i]
						.getFrame().getUnits()[y]))
					# Add it to the array of dependent variables
					depvars.append(tup)
			# Get the datestamp from the datachest helper class.
			dStamp = dateStamp()
			# Time is the only independent variable
			indepvars.append(("time", [1], "utc_datetime", "s"))
			# The vars variable holds ALL variables
			vars = []
			vars.extend(indepvars)
			vars.extend(depvars)
			# Construct the data set
			#print indepvars
			#print depvars
			self.dataSets[i].createDataset(title, indepvars, depvars)
			# The datawidth parameter says how many variables 
			# (independent and dependent) make up the dataset.
			# DataWidth is used internally only.
			self.dataSets[i].addParameter("DataWidth", len(vars))
			if(self.devices[i].getFrame().getYLabel() is not None):
				# Configure the label of the y axis given in the device'same
				# constructor.
				self.dataSets[i].addParameter("Y Label", self.devices[i]
					.getFrame().getYLabel())
	def done(self):
		'''Run when GUI is exited. Cleanly terminates the dataset 
		with Nan values.'''
		dStamp = dateStamp()
		for i in range(0, len(self.dataSets)):
			# If the dataset was being logged
			if(self.hasData[i]):
				vars = []
				vars.append(dStamp.utcNowFloat())
				# Append Nan
				for y in range(1, self.dataSets[i].getParameter("DataWidth")):
					vars.append(np.nan)
				#print(vars)
				self.dataSets[i].addData([vars])

	def save(self):
		'''Stores the data'''
		# For all datasets, check if there are readings
		for i in range(0, len(self.devices)):
			if(self.devices[i].getFrame().getReadings()
				is not None):
				# If the device did not have any readings and now it does
				# then we want to create a dataset.
				if(not self.hasData[i]):
					#self.hasValue = True
				
					self.configureDataSets(i)
		# For all datasets		
		for i in range(0, len(self.dataSets)):
			# If there is data in this dataset
			if(self.hasData[i]):
				depvars = []
				indepvars = []
				vars = []
				readings = []
				# Get the newest data
				for y in range(0, len(self.devices[i].getFrame()
					.getNicknames())):
					# This checks if the reading is displayed on the GUI
					# if it is not, then it does not include it in the 
					# dataset.
					if(self.devices[i].getFrame().getNicknames()
						[y] is not None):
						# If the device has readings
						if(self.devices[i].getFrame().getReadings()
							is not None):
							readings.append(float(self.devices[i].getFrame()
								.getReadings()[y]))
						else:
							readings.append(np.nan)
				dStamp = dateStamp()
				# If the device has readings, add data to dataset
				if(readings is not None):
					indepvars.append(dStamp.utcNowFloat())
					depvars.extend(readings)
					vars.extend(indepvars)
					vars.extend(depvars)
					#print vars
					varslist = self.dataSets[i].getVariables()
					#print "varslist: ", varslist
					try:
						self.dataSets[i].addData([vars])
					except:
						print self.devices[i].getFrame().getTitle()+" ERROR: could not store data, this might be due to a change made to the parameters of the device,"
						" if this is the case thene either delete the data set from the current storage directory or move it somewhere else."
		# Keep the thread going. Without this, the thread terminates and
		# is garbage-collected.
		threading.Timer(1, self.save).start()
		
				
		
