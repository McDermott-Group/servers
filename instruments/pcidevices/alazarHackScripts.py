import time
import ctypes

import labrad
import atsapi as ats
import numpy as np

from labrad.units import V

cxn = labrad.connect()
digitizer = cxn.ats_digitizer_server
#digitizer.list_devices()
digitizer.select_device("ATS1::1")

# time.sleep(2)
# digitizer.set_led_state(ats.LED_ON)
# time.sleep(2)
# digitizer.set_led_state(ats.LED_OFF)

digitizer.configure_external_clocking()
digitizer.configure_trigger()
digitizer.configure_inputs(4*V)
digitizer.set_records_per_buffer(10)
digitizer.set_number_of_records(20)
digitizer.set_samples_per_record(256)
digitizer.configure_buffers()
t = np.linspace(0, 255, 256)
Omega = 30.028e6*2*np.pi
WA = np.cos(Omega * t)
WB = np.sin(Omega * t)
digitizer.add_demod_weights(WA, WB, "testing")
start = time.time()
digitizer.acquire_data()
digitizer.get_iqs("testing")
#data = digitizer.get_records()
stop = time.time()
print stop-start


