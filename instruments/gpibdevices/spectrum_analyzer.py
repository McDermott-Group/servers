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
#
# UPDATED
# 4 Aug, 2010 - Nathan Earnest - 2.1
# 2019 Nov, 21 - Chuanhong Liu -2.2

"""
### BEGIN NODE INFO
[info]
name = Spectrum Analyzer Server
version = 2.2
description = 
[startup]
cmdline = %PYTHON% %FILE%
timeout = 20
[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""

from labrad import types as T, errors
from labrad.server import setting
from labrad.gpib import GPIBManagedServer, GPIBDeviceWrapper
from struct import unpack
from twisted.internet.defer import inlineCallbacks, returnValue
from labrad import util
from labrad.units import kHz, MHz, GHz
from datetime import datetime
import time

__QUERY__ = """\
:FORM INT,32
:FORM:BORD NORM
:TRAC? TRACE%s"""


class SpectrumAnalyzer(GPIBManagedServer):
    name = "Spectrum Analyzer Server"
    deviceName = ["HP8593A"]
    deviceWrapper = GPIBDeviceWrapper

    @setting(
        10,
        "Get Trace",
        data=["{Query TRACE1}", "w {Specify trace to query: 1, 2, or 3}"],
        returns=["v[MHz] {start} v[MHz] {step} *v {y-values}"],
    )
    def get_trace(self, c, data=1):
        """Returns the y-values of the current trace from the spectrum analyzer"""
        dev = self.selectedDevice(c)
        if data < 1 or data > 3:
            raise Exception("data out of range")
        trace = data
        # start = float((yield dev.query('FA?;')))
        # span = float((yield dev.query('SP?;')))
        start = 0.0
        span = 0.0
        maxRetries = 10

        for i in range(maxRetries):
            try:
                yield dev.write("TRA?;")
                # yield dev.write('TRA')
                # t1 = time.time()
                resp = yield dev.read_raw()
                # t2 = time.time()
                vals = _parseBinaryData(resp)

                break
            except Exception:
                pass
            if i + 1 < maxRetries:
                print("Failed to get trace, trying again.")
            else:
                raise Exception("Failed to get trace")

        n = len(vals)

        # print('get_read takes:', t2-t1)
        returnValue((start / 1.0e6 * MHz, span / 1.0e6 / (n - 1) * GHz, vals))

    # @setting(12, 'Get Averaged Trace',
    # data=['{Query TRACE1}',
    # 'w {Specify trace to query: 1, 2, or 3}'],
    # returns=['v[MHz] {start} v[MHz] {step} *v {y-values}'])
    # def get_averaged_trace(self, c, data=1):
    # dev = self.selectedDevice(c)
    # self.switch_average(c, setting = 'OFF')
    # averaging = True
    # self.switch_average(c, setting = 'ON')
    # yield dev.write('*CLS')
    # yield dev.write('*ESE 1')
    # yield dev.write(':INIT:IMM')
    # yield dev.write('*OPC')
    # while averaging:
    # result = yield dev.query('*STB?')
    # if int(result)&(1<<5):
    # averaging = False
    # yield util.wakeupCall(1)
    # trace =  yield self.get_trace(c, data = data)
    # self.switch_average(c, setting = 'OFF')
    # returnValue(trace)

    @setting(
        20,
        "Peak Frequency",
        data=["{Get Reading}"],
        returns=["v[GHz] {Peak Frequency}"],
    )
    def peak_frequency(self, c, data):
        """Gets the current frequency from the peak detector"""
        dev = self.selectedDevice(c)
        pos = float((yield dev.query(":CALC:MARK:X?")))
        returnValue(T.Value(pos / 1e9, "GHz"))

    @setting(
        21,
        "Peak Amplitude",
        data=["{Get Reading}"],
        returns=["v[dBm] {Peak Amplitude}"],
    )
    def peak_amplitude(self, c, data):
        """Gets the current amplitude from the peak detector"""
        dev = self.selectedDevice(c)
        height = float((yield dev.query(":CALC:MARK:Y?")))
        returnValue(T.Value(height, "dBm"))

    @setting(
        22,
        "Average Amplitude",
        trace=["{Get average of Trace 1}", "w {Get average of this trace}"],
        returns=["v[dBm] {Average Amplitude}"],
    )
    def average_amplitude(self, c, trace=1):
        """Gets the average amplitude of the entire trace"""
        dev = self.selectedDevice(c)
        height = float((yield dev.query(":TRAC:MATH:MEAN? TRACE%d\n" % trace)))
        returnValue(T.Value(height, "dBm"))

    @setting(
        23,
        "Marker Amplitude",
        data=["{Get Reading}"],
        returns=["v[dBm] {Peak Amplitude}"],
    )
    def marker_amplitude(self, c, data):
        """Gets the current amplitude from the peak detector"""
        dev = self.selectedDevice(c)
        height = float((yield dev.query("MKCF;MKA?;")))
        returnValue(T.Value(height, "dBm"))

    @setting(
        51,
        "Number Of Points",
        n=[":Default, get number of points", "w: Set number of points"],
        returns=["w"],
    )
    def number_of_points(self, c, n=None):
        """Set of get the current number of points in the sweep"""
        dev = self.selectedDevice(c)
        if n is not None:
            yield dev.write(":SWE:POIN %d" % n)
        numpts = yield dev.query(":SWE:POIN?")
        returnValue(int(numpts))

    @setting(102, "Do IDN query", returns=["s"])
    def do_IDN_query(self, c):
        """Gets the IDN string from the device"""
        dev = self.selectedDevice(c)
        idn = yield dev.query("*IDN?")
        returnValue(idn)

    @setting(500, "set_center_frequency", f="v[GHz]", returns="")
    def set_center_frequency(self, c, f):
        """Sets the center frequency"""
        dev = self.selectedDevice(c)
        dev.write("CF %gGHZ;" % f["GHz"])

    @setting(522, "set_span_frequency", f="v[MHz]", returns="")
    def set_span_frequency(self, c, f):
        """Sets the Frequency Span"""
        dev = self.selectedDevice(c)
        dev.write("SP %gMHZ" % f["MHz"])

    @setting(523, "set_resolution_bandwidth", f="v[kHz]", returns="")
    def set_resolution_bandwidth(self, c, f):
        """Set the Resolution Bandwidth"""
        dev = self.selectedDevice(c)
        dev.write(":RB %gkHz" % f["kHz"])

    @setting(524, "Set Video Bandwidth", f="v[kHz]", returns="")
    def set_video_bandwidth(self, c, f):
        """Set the video Bandwidth"""
        dev = self.selectedDevice(c)
        dev.write(":BAND:VID %gkHz" % f["kHz"])

    @setting(26, "Set Marker to center Frequency", returns="")
    def set_marker_to_center_frequency(self, c):
        """Sets the marker to center frequency"""
        dev = self.selectedDevice(c)
        yield dev.write("MKCF;")
        print("Laaadiiida")

    @setting(600, "set_y_scale", setting="s", returns="")
    def set_y_scale(self, c, setting):
        """This sets the Y scale to either LINear or LOGarithmic"""
        allowed = ["LN", "LG"]
        if setting not in allowed:
            raise Exception("allowed settings are: %s" % allowed)
        dev = self.selectedDevice(c)
        dev.write("%s" % setting)

    @setting(602, "SetReference Level", f="v[dBm]", returns=[""])
    def set_reference_level(self, c, f):
        """Set the reference level"""
        dev = self.selectedDevice(c)
        dev.write("DISP:WIND:TRAC:Y:RLEV %gdBm" % f["dBm"])

    @setting(603, "set_sweep_time", f="v[ms]", returns="")
    def set_sweep_time(self, c, f):
        """Set the sweep time"""
        dev = self.selectedDevice(c)
        dev.write(":ST %gms" % f["ms"])

    @setting(604, "set_sweep_mode", setting="s", returns="")
    def set_sweep_mode(self, c, setting="s"):
        """This sets the sweep mode"""
        allowed = ["CONTS", "SNGLS"]
        if setting not in allowed:
            raise Exception("allowed settings are: %s" % allowed)
        dev = self.selectedDevice(c)
        dev.write(":%s" % setting)

    @setting(605, "Detector type", setting="s", returns="")
    def set_detector(self, c, setting="POS"):
        """This sets the detector type to either Peak,Negative Peak or Sample"""
        allowed = ["SAMP", "POS", "NEG"]
        if setting not in allowed:
            raise Exception("allowed settings are: %s" % allowed)
        dev = self.selectedDevice(c)
        dev.write(":DET %s" % setting)

    @setting(15, "set_trigger_source", setting="s")
    def set_trigger_source(self, c, setting="EXT"):
        """This sets the triger source to Free Run, Video, Power Line, or External"""
        allowed = ["IMM", "VID", "LINE", "EXT"]
        if setting not in allowed:
            raise Exception("allowed settings are: %s" % allowed)
        dev = self.selectedDevice(c)
        dev.write("TM %s;" % setting)
        # dev.write('TM EXT;' % setting)

    @setting(701, "Average ON/OFF", setting="s", returns="")
    def switch_average(self, c, setting="OFF"):
        """This turns the averaging on or off"""
        allowed = ["OFF", "ON", 0, 1]
        if setting not in allowed:
            raise Exception("allowed settings are: %s" % allowed)
        dev = self.selectedDevice(c)
        dev.write(":AVER %s" % setting)

    @setting(702, "Start Frequency", f="v[MHz]", returns="")
    def start_frequency(self, c, f):
        """Set the starting frequency"""
        dev = self.selectedDevice(c)
        dev.write(":FREQ:STAR %gMHz" % f["MHz"])

    @setting(703, "Stop Frequency", f="v[MHz]", returns="")
    def stop_frequency(self, c, f):
        """Set the stop frequency"""
        dev = self.selectedDevice(c)
        dev.write(":FREQ:STOP %gMHz" % f["MHz"])

    @setting(
        704,
        "Number Of Averages",
        n=[":Default, get number of averages", "w: Set number of averages"],
        returns=["w"],
    )
    def num_averages(self, c, n=None):
        """Set of get the current number of points in the sweep"""
        dev = self.selectedDevice(c)
        if n is not None:
            yield dev.write(":AVER:COUN %d" % n)
        numavs = yield dev.query(":AVER:COUN?")
        returnValue(int(numavs))

    @setting(705, "Query 10 MHz ref", returns=["s"])
    def check_extref(self, c):
        """Checks whether EXT 10 MHz ref is used. Returns 'EXT' or 'INT'."""
        dev = self.selectedDevice(c)
        idn = yield dev.query(":SENS:ROSC:SOUR?")  # agilent n9010a
        # idn = yield dev.query(':CAL:FREQ:REF?') # agilent e4407b
        returnValue(idn)


##  Attempt to set average type.  SA does not accept value.
##  Gives error: "illegal paramter value"
##    @setting(702, 'Average Type', setting='s', returns='')
##    def average_type(self, c, setting='VID'):
##        """This switching the averaging type from either Video or to RMS Power"""
##        allowed = ['VID', 'POW']
##        if setting not in allowed:
##            raise Exception('allowed settings are: %s' % allowed)
##        dev = self.selectedDevice(c)
##        dev.write(':AVER:TYPE %s' % setting)


## dev.write('DISPlay:WINDow:TRACe:Y:SPACing  LINear|LOGarithmic)
##    @setting(501, 'Resolution Bandwidth',
##                  accepts=['v[kHz]'],
##                  returns=['v[kHz]'])
##    @inlineCallbacks
##    def set_resolution_band(self, c, data):
##        """Sets the resolution bandwidth"""
##        dev = self.selectedDevice(c)
##        yield dev.write(':FREQ:CENT %gMHz\n' %data.value )
##        returnValue(data)


def _parseBinaryData(data):
    """Parse binary trace data."""
    # h = int(data[1]) #length of header
    # d = int(data[2:2+h]) #header, tells us how many bytes of data
    # if len(s) != d:
    # raise errors.HandlerError('Could not decode binary response.')
    # d=2080
    # s = data
    # n = d/4 # 4 bytes per data point
    # n=len(data);
    # data = unpack('>'+'1'*n, data)
    # print s
    # data = [d/1000.0 for d in data]
    return tuple(data.split(","))


__server__ = SpectrumAnalyzer()

if __name__ == "__main__":
    from labrad import util

    util.runServer(__server__)
