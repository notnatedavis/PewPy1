#   src/setup.py
#   Setup configuration for installation and distribution

# ----- Imports ----- #
from setuptools import setup, find_packages
import os
import sys
# check Python version
if sys.version_info < (3, 13) :
    sys.exit("PewPy requires Python 3.13 or higher (due to multithreading)")

def read_requirements() :
    # Read requirements from requirements.txt
    requirements = []
    try : 
        with open('requirements.txt', 'r') as f :
            for line in f :
                line = line.strip()
                if line and not line.startswith('#') :
                    # handle platform-specific dependencies
                    if ';' in line :
                        line = line.split(';')[0].strip()
                   requirements.append(line)
    except FileNotFoundError :
        print("[warning] requirements.txt not found")
    return requirements

setup(
    name="PewPy",
    author="@notnatedavis",
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    python_requires=">=3.13",
    install_requires=read_requirements(),
    include_package_data=True,
)