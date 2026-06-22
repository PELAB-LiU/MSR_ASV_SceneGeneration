from abc import ABC
from dataclasses import dataclass
from typing import Dict

from global_config import GlobalConfig

"""
Ship types:
tanker, MMSI: 413474690 : 93 x 17 m
tanker, MMSI: 412377520 : 146 x 21 m
tanker, MMSI: 413441230 : 82 x 12 m
tanker, MMSI: 413697340 : 96 x 16 m

container, MMSI: 413146000 : 263 x 32 m
container, MMSI: 412713000 : 294 x 32 m
container, MMSI: 212602000 : 259 x 32 m

cargo vessel, MMSI: 413700110 : 159 x 23 m
cargo vessel, MMSI: 412766340 : 179 x 28 m

High Speed Craft, MMSI: 477937400 : 47 x 12 m
High Speed Craft, MMSI: 477937500 : 47 x 12 m
High Speed Craft, MMSI: 477937200 : 47 x 12 m
High Speed Craft, MMSI: 477525000 : 40 x 15 m
High Speed Craft, MMSI: 477385000 :	45 x 12 m

Passenger ship, MMSI: 477995974 : 25 x 8 m
Passenger ship, MMSI: 477995293 : 30 x 8 m

"""


@dataclass(frozen=True, repr=False)
class VesselType(ABC):
    name: str = "VesselType"
    min_length: float = GlobalConfig.MIN_LENGTH
    max_length: float = GlobalConfig.MAX_LENGTH
    min_speed: float = GlobalConfig.MIN_SPEED_IN_MS
    max_speed: float = GlobalConfig.MAX_SPEED_IN_MS
    min_beam: float = GlobalConfig.MIN_BEAM
    max_beam: float = GlobalConfig.MAX_BEAM

    def do_match(self, length: float, speed: float, beam=None) -> bool:
        return (
            self.min_length - GlobalConfig.EPSILON
            <= length
            <= self.max_length + GlobalConfig.EPSILON
            and self.min_speed - GlobalConfig.EPSILON
            <= speed
            <= self.max_speed + GlobalConfig.EPSILON
            and (
                beam is None
                or self.min_beam - GlobalConfig.EPSILON
                <= beam
                <= self.max_beam + GlobalConfig.EPSILON
            )
        )

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name

    @property
    def is_unspecified(self) -> bool:
        return False


@dataclass(frozen=True, repr=False)
class UnspecifiedVesselType(VesselType):
    name: str = "UnspecifiedType"

    @property
    def is_unspecified(self) -> bool:
        return True


@dataclass(frozen=True, repr=False)
class OtherVesselType(VesselType):
    name: str = "OtherType"
    pass


@dataclass(frozen=True, repr=False)
class MiniUSV(VesselType):
    name: str = "MiniUSV"
    min_length: float = GlobalConfig.MIN_LENGTH
    max_length: float = GlobalConfig.MAX_LENGTH
    min_speed: float = GlobalConfig.MIN_SPEED_IN_MS
    max_speed: float = GlobalConfig.MAX_SPEED_IN_MS
    min_beam: float = GlobalConfig.MIN_BEAM
    max_beam: float = GlobalConfig.MAX_BEAM


@dataclass(frozen=True, repr=False)
class CargoShip(VesselType):
    name: str = "CargoShip"
    min_length: float = 50
    max_length: float = 400
    max_speed: float = 25 * GlobalConfig.KNOT_TO_MS_CONVERSION
    min_beam: float = 10
    max_beam: float = 60


@dataclass(frozen=True, repr=False)
class Tanker(VesselType):
    name: str = "Tanker"
    min_length: float = 60
    max_length: float = 350
    max_speed: float = 20 * GlobalConfig.KNOT_TO_MS_CONVERSION
    min_beam: float = 10
    max_beam: float = 60


@dataclass(frozen=True, repr=False)
class ContainerShip(VesselType):
    name: str = "ContainerShip"
    min_length: float = 100
    max_length: float = 400
    max_speed: float = 25 * GlobalConfig.KNOT_TO_MS_CONVERSION
    min_beam: float = 15
    max_beam: float = 65


@dataclass(frozen=True, repr=False)
class PassengerShip(VesselType):
    name: str = "PassengerShip"
    min_length: float = 20
    max_length: float = 350
    max_speed: float = 40 * GlobalConfig.KNOT_TO_MS_CONVERSION
    min_beam: float = 5
    max_beam: float = 50


@dataclass(frozen=True, repr=False)
class OSPassengerShip(VesselType):
    name: str = "OSPassengerShip"
    min_length: float = 30.0
    max_length: float = 30.0
    max_speed: float = 40.0 * GlobalConfig.KNOT_TO_MS_CONVERSION
    min_beam: float = 10.0
    max_beam: float = 10.0


@dataclass(frozen=True, repr=False)
class FishingShip(VesselType):
    name: str = "FishingShip"
    min_length: float = 2
    max_length: float = 100
    max_speed: float = 15 * GlobalConfig.KNOT_TO_MS_CONVERSION
    min_beam: float = 2
    max_beam: float = 20


@dataclass(frozen=True, repr=False)
class MotorVessel(VesselType):
    name: str = "MotorVessel"
    min_length: float = 10
    max_length: float = 370
    max_speed: float = 30 * GlobalConfig.KNOT_TO_MS_CONVERSION
    min_beam: float = 3
    max_beam: float = 80


@dataclass(frozen=True, repr=False)
class SailingVessel(VesselType):
    name: str = "SailingVessel"
    min_length: float = 5
    max_length: float = 60
    max_speed: float = 20 * GlobalConfig.KNOT_TO_MS_CONVERSION
    min_beam: float = 2
    max_beam: float = 12


@dataclass(frozen=True, repr=False)
class MilitaryVessel(VesselType):
    name: str = "MilitaryVessel"
    min_length: float = 20
    max_length: float = 300
    max_speed: float = 50 * GlobalConfig.KNOT_TO_MS_CONVERSION
    min_beam: float = 5
    max_beam: float = 40


# ALL_VESSEL_TYPES : List[VesselType] = [OtherVesselType(), Tanker(), CargoShip(), ContainerShip(), PassengerShip(), FishingShip(), MotorVessel(), SailingVessel(), MilitaryVessel()]
ALL_VESSEL_TYPES: Dict[str, VesselType] = {
    "OtherType": OtherVesselType(),
    "MiniUSV": MiniUSV(),
    "CargoShip": CargoShip(),
    "Tanker": Tanker(),
    "ContainerShip": ContainerShip(),
    "PassengerShip": PassengerShip(),
    "FishingShip": FishingShip(),
    "MotorVessel": MotorVessel(),
    "SailingVessel": SailingVessel(),
    "MilitaryVessel": MilitaryVessel(),
    "OSPassengerShip": OSPassengerShip(),
    "UnspecifiedType": UnspecifiedVesselType(),
}

DEFAULT_VESSEL_TYPE = UnspecifiedVesselType()
