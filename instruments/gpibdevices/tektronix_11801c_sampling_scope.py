# Copyright (C) 2016 Alexander Opremcak
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
name = Tekronix 11801C Digital Sampling Oscilloscope
version = 1.0
description = Basic Functionality for TDR
  
[startup]
cmdline = %PYTHON% %FILE%
timeout = 20
  
[shutdown]
message = 987654321
timeout = 5
### END NODE INFO
"""

from labrad.server import setting
from labrad.gpib import GPIBManagedServer
from twisted.internet.defer import returnValue
import numpy as np


class Tek11801C_Server(GPIBManagedServer):
    name = 'Tek11801C' # Server name.
    deviceName = ['ID TEK/11801C']
  
    @setting(10, 'Get Instrument Name', returns='s')
    def getInstrumentName(self, c):
        """Return the instrument name."""
        dev = self.selectedDevice(c)
        instrumentName = yield dev.query('ID?')
        returnValue(instrumentName)

    @setting(11, 'Get Num Sampling Heads', returns='i')
    def getNumSamplingHeads(self, c):
        """
        Return the number of sampling heads recognized by
        the Tek11801C.
        """
        dev = self.selectedDevice(c)
        # Next line returns something like 'ACQNUM 2'.
        resp = yield dev.query('ACQNUM?')
        NumAcqSys= int(resp.split(" ")[1])
        returnValue(NumAcqSys)

    @setting(12, 'Get Averaging State', returns='s')
    def getAveragingState(self, c):
        """Return the averaging state of the Tek11801C."""
        dev = self.selectedDevice(c)
        # Next line returns either 'AVG ON' or 'AVG OFF'.
        resp = yield dev.query('AVG?')
        # Parse to return either 'ON' or 'OFF'.
        returnValue(resp.split(" ")[1])

    @setting(13, 'Set Averaging State', avgState='s', returns='')
    def setAveragingState(self, c, avgState):
        """Set the averaging state of the Tek11801C."""
        dev = self.selectedDevice(c)
        possibilities = ('ON', 'OFF')
        if avgState.upper() in (pos.upper() for pos in possibilities):
            yield dev.write('AVG %s' %avgState.upper())
        else:
            print("Acceptable inputs for this function are " + 
                  "'ON' or 'OFF'")

    @setting(14, 'Get Chan Volt Offset', chanNum='w', returns='v[V]')
    def getChanVoltOffset(self, c, chanNum):
        """Return the averaging state of the Tek11801C."""
        dev = self.selectedDevice(c)
        # Next line returns either 'AVG ON' or 'AVG OFF'.
        resp = yield dev.query('CHM%s? OFFSET' %str(chanNum))
        # Parse to return either on or off.
        returnValue(float(resp.split(':')[1]))

    @setting(27, 'Get Num Points', returns='s')
    def getNumTracePoints(self, c):
        """Return number of points."""
        dev = self.selectedDevice(c)
        length = yield dev.query('TBM? LEN')
        returnValue(length)

    @setting(28, 'Get Trace Data', traceNum='w', returns='?')
    def getTraceData(self, c, traceNum=None):
        """
        Return trace data. This setting returns a tuple of 2D arrays,
        one for each trace. The form of 2D arrays is
        [[time_0, voltage(time_0)], ..., [time_n, voltage(time_m)]].
        """
        dev = self.selectedDevice(c)
        if traceNum is None:    # Assume user wants all traces.
            traceData = yield dev.query('OUTPUT ALLTRACE;WAV?')
        if traceNum >= 1:       # User specified 
            traceData = yield dev.query('OUTPUT TRACE%s;WAV?'
                    %str(traceNum))
        splitter = traceData.split(';')
        data = ()
        # Increment by 2's, 1 preamble and 1 data string per trace.
        for ii in range(0, len(splitter), 2):
            tracePreamble = splitter[ii].split(',')
            traceDataStr = splitter[ii+1].split(',')
            
            for jj in range(0, len(tracePreamble)):
                if 'XINCR' in tracePreamble[jj]:
                    XINCR = float(tracePreamble[jj].split(':')[1])
                elif 'XMULT' in tracePreamble[jj]:
                    XMULT = float(tracePreamble[jj].split(':')[1])
                elif 'XUNIT' in tracePreamble[jj]:
                    XUNIT = tracePreamble[jj].split(':')[1]
                elif 'XZERO' in tracePreamble[jj]:
                    XZERO = float(tracePreamble[jj].split(':')[1])
                elif 'YMULT' in tracePreamble[jj]:
                    YMULT = float(tracePreamble[jj].split(':')[1])
                elif 'YUNIT' in tracePreamble[jj]:
                    YUNIT = tracePreamble[jj].split(':')[1]
                elif 'YZERO' in tracePreamble[jj]:
                    YZERO = float(tracePreamble[jj].split(':')[1])
                   
            tdrData = np.empty((len(traceDataStr)-1, 2))
            for kk in range (1, len(traceDataStr)):
                tdrData[kk-1][0] = XINCR * (kk - 1) + XZERO
                tdrData[kk-1][1] = YZERO + YMULT*float(traceDataStr[kk])
            data = data + (np.copy(tdrData),)
        returnValue(data)
    
  
__server__ = Tek11801C_Server()


if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)
