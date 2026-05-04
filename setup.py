#   setup.py

# ----- Imports ----- #
from setuptools import setup, find_packages
import sys
if sys.version_info < (3, 13):
    sys.exit("PewPy requires Python 3.13 or higher")

# ----- Main Class ----- #
def read_requirements() :
    reqs = []
    try :
        with open('requirements.txt', 'r') as f :
            for line in f :
                line = line.strip()
                if line and not line.startswith('#') :
                    if ';' in line :
                        line = line.split(';')[0].strip()
                    reqs.append(line)
    except FileNotFoundError :
        print("[warning] requirements.txt not found")
    return reqs

setup(
    name="PewPy",
    author="@notnatedavis",
    packages=find_packages(),
    python_requires=">=3.13",
    install_requires=read_requirements(),
    include_package_data=True,
    # config files are not part of the package; kept as external resources
)