# Copyright (C) 2016 Noah Meltzer, Alexander Opremcak
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
name = Omega Temperature Monitor Server
version = 1.0.14
description = Monitors temperature

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""

import time

# The LoopingCall function allows a function to be called periodically on a time interval
from twisted.internet.task import LoopingCall
from twisted.internet.reactor import callLater
# The reactor drives event loops (useful for a number of applications as well as implementing LoopingCall)
from twisted.internet import reactor

from datetime import datetime

from labrad.devices import DeviceServer, DeviceWrapper
from labrad.server import setting
import labrad.units as units
from twisted.internet.defer import inlineCallbacks, returnValue
from labrad import util

    
class OmegaTempMonitorWrapper(DeviceWrapper):
    @inlineCallbacks
    def connect(self, server, port):
        """Connect to an Omega temperature monitor."""
        print('Connecting to "%s" on port "%s"...' %(server.name, port))
        self.server = server
        self.ctx = server.context()
        self.port = port
        p = self.packet()
        p.open(port)
        p.baudrate(9600L)
        p.stopbits(1L)
        p.bytesize(7L)
        p.parity('O')
        p.timeout(1 * units.s)
        p.read_line() # Clear out the read buffer.
        yield p.send()
        
    def packet(self):
        """Create a packet in our private context."""
        return self.server.packet(context=self.ctx)
    
    def shutdown(self):
        """Disconnect from the serial port when we shut down."""
        return self.packet().close().send()
    
    @inlineCallbacks
    def write_line(self, code):
        """Write a data value to the temperature monitor."""
        p = self.packet()
        p.write_line(code)
        yield p.send()

    @inlineCallbacks
    def read_line(self):
        """Read a data value to the temperature monitor."""
        p = self.packet()
        p.read_line()
        ans = yield p.send()
        returnValue(ans.read_line)

   
            
class OmegaTempMonitorServer(DeviceServer):
    deviceName = 'Omega Temp Monitor Server'
    name = 'Omega Temp Monitor Server'
    deviceWrapper = OmegaTempMonitorWrapper
    alertInterval = 7200 #Default email alert interval is 7200s (2 hours)
    checkInterval = 2 #Default measurement test interval is 2s 
    thresholdLow = 50
    thresholdHigh = 60
            
    @inlineCallbacks
    def initServer(self):
        """Initialize the Temperature Monitor Server"""
        print "Server Initializing"
        self.reg = self.client.registry()
        yield self.loadConfigInfo()
        yield DeviceServer.initServer(self)
        
    def startRefreshing(self):
        """Start periodically refreshing the list of devices.
        The start call returns a deferred which we save for later.
        When the refresh loop is shutdown, we will wait for this
        deferred to fire to indicate that it has terminated.
        """
        dev = self.dev
        self.refresher = LoopingCall(self.refreshMe)
        self.refresherDone = \
                self.refresher.start(5.0,
                now=True)

    def refreshMe(self):
        """Periodically called automatically, used to call
        functions that must be called repeatedly"""
        #print "refreshing"
        self.checkMeasurements(self.dev)
        
    @inlineCallbacks
    def stopServer(self):
        """Kill the device refresh loop and wait for it to terminate."""
        if hasattr(self, 'refresher'):
            self.refresher.stop()
            yield self.refresherDone
            
    @setting(9, 'Start Server', returns='b')
    def start_server(self, c):
        """starts server ***insert meaningful text here"""
        dev = self.selectedDevice(c)
        self.dev = dev
        callLater(0.1, self.startRefreshing)
        return True
        
    @inlineCallbacks
    def getTemperature(self, dev):
        """Query the device for the temperature via serial communication"""
        yield dev.write_line("*X01")
        reading = yield dev.read_line()
        reading.rsplit(None, 1)[-1] #get last number in string
        reading = float(reading.lstrip("X01"))
        returnValue(reading * units.degF)

    @inlineCallbacks
    def checkMeasurements(self, dev):
        """Make sure measured values are within acceptable range"""
        #print "Checking Measurements"
        print "Temperature: "
        temperature = yield self.getTemperature(dev)
        print temperature
##        if thresholdLow<getTemperature<thresholdHigh:
##             self.alertRefresherDone = \
##                self.alertRefresher.start(self.alertInterval,
##                now=True)
##        else:
##             self.alertRefresherDone = \
##                self.alertRefresher.start(self.sendAlert,
##                now=False)
        
    def sendAlert(self):
        print "~~~~~PROBLEM WITH TEMPERATURE; ALERT SENT~~~~~"
        
    @inlineCallbacks
    def loadConfigInfo(self):
        """Load configuration information from the registry."""
        reg = self.reg
        yield reg.cd(['', 'Servers', 'Omega Temperature Monitor',
                'Links'], True)
        dirs, keys = yield reg.dir()
        p = reg.packet()
        for k in keys:
            p.get(k, key=k)
        ans = yield p.send()
        self.serialLinks = dict((k, ans[k]) for k in keys)
    
    @inlineCallbacks    
    def findDevices(self):
        """Find available devices from list stored in the registry."""
        devs = []
        for name, (server, port) in self.serialLinks.items():
            if server not in self.client.servers:
                continue
            server = self.client[server]
            ports = yield server.list_serial_ports()
            if port not in ports:
                continue
            devName = '{} - {}'.format(server, port)
            devs += [(name, (server, port))]
        returnValue(devs)


__server__ = OmegaTempMonitorServer()


if __name__ == '__main__':
    util.runServer(__server__)
