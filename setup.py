from setuptools import find_packages, setup

from os import path

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='Rigol1000z-remote',
    version='0.3.1',
    author="Alexander Zettler(@AlexZettler), @jeanyvesb9, @jtambasco",
    author_email="azettler@live.com",
    description="Python VISA (USB and Ethernet) library for interface with Rigol DS1000z series oscilloscopes.",
    long_description=long_description,
    long_description_content_type='text/markdown',
    url="https://github.com/AlexZettler/Rigol1000z",
    packages=[
        'Rigol1000z'
        # 'rigol1000z',
        # 'rigol1000zcommandmenu',
        # 'commands',
        # 'constants'
    ],
    install_requires=[
        "tqdm",
        "numpy",
        "pyvisa",
        "pyvisa-py",
    ],
    classifiers=[
        'Programming Language :: Python :: 3.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Hardware :: Hardware Drivers'
    ]
)
