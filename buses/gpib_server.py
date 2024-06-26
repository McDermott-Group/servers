# Copyright (C) 2008  Matthew Neeley
#           (C) 2015  Chris Wilen, Ivan Pechenezhskiy, Joseph Suttle
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
name = GPIB Bus
version = 1.4.1
description = Gives access to GPIB devices via pyvisa.
instancename = %LABRADNODE% GPIB Bus

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""

import string
import pyvisa as visa
from pyvisa.errors import VisaIOError

from twisted.internet.defer import inlineCallbacks
from twisted.internet.reactor import callLater

# from twisted.internet.task import LoopingCall

from labrad.server import LabradServer, setting
from labrad.errors import DeviceNotSelectedError
import labrad.units as units


class GPIBBusServer(LabradServer):
    """Provides direct access to GPIB-enabled devices."""

    name = "%LABRADNODE% GPIB Bus"
    # refreshInterval = 10
    defaultTimeout = 1.0 * units.s

    def initServer(self):
        self.mydevices = {}
        # start refreshing only after we have started serving
        # this ensures that we are added to the list of available
        # servers before we start sending messages
        callLater(0.1, self.startRefreshing)

    def startRefreshing(self):
        """Start periodically refreshing the list of devices.

        The start call returns a deferred which we save for later.
        When the refresh loop is shutdown, we will wait for this
        deferred to fire to indicate that it has terminated.
        """
        # self.refresher = LoopingCall(self.refreshDevices)
        # self.refresherDone = self.refresher.start(self.refreshInterval, now=True)
        self.refreshDevices()

    # @inlineCallbacks
    # def stopServer(self):
    # """Kill the device refresh loop and wait for it to terminate."""
    # if hasattr(self, 'refresher'):
    # self.refresher.stop()
    # yield self.refresherDone

    def refreshDevices(self):
        """Refresh the list of known devices on this bus.

        Currently supported are GPIB devices and GPIB over USB.
        """
        try:
            self.rm = visa.ResourceManager()
            # Use str() because labrad.types can't deal with unicode
            # strings.
            addresses = [str(a) for a in self.rm.list_resources()]
            additions = set(addresses) - set(self.mydevices.keys())
            deletions = set(self.mydevices.keys()) - set(addresses)
            for addr in additions:
                try:
                    if addr.startswith("GPIB"):
                        instName = addr
                    elif addr.startswith("TCPIP"):
                        instName = addr
                    elif addr.startswith("USB"):
                        if "::INSTR" in addr:
                            instName = addr
                        else:
                            instName = addr + "::INSTR"
                    else:
                        continue
                    instr = self.rm.open_resource(instName, open_timeout=1.0)
                    # instr.write_termination = u'\r\n'
                    instr.clear()
                    self.mydevices[addr] = instr
                    self.sendDeviceMessage("GPIB Device Connect", addr)
                except Exception as e:
                    print(("Failed to add %s: %s" % (addr, str(e))))
            # Because pyvisa's list_resources() command doesn't list
            # TCPIP addresses, we need to make sure we don't delete them
            # everytime we refresh the address list.
            for addr in deletions:
                if not (addr.startswith("TCPIP")):
                    del self.mydevices[addr]
                self.sendDeviceMessage("GPIB Device Disconnect", addr)
        except Exception as e:
            print(("Problem while refreshing devices: %s" % str(e)))

    @setting(27, tcpAddr="s")
    def addTCPIPDevice(self, c, tcpAddr=None):
        """refreshDevices fails to find TCPIP VISA objects, so you need
        to add them manually.  This function allows you to do that. The
        address should look like this: 'TCPIP::10.128.226.234::INSTR'.
        """
        try:
            self.rm = visa.ResourceManager()
            try:
                instr = self.rm.open_resource(tcpAddr, open_timeout=10.0)
                # instr.write_termination = u'\r\n'
                print((instr.query("*IDN?")))
                instr.clear()
                self.mydevices[tcpAddr] = instr
                self.sendDeviceMessage("GPIB Device Connect", tcpAddr)
            except Exception as e:
                print(("Failed to add %s: %s" % (tcpAddr, str(e))))
        except Exception as e:
            print(("Problem while adding TCPIP address: %s" % str(e)))

    def getSocketsList(self):
        """Get a list of all connected devices.

        Return:
        A list of strings with the names of all connected devices, ready
        for being used to open each of them.
        """
        return self.rm.list_resources()

    def sendDeviceMessage(self, msg, addr):
        print(("%s: %s" % (msg, addr)))
        self.client.manager.send_named_message(msg, (self.name, addr))

    def initContext(self, c):
        c["timeout"] = self.defaultTimeout

    def getDevice(self, c):
        if "addr" not in c:
            raise DeviceNotSelectedError("No GPIB address selected")
        if c["addr"] not in self.mydevices:
            raise Exception("Could not find device %s" % c["addr"])
        instr = self.mydevices[c["addr"]]
        instr.timeout = c["timeout"]["ms"]
        return instr

    @setting(19, returns="*s")
    def list_addresses(self, c):
        """Get a list of GPIB addresses on this bus."""
        return sorted(self.mydevices.keys())

    @setting(21)
    def refresh_devices(self, c):
        """Manually refresh devices."""
        self.refreshDevices()

    @setting(20, addr="s", returns="s")
    def address(self, c, addr=None):
        """Get or set the GPIB address for this context.

        To get the addresses of available devices, use the list_devices
        setting.
        """
        if addr is not None:
            c["addr"] = addr
        return c["addr"]

    @setting(22, time="v[s]", returns="v[s]")
    def timeout(self, c, time=None):
        """Get or set the GPIB timeout."""
        if time is not None:
            c["timeout"] = time
        return c["timeout"]

    @setting(23, data="s", returns="")
    def write(self, c, data):
        """Write a string to the GPIB bus."""
        try:
            # Note the explicit conversion from ASCII to Unicode.
            # print c['addr'], unicode(data)
            self.getDevice(c).write(str(data))
        except VisaIOError:
            print(("Could not write '%s' to %s" % (str(data), c["addr"])))

    @setting(24, bytes="w", returns="s")
    def read_raw(self, c, bytes=None):
        """Read a raw string from the GPIB bus.

        If specified, this method reads only the given number of bytes,
        otherwise, it reads until the device stops sending.
        """
        instr = self.getDevice(c)
        try:
            if bytes is None:
                return instr.read_raw()
            else:
                return instr.read_raw(bytes)
        except VisaIOError:
            print(("No response from %s" % c["addr"]))
            return ""

    @setting(25, returns="s")
    def read(self, c):
        """Read from the GPIB bus."""
        try:
            # Note the explicit conversion from Unicode to ASCII.
            resp = self.getDevice(c).read()
            resp = resp.strip(string.whitespace + "\x00")
            return resp.encode("ascii", "ignore")
        except VisaIOError:
            print(("No response from %s" % c["addr"]))
            return ""

    @setting(26, data="s", returns="s")
    def query(self, c, data):
        """Make a GPIB query.

        This query is atomic. No other communication to the device will
        occur while the query is in progress.
        """
        try:
            # Note the explicit conversion from Unicode to ASCII.
            resp = self.getDevice(c).query(data)
            resp = resp.strip(string.whitespace + "\x00")
            return resp.encode("ascii", "ignore")
        except VisaIOError:
            print(("No response from %s to '%s'" % (c["addr"], str(data))))
            return ""


__server__ = GPIBBusServer()

if __name__ == "__main__":
    from labrad import util

    util.runServer(__server__)
