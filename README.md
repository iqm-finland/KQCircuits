KLayout macros for microwave circuits.

# Installation

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

