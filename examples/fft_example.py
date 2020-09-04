from Rigol1000z import Rigol1000z
from time import sleep
from Rigol1000z.constants import *
from numpy.fft import rfftfreq, rfft
import numpy as np
from typing import List
import matplotlib.pyplot as plt

if __name__ == '__main__':
    # Create oscilloscope interface using with statement!
    with Rigol1000z() as osc:
        # osc.ieee488.reset()  # start with known state by restoring default settings
        # osc.autoscale()
        osc.run()

        sleep(1.0)

        capt = osc.get_capture(EWaveformMode.Raw)  # , "./waveform_fft.csv")  # Collect waveform data

        # print(f"data_type: {type(data)}, data: {data}")
        for ch_wf in capt.waveforms.values():
            # Setup figure
            fig, axs = plt.subplots(4, 1, constrained_layout=True)

            # Get the x-axis time series values and total period
            time_series = capt.to_timebase(ch_wf.wf_data.size)
            capture_period = (time_series[-1] - time_series[0])
            sample_period = capture_period / time_series.size

            # Plot the captureed waveform
            axs[0].plot(time_series, ch_wf.to_float_amplitude_array())

            # Plot the captured waveform with the windowing function applied
            axs[1].plot(time_series, np.hanning(ch_wf.wf_data.size) * ch_wf.to_float_amplitude_array())

            # Define a function to calculate the magnitude of a complex number
            mag_funct = lambda x: np.sqrt(x.real ** 2 + x.imag ** 2)  # Report me to the pep8 police

            # Calculate the x axis frequency values
            freq_bin_centers = rfftfreq(ch_wf.wf_data.size, sample_period)

            # Calculate fft
            freq_data = mag_funct(
                # Calculate the fourier transform after applying the windowing function
                rfft(np.hanning(ch_wf.wf_data.size) * ch_wf.to_float_amplitude_array())
            )

            # Plot the fft as a line graph
            axs[2].plot(freq_bin_centers, freq_data)
            axs[2].set_yscale('log')
            axs[2].set_xscale('log')

            # Plot the magnitude_spectrum
            axs[3].magnitude_spectrum(
                ch_wf.to_float_amplitude_array(),  # Pass the waveform directly to this plotting function
                1.0 / sample_period,
                scale='dB'
            )
            axs[3].set_xscale('log')

            # Show the plot
            plt.show()
