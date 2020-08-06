import pyvisa
from Rigol1000z import Rigol1000z
from time import sleep
from Rigol1000z.constants import *
from numpy.fft import fftfreq, fft
import numpy as np
from typing import List
import matplotlib.pyplot as plt

# Create oscilloscope interface using with statement!
with Rigol1000z() as osc:
    osc.ieee488.reset()  # start with known state by restoring default settings

    osc.run()
    osc.autoscale()

    tb, data = osc.get_data((1,), EWaveformMode.Raw)  # , "./waveform_fft.csv")  # Collect waveform data
    tb: np.ndarray = tb
    data: List[np.ndarray] = data

    # Setup figure
    fig: plt.Figure = plt.figure(6)

    ax: plt.Axes = fig.add_subplot(2, 1, 1)
    signal_graph = ax.plot(tb, data[0])

    capture_period = (tb[-1] - tb[0])
    # print(capture_period)

    sample_period = capture_period / tb.size
    # print(type(sample_period))

    freq_data: np.ndarray = fft(data[0])[:int(data[0].size / 2) - 1]
    freq_bin_centers = fftfreq(data[0].size, sample_period)[:int(data[0].size / 2) - 1]
    # print(f"{freq_bin_centers[0]}, {freq_bin_centers[int(freq_bin_centers.size/2)-1]}")
    # print(type(freq_bin_centers))

    # calculate the magnitude of the complex number returned
    comp_mag = lambda x: np.sqrt(x.real ** 2 + x.imag ** 2)
    freq_data = comp_mag(freq_data)

    # ax: plt.Axes = fig.add_subplot(2, 1, 2)
    # freq_graph = ax.plot(freq_bin_centers, freq_data)
    # ax.set_yscale('log')
    # ax.set_xscale('log')

    # Plot the magnitude_spectrum
    ax: plt.Axes = fig.add_subplot(2, 1, 2)
    freq_graph = ax.magnitude_spectrum(data[0], 1 / sample_period, scale='dB')
    ax.set_xscale('log')
    # ax.set_xlim(left=1)
    # ax.set_ylim(bottom=-50.0)

    plt.show()
