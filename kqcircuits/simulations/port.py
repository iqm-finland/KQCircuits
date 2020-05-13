from kqcircuits.pya_resolver import pya
DPoint = pya.DPoint


class Port:
    """
    Base data structure for simulation ports.
    """
    def __init__(self, number: int,
                 resistance: float = 50, reactance: float = 0, inductance: float = 0, capacitance: float = 0):
        self.number = number
        self.resistance = resistance
        self.reactance = reactance
        self.inductance = inductance
        self.capacitance = capacitance
        self.type = type(self).__name__

    def as_dict(self):
        return vars(self)


class InternalPort(Port):
    """
    Data structure for ports inside the simulation area
    """
    def __init__(self, number: int, signal_location: DPoint, ground_location: DPoint,
                 resistance: float = 50, reactance: float = 0, inductance: float = 0, capacitance: float = 0):
        super().__init__(number, resistance, reactance, inductance, capacitance)
        self.signal_location = signal_location
        self.ground_location = ground_location


class EdgePort(Port):
    """
    Data structure for ports at the edge of the simulation area
    """
    def __init__(self, number: int, signal_location: DPoint,
                 resistance: float = 50, reactance: float = 0, inductance: float = 0, capacitance: float = 0):
        super().__init__(number, resistance, reactance, inductance, capacitance)
        self.signal_location = signal_location