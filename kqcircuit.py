import pya
import os
from kqcircuit.pcells.waveguide_cop import WaveguideCopStreight
from kqcircuit.pcells.waveguide_cop import WaveguideCopCurve
from kqcircuit.pcells.waveguide_cop import WaveguideCop
from kqcircuit.pcells.finger_capacitor import FingerCapacitor
from kqcircuit.pcells.meander import MeanderCenter
from kqcircuit.pcells.swissmon import Swissmon
from kqcircuit.pcells.launcher import Launcher
from kqcircuit.pcells.chips.chip_base import ChipBase
from kqcircuit.pcells.chips.demo import DemoChip

import kqcircuit.defaults 


import sys
import inspect
from importlib import reload

reload(kqcircuit.defaults)
reload(sys.modules[Swissmon.__module__])
reload(sys.modules[WaveguideCop.__module__])
reload(sys.modules[WaveguideCopCurve.__module__])
reload(sys.modules[ChipBase.__module__])
reload(sys.modules[Launcher.__module__])
reload(sys.modules[DemoChip.__module__])
reload(sys.modules[MeanderCenter.__module__])
reload(sys.modules[FingerCapacitor.__module__])


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
        
    # Load fixed library cells
    self.path_kqcircuit = os.path.dirname(__file__)    
    self.layout().read(os.path.join(self.path_kqcircuit, "shapes", "squids.oas"))

    # Create the PCell declarations
    self.layout().register_pcell("Waveguide", WaveguideCop())
    self.layout().register_pcell("Waveguide streight", WaveguideCopStreight())
    self.layout().register_pcell("Waveguide curved", WaveguideCopCurve())
    self.layout().register_pcell("Meander", MeanderCenter())
    self.layout().register_pcell("Swissmon", Swissmon())
    self.layout().register_pcell("FingerCap", FingerCapacitor())
    self.layout().register_pcell("TJunction", WaveguideCopCurve())
    self.layout().register_pcell("Launcher", Launcher())
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
    self.layout().register_pcell("Demo", DemoChip())
    self.layout().register_pcell("Base", ChipBase())

    self.register("KQChip")

# Instance the libraries 
KQCircuitLibrary()
KQChipLibrary()
