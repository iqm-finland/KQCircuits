KLayout macros for microwave circuits.

# Installation of KQCircuit

## Recuirements
Tested with 
* Python 3.5.2, 
* KLayout 0.25.6

Required packages
* numpy

## Linux
Typical location for local macros, which you can edit:
```
    ~/.klayout/pymacros
```

Command to run KLayout:
```
    LD_LIBRARY_PATH=. ./klayout -e
```
tha path should point to the directory of the build directory. In my case 
```
    ~/Software/klayout-0.25.6/bin-release
```
which contains files `klayout` and `libkaylayout*.so`

## Windows
Typical location for local checkout:
```
	~/KLayout/python/kqcircuit 
```

# Installation of KLayout with python support
## Linux
Python 3.* is usually available out of box, but the latest KLayout has to be built from source. In Aalto one should built it into userspace without using `sudo`.


## Windows
Python has to be availble in the path of linked in KLayout python path. See KLayout doc.

