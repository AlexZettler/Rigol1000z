# Rigol1000z
Python library to interface with Rigol DS1000z series oscilloscopes.

The interface uses the VISA communication protocol implemented in (PyVISA) and supports both USB and Ethernet.

## Platforms
* Windows 10 - Tested
* ArchLinux - when forked, [@jeanyvesb9](https://github.com/jeanyvesb9/Rigol1000z) stated his version worked with Arch, so I suspect compatibility.

## Dependencies
* [python3.7](https://www.python.org/downloads/release)+ Python version as f-strings are used in the library
* [numpy](https://github.com/numpy/numpy) Library for efficient storage and processing of arrays
* [pyvisa](https://github.com/pyvisa/pyvisa) Visa communication protocol
* [tqdm](https://github.com/tqdm/tqdm) Command line progress bar

## Recommended
* [pipenv](https://pypi.org/project/pipenv/)
makes installation of requirements easier and separates python environments reducing the probability of package dependency conflicts.
To install run the following commands from your working directory 

```bash
pip install pipenv
pipenv install
```

## Example
```python
from Rigol1000z import Rigol1000z
from time import sleep
from Rigol1000z.constants import *

# Create oscilloscope interface using with statement!
with Rigol1000z() as osc:
    osc.ieee488.reset()  # start with known state by restoring default settings

    # osc.autoscale()  # Autoscale the scope

    # Set the horizontal timebase
    osc.timebase.mode = ETimebaseMode.Main  # Set the timebase mode to main (normal operation)
    osc.timebase.scale = 10 * 10 ** -6  # Set the timebase scale

    # Go through each channel
    for i in range(1, 5):
        osc[i].enabled = True  # Enable the channel
        osc[i].scale_v = 1000e-3  # Change voltage range of the channel to 1.0V/div.

    osc[2].invert = True  # Invert the channel

    osc.run()  # Run the scope if not already
    sleep(0.5)  # Let scope collect the waveform

    osc.stop()  # Stop the scope in order to collect data.

    # Take a screenshot of the scope's display
    osc.get_screenshot('./screenshot.png')

    # Collect and save waveform data from all enabled channels
    tb, data = osc.get_data(
        channels=(1,),
        mode=EWaveformMode.Raw,
        filename='./channels.csv'
    )

    osc.run()  # Move back to run mode when data collection is complete
```

## Acknowledgements
Based on the original work by [@jtambasco](https://github.com/jtambasco/RigolOscilloscope) which was further developed by [@jeanyvesb9](https://github.com/jeanyvesb9/Rigol1000z).

I have heavily modified the work to be closer to a full implementation of a Rigol1000z library.

My goal for the rewrite has been to make the device as easy as possible to control by:
* Type hinting function parameters, and return values.
* Developing a command hierarchy as it is found in the Rigol programming manual and adding docstrings describing the effect of the function.
* Implementing most set/get commands as properties and related setters for a more organic device interface.
* Defining discrete string constants separately so that autocompletion of constants can be preformed from the corresponding enumeration class

## Feedback/Contributing
I began this project to create the best library to control the Rigol1000z series of scopes.
This is a huge project and I suspect there will be issues with some commands.

If any issues are discovered, please submit an issue to the [issues page](https://github.com/AlexZettler/Rigol1000z/issues)
with the oscilloscope model you are using, and code you were running. 

Feedback will keep this project growing and I encourage all suggestions.

## Contributing
There are menus that aren't yet implemented completely. If you would like to implement one of these menus feel free to submit a pull request.

If you are having an issue and want to fix it, please create the issue first with the model and code so that problems are addressed and tracked properly :)