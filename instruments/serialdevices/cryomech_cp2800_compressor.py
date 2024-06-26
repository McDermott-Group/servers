# Copyright (C) 2007  Matthew Neeley
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

# version 2.1: added caching of values to reduce amount written/read over serial
# version 2.2: added allowed temperature and current ranges to throw out bogus data

"""
### BEGIN NODE INFO
[info]
name = CP2800 Compressor
version = 2.2.2
description = Compressor for the ADR pulse tube cooler.
[startup]
cmdline = %PYTHON% %FILE%
timeout = 20
[shutdown]
message = 987654321
timeout = 5
### END NODE INFO
"""

import time

from labrad.devices import DeviceServer, DeviceWrapper
from labrad.server import setting, inlineCallbacks, returnValue
import labrad.units
from labrad.units import s, degC, K, psi, torr, min as minutes, A
from labrad import util

CACHE_TIME = 0.8
ALLOWED_CURRENT_RANGE = [-100 * A, 100 * A]
ALLOWED_TEMPERATURE_RANGE = [0 * K, 500 * K]

# registry (for info about where to connect)
# Servers -> CP2800 Compressor
# -> Serial Links = [(server, port),...]
# -> Logs -> <deviceName> -> YYYY -> MM -> DD ->

# data vault (for logging of numerical data)
# Logs -> CP2800 Compressor -> <deviceName> -> {YYYY} -> {MM} -> {DD} ->
#      -> Vince -> {YYYY} -> {MM} -> {DD} ->
#      -> Jules -> {YYYY} -> {MM} -> {DD} ->


class CompressorDevice(DeviceWrapper):
    @inlineCallbacks
    def connect(self, server, port):
        """Connect to a compressor device."""
        print(('Connecting to "%s" on port "%s"...' % (server.name, port)))
        self.server = server
        self.ctx = server.context()
        self.port = port
        # Cache the values for many of the requests so as to reduce
        # serial traffic.
        self.status, self.status_time = None, 0
        self._temperatures, self._temperatures_time = None, 0
        self._pressures, self._pressures_time = None, 0
        self.cpu_temp, self.cpu_temp_time = None, 0
        self.motor_current, self.motor_current_time = None, 0

        p = self.packet()
        p.open(port)
        p.baudrate(115200)
        p.read()  # Clear out the read buffer.
        p.timeout(TIMEOUT)
        yield p.send()

    def packet(self):
        """Create a packet in our private context."""
        return self.server.packet(context=self.ctx)

    def shutdown(self):
        """Disconnect from the serial port when we shut down."""
        return self.packet().close().send()

    @inlineCallbacks
    def write(self, key, value, index=0):
        """Write a data value to the compressor."""
        if key not in WRITEABLE:
            raise Exception('Cannot write to key "%s".' % (key,))
        pkt = write(HASHCODES[key], int(value), index=index)
        yield self.packet().write(pkt).read_line("\r").send()

    @inlineCallbacks
    def read(self, key, index=0):
        """Read a data value from the compressor."""
        if key not in READABLE:
            raise Exception('Cannot read key "%s".' % (key,))
        p = self.packet()
        p.write(read(HASHCODES[key], index=index))
        p.read_line("\r")
        ans = yield p.send()
        returnValue(getValue(ans.read_line))

    @inlineCallbacks
    def read_raw(self, hashcode, index=0):
        p = self.packet()
        p.write(read(hashcode, index=index))
        p.read_line("\r")
        ans = yield p.send()
        returnValue(getValue(ans.read_line))

    def startCompressor(self):
        return self.write("EV_START_COMP_REM", 1)

    def stopCompressor(self):
        return self.write("EV_STOP_COMP_REM", 1)

    @inlineCallbacks
    def compressorStatus(self):
        if time.time() - self.status_time > CACHE_TIME:
            ans = yield self.read("COMP_ON")
            self.status = bool(ans)
            self.status_time = time.time()
        returnValue(self.status)

    @inlineCallbacks
    def readArrays(self, keys, length, processFunc):
        """Read arrays from the compressor, returning processed results."""
        p = self.packet()
        for i in range(length):
            for key in keys:
                p.write(read(HASHCODES[key], i))
                p.read_line("\r", key=(i, key))
        ans = yield p.send()
        vals = [
            [processFunc(getValue(ans[i, key])) for key in keys] for i in range(length)
        ]
        returnValue(vals)

    @inlineCallbacks
    def temperatures(self):
        if time.time() - self._temperatures_time > CACHE_TIME:
            keys = "TEMP_TNTH_DEG", "TEMP_TNTH_DEG_MINS", "TEMP_TNTH_DEG_MAXES"
            ts = yield self.readArrays(keys, 4, toTemp)
            # if [t for t in ts if t[0]['K'] >= ALLOWED_TEMPERATURE_RANGE[0] and t[0]['K'] <= ALLOWED_TEMPERATURE_RANGE[1]]:
            # if all([t[0]['K'] >= ALLOWED_TEMPERATURE_RANGE[0] and t[0]['K'] <= ALLOWED_TEMPERATURE_RANGE[1] for t in ts]):
            self._temperatures = ts
            self._temperatures_time = time.time()
        returnValue(self._temperatures)

    @inlineCallbacks
    def pressures(self):
        if time.time() - self._pressures_time > CACHE_TIME:
            keys = "PRES_TNTH_PSI", "PRES_TNTH_PSI_MINS", "PRES_TNTH_PSI_MAXES"
            self._pressures = yield self.readArrays(keys, 2, toPress)
            self._pressures_time = time.time()
        returnValue(self._pressures)

    def clearMarkers(self):
        """Clear Min/Max temperature and pressure markers."""
        return self.write("CLR_TEMP_PRES_MMMARKERS", 1)


class CompressorServer(DeviceServer):
    name = "CP2800 Compressor"
    deviceWrapper = CompressorDevice

    @inlineCallbacks
    def initServer(self):
        yield self.loadConfigInfo()
        yield DeviceServer.initServer(self)

    @inlineCallbacks
    def loadConfigInfo(self):
        """Load configuration information from the registry."""
        reg = self.client.registry
        p = reg.packet()
        p.cd(["", "Servers", "CP2800 Compressor"], True)
        p.get("Serial Links", "*(ss)", key="links")
        ans = yield p.send()
        self.serialLinks = ans["links"]

    @inlineCallbacks
    def findDevices(self):
        """Find available devices from list stored in the registry."""
        devs = []
        for name, port in self.serialLinks:
            if name not in self.client.servers:
                continue
            server = self.client[name]
            ports = yield server.list_serial_ports()
            if port not in ports:
                continue
            devName = "%s - %s" % (name, port)
            devs += [(devName, (server, port))]
        returnValue(devs)

    @setting(100, "Start", returns="")
    def start_compressor(self, c):
        """Start the compressor."""
        dev = self.selectedDevice(c)
        yield dev.startCompressor()

    @setting(200, "Stop", returns="")
    def stop_compressor(self, c):
        """Stop the compressor."""
        dev = self.selectedDevice(c)
        yield dev.stopCompressor()

    @setting(300, "Status", returns="b")
    def compresssor_status(self, c):
        """Get the on/off status of the compressor."""
        dev = self.selectedDevice(c)
        return dev.compressorStatus()

    @setting(1000, "Temperatures", returns="*(v[K]{curr}, v[K]{min}, v[K]{max})")
    def temperatures(self, c):
        """
        Get temperatures.
        Returns the current, min and max temperatures for the following
        4 channels: water in, water out, helium, and oil. The Min and
        Max markers can be reset by calling 'Clear Markers'.
        """
        dev = self.selectedDevice(c)
        return dev.temperatures()

    @setting(1050, "Current Temperatures Only", returns="*v[K]{curr}")
    def temperaturesForGui(self, c):
        dev = self.selectedDevice(c)
        allTemps = yield dev.temperatures()
        temps = [i[0] for i in allTemps]
        returnValue(temps)

    @setting(1100, "Pressures", returns="*(v[torr]{curr}, v[torr]{min}, v[torr]{max})")
    def pressures(self, c):
        """
        Get pressures.
        Returns the current, min and max pressures for the following
        2 channels: high side, low side. The Min and Max
        markers can be reset by calling 'Clear Markers'.
        """
        dev = self.selectedDevice(c)
        return dev.pressures()

    @setting(1200, "Clear Markers")
    def clear_markers(self, c):
        """Clear Min/Max temperature and pressure markers."""
        dev = self.selectedDevice(c)
        yield dev.clearMarkers()

    @setting(2000, "CPU Temp", returns="v[K]")
    def cpu_temp(self, c):
        """Get the CPU temperature."""
        dev = self.selectedDevice(c)
        if time.time() - dev.cpu_temp_time > CACHE_TIME:
            ans = yield dev.read("CPU_TEMP")
            t = toTemp(ans)
            if t >= ALLOWED_TEMPERATURE_RANGE[0] and t <= ALLOWED_TEMPERATURE_RANGE[1]:
                dev.cpu_temp = t
                dev.cpu_temp_time = time.time()
        returnValue(dev.cpu_temp)

    @setting(2100, "Elapsed Time", returns="v[min]")
    def elapsed_time(self, c):
        """Get the elapsed running time of the compressor."""
        dev = self.selectedDevice(c)
        ans = yield dev.read("COMP_MINUTES")
        returnValue(float(ans) * minutes)

    @setting(2200, "Motor Current", returns="v[A]")
    def motor_current(self, c):
        """Get the motor current draw."""
        dev = self.selectedDevice(c)
        if time.time() - dev.motor_current_time > CACHE_TIME:
            ans = yield dev.read("MOTOR_CURR_A")
            t = float(ans) * A
            if t >= ALLOWED_CURRENT_RANGE[0] and t <= ALLOWED_CURRENT_RANGE[1]:
                dev.motor_current = t
                dev.motor_current_time = time.time()
        returnValue(dev.motor_current)

    @setting(2300, "Read Raw", hashcode="w", index="w", returns="i")
    def read_raw(self, c, hashcode, index=0):
        dev = self.selectedDevice(c)
        ans = yield dev.read_raw(hashcode, index)
        returnValue(ans)


# Compressor control protocol.
STX = 0x02
ESC = 0x07
ADDR = 0x10
CR = ord("\r")
CMD_RSP = 0x80
RESP_LEN = 14  # 3 bytes SMDP header, 8 bytes data, 2 bytes checksum, CR.
TIMEOUT = 1 * labrad.units.s  # Serial read timeout.

# Codes for compressor variables.
HASHCODES = {
    # misc
    "CODE_SUM": 0x2B0D,  # Firmware checksum.
    "MEM_LOSS": 0x801A,  # TRUE if nonvolatile memory was lost.
    "CPU_TEMP": 0x3574,  # CPU temperature (0.1 C).
    "BATT_OK": 0xA37A,  # TRUE if clock OK.
    "BATT_LOW": 0x0B8B,  # TRUE if clock battery low.
    "COMP_MINUTES": 0x454C,  # Elapsed compressor minutes.
    "MOTOR_CURR_A": 0x638B,  # Compressor motor current draw, in Amps.
    # temperatures
    "TEMP_TNTH_DEG": 0x0D8F,  # Temperatures (0.1 C).
    "TEMP_TNTH_DEG_MINS": 0x6E58,  # Minimum temps seen (0.1 C).
    "TEMP_TNTH_DEG_MAXES": 0x8A1C,  # Maximum temps seen (0.1 C).
    "TEMP_ERR_ANY": 0x6E2D,  # TRUE if any temperature sensor has failed.
    # pressures
    "PRES_TNTH_PSI": 0xAA50,  # Low/high side pressures (0.1 PSI).
    "PRES_TNTH_PSI_MINS": 0x5E0B,  # Minimum pressures seen (0.1 PSI).
    "PRES_TNTH_PSI_MAXES": 0x7A62,  # Maximum pressures seen (0.1 PSI).
    "PRES_ERR_ANY": 0xF82B,  # TRUE if any pressure sensor has failed.
    "H_ALP": 0xBB94,  # Average low-side pressure (0.1 PSI).
    "H_AHP": 0x7E90,  # Average high-side pressure (0.1 PSI).
    "H_ADP": 0x319C,  # Average delta pressure (0.1 PSI).
    "H_DPAC": 0x66FA,  # 1st deriv. of high side pressure, "bounce" (0.1 PSI).
    "CLR_TEMP_PRES_MMMARKERS": 0xD3DB,  # Reset pres/temp min/max markers.
    # Compressor control and status.
    "EV_START_COMP_REM": 0xD501,  # Start compressor.
    "EV_STOP_COMP_REM": 0xC598,  # Stop compressor.
    "COMP_ON": 0x5F95,  # TRUE if compressor is on.
    "ERR_CODE_STATUS": 0x65A4,  # Non-zero value indicates an error code.
}

READABLE = [
    "CPU_TEMP",
    "TEMP_TNTH_DEG",
    "TEMP_TNTH_DEG_MINS",
    "TEMP_TNTH_DEG_MAXES",
    "PRES_TNTH_PSI",
    "PRES_TNTH_PSI_MINS",
    "PRES_TNTH_PSI_MAXES",
    "H_ALP",
    "H_AHP",
    "H_ADP",
    "COMP_ON",
    "COMP_MINUTES",
    "MOTOR_CURR_A",
]

WRITEABLE = [
    "EV_START_COMP_REM",
    "EV_STOP_COMP_REM",
    "CLR_TEMP_PRES_MMMARKERS",
]


# SMDP functions (Sycon Multi-Drop Protocol).
def checksum(data):
    """Compute checksum for Sycon Multi Drop Protocol."""
    ck = sum(data) % 256
    cksum1 = (ck >> 4) + 0x30
    cksum2 = (ck & 0xF) + 0x30
    return [cksum1, cksum2]


def stuff(data):
    """Escape the data to be sent to compressor."""
    XLATE = {0x02: 0x30, 0x0D: 0x31, 0x07: 0x32}
    out = []
    for c in data:
        if c in XLATE:
            out.extend([ESC, XLATE[c]])
        else:
            out.append(c)
    return out


def unstuff(data):
    """Unescape data coming back from the compressor."""
    XLATE = {0x30: 0x02, 0x31: 0x0D, 0x32: 0x07}
    out = []
    escape = False
    for c in data:
        if escape:
            out.append(XLATE[c])
            escape = False
        elif c == ESC:
            escape = True
        else:
            out.append(c)
    return out


def pack(data):
    """
    Make a packet to send data to the compressor.
    We use the Sycon Multi Drop Protocol.
    """
    chk = checksum([ADDR, CMD_RSP] + data)
    pkt = [ADDR, CMD_RSP] + stuff(data)
    return [STX] + pkt + chk + [CR]


def unpack(response):
    """Pull binary data out of SMDP response packet."""
    if isinstance(response, str):
        response = [ord(c) for c in response]
    if response[-1] == CR:
        response = response[:-1]
    rsp = response[2] & 0xF  # Response code (see SMDP docs).
    # Drop 3 byte header (STX, ADDR, CMD_RSP) and 2 byte checksum.
    data = unstuff(response[3:-2])
    return data


# Data Dictionary for CP2800 Compressor.
def read(hashcode, index=0):
    """Make a packet to read a variable."""
    return pack([0x63] + toBytes(hashcode, count=2) + [index])


def write(hashcode, value, index=0):
    """Make a packet to write a variable."""
    return pack([0x61] + toBytes(hashcode, count=2) + [index] + toBytes(value))


def getValue(resp):
    """Get an integer value from a response packet."""
    data = unpack(resp)
    return fromBytes(data[-4:])


def toBytes(n, count=4):
    """Turn an int into a list of bytes."""
    return [(n >> (8 * i)) & 0xFF for i in reversed(list(range(count)))]


def fromBytes(b, count=4):
    """Turn a list of bytes into an int."""
    return sum(d << (8 * i) for d, i in zip(b, reversed(list(range(count)))))


def toTemp(v, units=K):
    """Convert temp reading to a LabRAD temperature."""
    return ((v / 10.0) * degC).inUnitsOf(units)


def toPress(v, units=torr):
    """Convert a pressure reading to a LabRAD pressure."""
    return ((v / 10.0) * psi).inUnitsOf(units)


# Create a server instance and run it
__server__ = CompressorServer()


if __name__ == "__main__":
    util.runServer(__server__)
