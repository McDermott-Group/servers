import time
import numpy as np
import atsapi as ats

import labrad
from labrad.units import V

cxn = labrad.connect()
digitizer = cxn.ats_waveform_digitizer
digitizer.select_device("ATS1::1")
digitizer.configure_external_clocking()
digitizer.configure_trigger()

digitizer.configure_inputs(400e-3*V)
digitizer.samples_per_record(512)
digitizer.records_per_buffer(10)
digitizer.number_of_records(100)
digitizer.configure_buffers()


t = np.linspace(0, 255, 256)
Omega = 2 * np.pi * 31.25e6
WA = np.cos(Omega * t)
WB = np.sin(Omega * t)

start = time.time()
digitizer.acquire_data()
iqs = digitizer.get_iqs(WA, WB)
data = digitizer.get_records()
y = data[0][1]
x = []
y_noUnits = []
for ii in range(0, len(y)):
    x.append(float(ii))
    y_noUnits.append(y[ii]['V'])

import matplotlib.pyplot as plt
import numpy as np
#print y
#x = np.arange(sample)
#y = np.sin(2 * np.pi * f * x / Fs)
plt.plot(x,y_noUnits)
plt.xlabel('voltage(V)')
plt.show()

stop = time.time()
print('Executions time: %f seconds.' %(stop-start))