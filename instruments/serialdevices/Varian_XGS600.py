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
name = Varian Guage Controlelr
version = 1.0.1
description = Controls vacuum cart

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""

from labrad.devices import DeviceServer, DeviceWrapper
from labrad.server import setting
import labrad.units as units
from labrad import util

from utilities import sleep

from twisted.internet.task import LoopingCall
from twisted.internet.reactor import callLater
from twisted.internet.defer import inlineCallbacks, returnValue, DeferredLock

from functools import partial
import time

import numpy as np
class VarianControllerWrapper(DeviceWrapper):
    @inlineCallbacks
    def connect(self, server, port):
        '''Connect the the guage controller'''
        print('Connecting to "%s" on port "%s"...' %(server.name, port))
        self.server = server
        self.ctx = server.context()
        self.port = port
        # The following parameters match the default configuration of 
        # the Varian unit.
        p = self.packet()
        p.open(port)
        p.baudrate(9600L)
        p.stopbits(1L)
        p.bytesize(8L)
        p.parity('N')
        p.rts(False)
        p.timeout(2 * units.s)
        # Clear out the read buffer. This is necessary for some devices.
        p.read_line()
        yield p.send()
        
    def packet(self):
        """Create a packet in our private context."""
        return self.server.packet(context=self.ctx)
    def shutdown(self):
        """Disconnect from the serial port when we shut down."""
        return self.packet().close().send()
        

    def rw_line(self, code):
        # Don't allow two concurrent read/write calls. Use deferred locking to
        # enforce this
        self._lock = DeferredLock()
        return self._lock.run(partial(self._rw_line, code))

    @inlineCallbacks
    def _rw_line(self, code):
        '''Write data to the device.'''
        yield self.server.write_line(code, context=self.ctx)
        time.sleep(0.1)
        ans = yield self.server.read(context=self.ctx)
        returnValue(ans)
        
class VarianControllerServer(DeviceServer):
    devicename = 'Varian Guage Controller'
    name = 'Varian Guage Controller'
    deviceWrapper = VarianControllerWrapper
    
    @inlineCallbacks
    def initServer(self):
        '''Initialize the server'''
        print "Server Initializing"
        self.reg = self.client.registry()
        yield self.loadConfigInfo()
        yield DeviceServer.initServer(self)
    
    @setting(12, 'Get Pressures', returns='*?')
    def pressures(self, c):
        dev = self.selectedDevice(c)
        ans = yield self.getPressures(dev)
        ans = ans.replace('>','')
        ans = ans.rsplit(',')
        ans = [val.strip() for val in ans]
        #print ans
        ans = [np.nan if not self.isFloat(val) else float(val) for val in ans ]
        
        unit = yield self.getUnits(dev)
        print unit
        if unit == '00':
           # print "torr"
            ans = ans * units.torr
        elif unit == '01':
            ans = [(val/1000) for val in ans]
            ans = ans*units.bar
        elif unit == '00':
            ans = ans * units.Pa
            
        returnValue(ans)
        
    @inlineCallbacks
    def getPressures(self, dev):
        
        ans = yield dev.rw_line("#000F\r")
        # Replace > symbol
        
        returnValue( ans)
        
    @inlineCallbacks
    def getUnits(self, dev):
        ans = yield dev.rw_line("#0013\r")
        ans = ans.strip()
        ans = ans.replace('>', '')
        returnValue( ans)
    def isFloat(self, val):
        try:
            float(val)
            return True
        except:
            return False
    @inlineCallbacks
    def loadConfigInfo(self):
        """Load configuration information from the registry."""
        reg = self.reg
        yield reg.cd(['', 'Servers', 'VarianController', 'Links'], True)
        dirs, keys = yield reg.dir()
        p = reg.packet()
        for k in keys:
            p.get(k, key=k)
        ans = yield p.send()
        self.serialLinks = {k: ans[k] for k in keys}

    @inlineCallbacks    
    def findDevices(self):
        """Find available devices from a list stored in the registry."""
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


__server__ = VarianControllerServer()


if __name__ == '__main__':
    util.runServer(__server__)