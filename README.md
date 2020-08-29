# Rigol1000z
Python library for interfacing with [Rigol's DS1000z](https://www.rigolna.com/products/digital-oscilloscopes/1000z/) series of oscilloscopes.

## Features
* Uses the VISA communication protocol implemented in ([PyVISA]((https://github.com/pyvisa/pyvisa))) which supports both USB and Ethernet communication protocols.
* Capture and Waveform objects with:
    * Builtin graphing functions.
    * SQLite database writing/reading for use in testing that requires a large number of waveforms to be captured.

## Dependencies
* [python3.7+](https://www.python.org/downloads/release) Python version as f-strings are used in the library
* [numpy](https://github.com/numpy/numpy) Library for efficient storage and processing of arrays
* [pyvisa](https://github.com/pyvisa/pyvisa) Visa communication protocol
* [tqdm](https://github.com/tqdm/tqdm) Command line progress bar

## Optional Dependencies
* [plotly](https://pypi.org/project/plotly/) - graphing library
* [matplotlib](https://pypi.org/project/matplotlib/) - graphing library

## Recommended
* [pipenv](https://pypi.org/project/pipenv/)
makes installation of requirements easier and separates python environments reducing the probability of package dependency conflicts.
To install run the following commands from your working directory 

```bash
pip install pipenv
pipenv install
```

## Platforms
* Windows 10 - Tested
* ArchLinux - when forked, [@jeanyvesb9](https://github.com/jeanyvesb9/Rigol1000z) stated his version worked with Arch, so I suspect compatibility.

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
## Code standards
To ensure the quality of the codebase I have been adhering to a few general rules:
* Pep8 is to be followed.
* All function parameters and return values should be typed as proposed through [pep484](https://www.python.org/dev/peps/pep-0484/) and [pep484](https://www.python.org/dev/peps/pep-0484/):
    * This has a number of benefits:
        * Allows editors to provide correct attribute auto-completion
        * Ensures predictable behavior from functions that are passed values
    * This is ensured through the following:
        * MyPy is used to check type adherence.
        * Tests ensure that types are of correct values when functions from external libraries without typing are called.
   
* Tests are good things to have to ensure that the system behaves as intended.
    * Tests are currently lacking but will be implemented in the future.
* Documentation is key and allows users to use this code quickly and efficiently.
    * [PyDoc3](https://github.com/pdoc3/pdoc) is used to generate HTML API documentation
    * Documentation should adhere to the [google style](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings) to minimize documentation overhead and allow for PyDoc parsing.

## Feedback/Contributing
I began this project to create the best library to control the Rigol1000z series of scopes.
This is a huge project and I suspect there will be issues with some commands.

If any issues are discovered, please submit an issue to the [issues page](https://github.com/AlexZettler/Rigol1000z/issues)
with the oscilloscope model you are using, and code you were running. 

Feedback will keep this project growing and I encourage all suggestions.

## Acknowledgements
Based on the original work by [@jtambasco](https://github.com/jtambasco/RigolOscilloscope) which was further developed by [@jeanyvesb9](https://github.com/jeanyvesb9/Rigol1000z).

Although a fork, the entire has been rewritten with the exception to the name of the Rigol1000z class name and logic responsible for retrieving waveform data.
I have heavily modified the work to be closer to a full implementation of a Rigol1000z library.

My goal for the rewrite has been to make the device as easy as possible to control by:
* Type hinting function parameters, and return values.
* Developing a command hierarchy as it is found in the [Rigol programming manual](https://www.rtelecom.net/userfiles/product_files_shared/Rigol/Oscilloscopes/MSO1000Z/DS1000Z_Programming%20Guide_EN.pdf) and adding docstrings describing the effect of the function.
* Implementing most set/get commands as properties and related setters for a more organic device interface.
* Defining discrete string constants separately so that autocompletion of constants can be preformed from the corresponding enumeration class

## Contributing
There are menus that aren't yet implemented completely. If you would like to implement one of these menus or fix a problem you've been having, feel free to submit a pull request.
