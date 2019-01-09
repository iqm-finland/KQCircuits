import pya
from kqcircuit.pcells.waveguide_cop import WaveguideCopStreight
from kqcircuit.pcells.waveguide_cop import WaveguideCopCurve
from kqcircuit.pcells.waveguide_cop import WaveguideCop
from kqcircuit.pcells.chips.chip_base import ChipBase
from kqcircuit.pcells.chips.test import TestChip


import sys
import inspect
from importlib import reload
reload(sys.modules[WaveguideCop.__module__])
reload(sys.modules[WaveguideCopCurve.__module__])
reload(sys.modules[ChipBase.__module__])
reload(sys.modules[TestChip.__module__])


"""
Quantum Circuits in KLayout
"""


class KQCircuitLibrary(pya.Library):
  """
  Quantum Circuits in KLayout
  """

  def __init__(self):
  
    # Set the description
    self.description = "Library for superconducting quantum circuits."
    
    # Create the PCell declarations
    self.layout().register_pcell("Waveguide", WaveguideCop())
    self.layout().register_pcell("Waveguide streight", WaveguideCopStreight())
    self.layout().register_pcell("Waveguide curved", WaveguideCopCurve())
    self.layout().register_pcell("Meander", WaveguideCopCurve())
    self.layout().register_pcell("Swissmon", WaveguideCopCurve())
    self.layout().register_pcell("FingerCap", WaveguideCopCurve())
    self.layout().register_pcell("TJunction", WaveguideCopCurve())
    self.layout().register_pcell("Launcher", WaveguideCopCurve())
    self.layout().register_pcell("Chip base", ChipBase())
    
    self.register("KQCircuit")
    
    

# Instantiate and register the library
KQCircuitLibrary()


class KQChipLibrary(pya.Library):
  """
  Implementation of Quantum Chips in KQCircuits
  """

  def __init__(self):
  
    # Set the description
    self.description = "Implementation of chips using KQCircuits."
    
    # Create the PCell declarations
    self.layout().register_pcell("Test", TestChip())
    
    self.register("KQChip")
    
    

# Instantiate and register the library
KQChipLibrary()
