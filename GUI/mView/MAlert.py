import smtplib
import MMail
import threading
import time
import sys
sys.dont_write_bytecode = True
#from email.mime.text import MIMEText

class MAlert:
	def __init__(self,checkBoxes,mins, maxs, contacts,  devices, tele):
		#print "Mins: ", mins, " \r\nMaxs:", maxs, " \r\nContacts:", contacts
		# Configure all public variables
		self.devices = devices
		self.mins = mins
		#print(mins)
		self.maxs = maxs
		self.contacts = contacts
		self.message = []
		self.checkBoxes = checkBoxes
		self.tele = tele
		self.t1 = 0
		# Have the specified people been notified about the specific device?
		self.mailSent =[]
		# Keep running, this is false when settings are changed and a 
		# new NAlert instance is created. Setting this to false terminates
		# the thread.
		self.keepGoing = True
		# Keep track of which mail was sent
		for i in range(0, len(self.devices)):
			for y in range(0, len(self.devices[i].getFrame().getNicknames())):
				if(self.devices[i].getFrame().getNicknames()[y] is not None):
					self.mailSent.append(False)
					#print(len(self.mailSent))
	def begin(self):
		# This runs on its own thread
		self.deviceThread = threading.Thread(target = self.monitorReadings, args=[])
		# If the main thread stops, stop the child thread
		self.deviceThread.daemon = True
		# Start the thread
		self.deviceThread.start()
	
	def monitorReadings(self):
		'''Monitor the readings for issues'''
		# Z keeps track of which index we are on for arrays which are not 2D.
		z = 0
		# For all devices
		for i in range(0, len(self.devices)):
			# If it has readings
			if(self.devices[i].getFrame().getReadings() is not None):
				# Loop through all readings
				for y in range(0, len(self.devices[i].getFrame().getNicknames())):
					# If the reading is displayed on the GUI
					#print(self.devices[i].getFrame().getNicknames())
					if(self.devices[i].getFrame().getNicknames()[y] is not None):
						# Get that specific reading
						#print self.mins
						if len(self.mins) is not 0:
							if(len(str(self.mins[z])) is not 0):
								if(float(self.mins[z])>float(self.devices[i].getFrame().getReadings()[y])):
								# If a min has been specified
									if(self.checkBoxes[z]):
									#print "mins", (self.mins)
										self.generateMessage(z,y,i)
										#print(z)
										self.sendMail(i, y, z)
									#print(self.mins[z])
						if len(self.maxs) is not 0:
							if(len(str(self.maxs[z])) is not 0):
								if(float(self.maxs[z])<float(self.devices[i].getFrame().getReadings()[y])):
									if(self.checkBoxes[z]):
										self.generateMessage(z,y,i)
										self.sendMail(i, y, z)
						#print "z",(z)
						#print "y", y
						z = z+1
			else:
				
				z=z+len(self.devices[i].getFrame().getNicknames())
		if(self.keepGoing):
			threading.Timer(1, self.monitorReadings).start()
			
	def stop(self):
		self.keepGoing = False
		
	def generateMessage(self,z, y, i):
		#print "HERE 1 ", z
		#print(self.mins[z])
		#print(self.maxs[z])
		#print(len(self.mailSent))
		if(not self.mailSent[z]):
			#print("try")
			# self.message.append(("On "
				# +time.asctime( time.localtime(time.time()) )
				# +", the "+self.devices[i].getFrame().getTitle()+"'s "
				# + self.devices[i].getFrame().getNicknames()[y] + " was "+
				# str(self.devices[i].getFrame().getReadings()[y])+
				# self.devices[i].getFrame().getUnits()[y] +
				# " which is out of the specified range of "
				# +str(self.mins[z]) 
				# + self.devices[i].getFrame().getUnits()[y]+
				# " - " +str(self.maxs[z])+
				# self.devices[i].getFrame().getUnits()[y]+"."))
			self.message.append(("Time: "
				+time.asctime( time.localtime(time.time()) )
				+" | "+self.devices[i].getFrame().getTitle()+"->"
				+ self.devices[i].getFrame().getNicknames()[y] + ": "+
				str(self.devices[i].getFrame().getReadings()[y])+
				self.devices[i].getFrame().getUnits()[y] +
				" | Range: "
				+str(self.mins[z]) 
				+ self.devices[i].getFrame().getUnits()[y]+
				" - " +str(self.maxs[z])+
				self.devices[i].getFrame().getUnits()[y]+"."))
			
			self.mailSent[z] = True
				
		# except:
			# print("except")
			# self.mailSent.append(False)
			
			#print(self.mins)
			#print(self.mins[z])
		#print "HERE 2 ",z
		#print self.message
			
	def sendMail(self, i, y, z):
		'''Send mail if the given amount of time has elapsed.'''
		HOURS_BETWEEN_EMAILS = 0.0003
		elapsedHrs = (time.time()-self.t1)/3600
		
		
		if(HOURS_BETWEEN_EMAILS<elapsedHrs):
			# NMail.NMail(self.contacts[z],self.devices[i].getFrame()
				# .getTitle(), self.devices[i].getFrame().getNicknames()[y], str(self.message))
			#print str(self.devices[i].getFrame().getNicknames()[y])
			#print str(self.message)
			#print self.contacts[z].split(',')
			success, address = self.tele.send_sms(self.devices[i].getFrame().getNicknames()[y], 
									str(self.message), 
									self.contacts[z].split(','),
									"labrad_physics")
			if (not success):
				print("Couldn't send email to group: "+str(self.contacts[z].split(','))+ 
				", someone may be missing from the registry or incorrectly entered.")
			#print(self.message)
			#else:
				#print("Mail sent")
			self.message = []
			self.mailSent = []
			for i in range(0, len(self.devices)):
				for y in range(0, len(self.devices[i].getFrame().getNicknames())):
					if(self.devices[i].getFrame().getNicknames()[y] is not None):
						self.mailSent.append(False)
						#print(len(self.mailSent))
			
			self.t1 = time.time()
	
