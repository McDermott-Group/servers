# Copyright (C) 2015 Chris Wilen, Ivan Pechenezhskiy
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
### BEGIN NODE INFO
[info]
name = SIM928
version = 2.4.4
description = Server interface for the SIM928 Isolated Voltage Source.
instancename = SIM928

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 5
### END NODE INFO
"""

from twisted.internet.defer import inlineCallbacks, returnValue

from labrad import util
from labrad.server import setting
from labrad.gpib import GPIBManagedServer, GPIBDeviceWrapper
from labrad.units import V


class SIM928Wrapper(GPIBDeviceWrapper):
    @inlineCallbacks
    def initialize(self):
        self.voltage = yield self.getVoltage()
        self.output = yield self.getOutput()

    @inlineCallbacks
    def reset(self):
        yield self.write("*CLS;*RST")
        yield self.initialize()

    @inlineCallbacks
    def getVoltage(self):
        try:
            voltage = yield self.query("VOLT?")
            self.voltage = float(voltage) * V
        except BaseException:
            print("Failed to read the voltage")
            self.voltage = yield self.getVoltage()
        returnValue(self.voltage)

    @inlineCallbacks
    def getOutput(self):
        try:
            output = yield self.query("EXON?")
            self.output = bool(int(output))
        except BaseException:
            print("Failed to read the output state")
            self.output = yield self.getOutput()
        returnValue(self.output)

    @inlineCallbacks
    def setVoltage(self, v):
        if self.voltage != v:
            yield self.write("VOLT {:.5f}".format(v["V"]))
            # Ensure that the voltage is actually set to the right level.
            self.voltage = yield self.getVoltage()

    @inlineCallbacks
    def setOutput(self, on):
        if self.output != bool(on):
            yield self.write("EXON %d" % int(on))
            # Ensure that the output is set properly.
            self.output = yield self.getOutput()


class SIM928Server(GPIBManagedServer):
    """Provides basic control for SRS SIM928 voltage source."""

    name = "SIM928"
    deviceName = "STANFORD RESEARCH SYSTEMS SIM928"
    deviceWrapper = SIM928Wrapper

    @setting(100, "Reset")
    def reset(self, c):
        """Reset the voltage source."""
        yield self.selectedDevice(c).reset()

    @setting(101, "Voltage", v="v[V]", returns="v[V]")
    def voltage(self, c, v=None):
        """Get or set the voltage."""
        dev = self.selectedDevice(c)
        if v is not None:
            yield dev.setVoltage(v)
        returnValue(dev.voltage)

    @setting(102, "Output", on="b", returns="b")
    def output(self, c, on=None):
        """Get or set the output (on/off)."""
        dev = self.selectedDevice(c)
        if on is not None:
            yield dev.setOutput(on)
        returnValue(dev.output)


__server__ = SIM928Server()


if __name__ == "__main__":
    util.runServer(__server__)
