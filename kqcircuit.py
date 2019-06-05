import pya
import os
from kqcircuit.pcells.waveguide_cop import WaveguideCopStreight
from kqcircuit.pcells.waveguide_cop import WaveguideCopCurve
from kqcircuit.pcells.waveguide_cop import WaveguideCop
from kqcircuit.pcells.waveguide_cop import WaveguideCopTCross
from kqcircuit.pcells.finger_capacitor import FingerCapacitorTapered
from kqcircuit.pcells.finger_capacitor import FingerCapacitorSquare
from kqcircuit.pcells.meander import MeanderCenter
from kqcircuit.pcells.swissmon import Swissmon
from kqcircuit.pcells.launcher import Launcher
from kqcircuit.pcells.marker import Marker
from kqcircuit.pcells.chips.chip_base import ChipBase
from kqcircuit.pcells.chips.demo import DemoChip
from kqcircuit.pcells.chips.ab_crossings import ABCrossings
from kqcircuit.pcells.chips.qfactor import ChipQFactor
from kqcircuit.pcells.chips.photonshaping import ChipShaping
from kqcircuit.pcells.airbridge import AirBridge
from kqcircuit.pcells.teststructures.airbridge_dc import AirBridgeDC

import kqcircuit.defaults 

import sys
import inspect
from importlib import reload


reload(kqcircuit.defaults)
reload(sys.modules[Swissmon.__module__])
reload(sys.modules[AirBridge.__module__])
reload(sys.modules[AirBridgeDC.__module__])
reload(sys.modules[WaveguideCopCurve.__module__])
reload(sys.modules[WaveguideCop.__module__])
reload(sys.modules[WaveguideCopTCross.__module__])
reload(sys.modules[ChipBase.__module__])
reload(sys.modules[Launcher.__module__])
reload(sys.modules[DemoChip.__module__])
reload(sys.modules[ChipShaping.__module__])
reload(sys.modules[Marker.__module__])
reload(sys.modules[ChipQFactor.__module__])
reload(sys.modules[ABCrossings.__module__])
reload(sys.modules[MeanderCenter.__module__])
reload(sys.modules[FingerCapacitorTapered.__module__])
reload(sys.modules[FingerCapacitorSquare.__module__])


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
    self.layout().register_pcell("Waveguide cross", WaveguideCopTCross())
    self.layout().register_pcell("Meander", MeanderCenter())
    self.layout().register_pcell("Airbridge", AirBridge())
    self.layout().register_pcell("Airbridge DC test", AirBridgeDC())
    self.layout().register_pcell("Swissmon", Swissmon())
    self.layout().register_pcell("Marker", Marker())
    self.layout().register_pcell("FingerCapT", FingerCapacitorTapered())
    self.layout().register_pcell("FingerCapS", FingerCapacitorSquare())
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
    self.layout().register_pcell("ABCrossings", ABCrossings())
    self.layout().register_pcell("Chip QFactor", ChipQFactor())
    self.layout().register_pcell("PhotonShaping", ChipShaping())

    self.register("KQChip")

# Instance the libraries 
KQCircuitLibrary()
KQChipLibrary()
