from typing import List

import numpy as np


class BaseConfig:
    # 6 nautical miles = 11112,066 meters
    # 5 nautical miles = 9260,005 meters
    # 4 nautical miles = 7408,004 meters
    # 3 nautical miles = 5556,003 meters
    # 2 nautical miles = 3704,002 meters
    KNOT_TO_MS_CONVERSION = 0.5144447  # 1 knot in metres per second
    N_MILE_TO_M_CONVERSION = 1852.001  # 1 nautical miles in metres

    BOW_ANGLE = np.radians(10.0)
    STERN_ANGLE = np.radians(135)
    SIDE_ANGLE = np.radians(112.5)
    BEAM_ROTATION_ANGLE = SIDE_ANGLE / 2

    HALF_BOW_ANGLE = BOW_ANGLE / 2
    HALF_SIDE_ANGLE = SIDE_ANGLE / 2
    HALF_STERN_ANGLE = STERN_ANGLE / 2

    EPSILON = 1e-10

    ONE_MINUTE_IN_SEC = 60
    FOUR_MINUTES_IN_SEC = 4 * ONE_MINUTE_IN_SEC
    ONE_HOUR_IN_SEC = 60 * ONE_MINUTE_IN_SEC
    TWO_HOURS_IN_SEC = 2 * ONE_HOUR_IN_SEC
    TEN_MINUTE_IN_SEC = 10 * ONE_MINUTE_IN_SEC
    TWENTY_MINUTE_IN_SEC = 20 * ONE_MINUTE_IN_SEC
    ONE_DAY_IN_SEC = 24 * ONE_HOUR_IN_SEC

    TWO_N_MILE = 2 * N_MILE_TO_M_CONVERSION

    VISIBILITY_DIST_2 = 2 * N_MILE_TO_M_CONVERSION
    VISIBILITY_DIST_3 = 3 * N_MILE_TO_M_CONVERSION
    VISIBILITY_DIST_5 = 5 * N_MILE_TO_M_CONVERSION
    VISIBILITY_DIST_6 = 6 * N_MILE_TO_M_CONVERSION

    MIN_HEADING = -np.pi
    MAX_HEADING = np.pi


class WaraPsConfig(BaseConfig):
    MIN_BEAM = 0.5
    MAX_BEAM = 0.5
    MIN_OBSTACLE_RADIUS = 0.1
    MAX_OBSTACLE_RADIUS = 10.0

    OS_VESSEL_TYPE = "MiniUSV"
    VALID_VESSEL_TYPES = ["MiniUSV"]
    VALID_STATIC_OBSTACLE_TYPES = []

    DIST_DRIFT = 1.0  # meter
    MIN_COORD = 0.0
    MAX_COORD = 0.5 * BaseConfig.N_MILE_TO_M_CONVERSION  # 926 m
    OS_COORD = MAX_COORD / 2
    MAX_DISTANCE = MAX_COORD * np.sqrt(2)
    MAX_TEMPORAL_DISTANCE = BaseConfig.ONE_HOUR_IN_SEC
    SAFE_TEMPORAL_DISTANCE = BaseConfig.TEN_MINUTE_IN_SEC

    MIN_LENGTH = 1.0
    MAX_LENGTH = 1.0
    MIN_SPEED_IN_MS = 0.2  # m/s
    MAX_SPEED_IN_MS = 2.0  # m/s


class GeneralMaritimeConfig(BaseConfig):
    MIN_BEAM = 2.0
    MAX_BEAM = 80.0
    MIN_OBSTACLE_RADIUS = 10.0
    MAX_OBSTACLE_RADIUS = 400.0

    OS_VESSEL_TYPE = "OSPassengerShip"
    VALID_VESSEL_TYPES = ["OtherType"]
    VALID_STATIC_OBSTACLE_TYPES = ["OtherType"]

    DIST_DRIFT = 50.0  # meter
    MIN_COORD = 0.0
    MAX_COORD = 2.0 * 6.5 * BaseConfig.N_MILE_TO_M_CONVERSION  # 24076.013 m
    OS_COORD = MAX_COORD / 2
    MAX_DISTANCE = MAX_COORD * np.sqrt(2)  # 34048.624 m
    MAX_TEMPORAL_DISTANCE = BaseConfig.TWO_HOURS_IN_SEC
    SAFE_TEMPORAL_DISTANCE = BaseConfig.TWENTY_MINUTE_IN_SEC

    MIN_LENGTH = 10.0
    MAX_LENGTH = 400.0
    MIN_SPEED_IN_MS = 0.2 * BaseConfig.KNOT_TO_MS_CONVERSION
    MAX_SPEED_IN_MS = 50.0 * BaseConfig.KNOT_TO_MS_CONVERSION


class GlobalConfig(GeneralMaritimeConfig):
    pass


# class GlobalConfig(WaraPsConfig):
#     pass


def vessel_radius(length: float) -> float:
    return length * 4


def o2VisibilityByo1(o1_sees_o2_stern: bool, o2_length: float) -> float:
    if o1_sees_o2_stern:
        if o2_length < 5:
            return (
                o2_length / 50 * GlobalConfig.VISIBILITY_DIST_2
            )  # MADE UP FOR WARA-PS
        elif o2_length < 50:
            return GlobalConfig.VISIBILITY_DIST_2
        else:
            return GlobalConfig.VISIBILITY_DIST_3
    else:
        if o2_length < 5:
            return (
                o2_length / 50 * GlobalConfig.VISIBILITY_DIST_5
            )  # MADE UP FOR WARA-PS
        elif o2_length < 12:
            return GlobalConfig.VISIBILITY_DIST_2
        elif o2_length < 20:
            return GlobalConfig.VISIBILITY_DIST_3
        elif o2_length < 50:
            return GlobalConfig.VISIBILITY_DIST_5
        else:
            return GlobalConfig.VISIBILITY_DIST_6


def possible_vis_distances_by_length(length1, length2):
    return [
        min(o2VisibilityByo1(True, length1), o2VisibilityByo1(True, length2)),
        min(o2VisibilityByo1(True, length1), o2VisibilityByo1(False, length2)),
        min(o2VisibilityByo1(False, length1), o2VisibilityByo1(True, length2)),
        min(o2VisibilityByo1(False, length1), o2VisibilityByo1(False, length2)),
    ]


def possible_vis_distances_by_bearing(o2_sees_o1_stern, o1_sees_o2_stern):
    if o1_sees_o2_stern or o2_sees_o1_stern:
        return [
            GlobalConfig.VISIBILITY_DIST_2,
            GlobalConfig.VISIBILITY_DIST_3,
            GlobalConfig.VISIBILITY_DIST_2,
            GlobalConfig.VISIBILITY_DIST_3,
        ]
    else:
        return [
            GlobalConfig.VISIBILITY_DIST_2,
            GlobalConfig.VISIBILITY_DIST_3,
            GlobalConfig.VISIBILITY_DIST_5,
            GlobalConfig.VISIBILITY_DIST_6,
        ]


def possible_vis_distances_by_length(length1, length2):
    return [
        min(o2VisibilityByo1(True, length1), o2VisibilityByo1(True, length2)),
        min(o2VisibilityByo1(True, length1), o2VisibilityByo1(False, length2)),
        min(o2VisibilityByo1(False, length1), o2VisibilityByo1(True, length2)),
        min(o2VisibilityByo1(False, length1), o2VisibilityByo1(False, length2)),
    ]


def vis_distance(o2_sees_o1_stern, length1, o1_sees_o2_stern, length2):
    return min(
        o2VisibilityByo1(o2_sees_o1_stern, length1),
        o2VisibilityByo1(o1_sees_o2_stern, length2),
    )


# FOR FUTURE WORK
# Table 1: Approximated minimum spacing for Coldwell's domain if ownship's length and beam are L1 and B1, and target's length and beam are L2 and B2, respectively.

# Encounter/Safety Condition                      | Own Domain Not Violated | Target's Domain Not Violated | Neither Domain is Violated | Domains Not Overlapping
# ---------------------------------------------------------------------------------------------------------------------------
# Head-on (port to a target)                      | 1.75L1 - 0.5B1          | 1.75L2 - 0.5B2              | 1.75L2 - 0.5B2            | 1.75L1 - 0.5B1 + 1.75L2 - 0.5B2
# Head-on (starboard to a target)                 | 3.25L1 - 0.5B1          | 3.25L2 - 0.5B2              | 3.25L2 - 0.5B2            | 3.25L1 - 0.5B1 + 3.25L2 - 0.5B2
# Crossing ahead of a target on starboard         | 3.25L1 - 0.5B1          | 6.1L2 - 0.5L2               | 6.1L2 - 0.5L2             | 3.25L1 - 0.5B1 + 6.1L2 - 0.5L2
# Crossing astern of a target from starboard      | 1.75L1 - 0.5B1          | 3.9L2 - 0.5L2               | 3.9L2 - 0.5L2             | 1.75L1 - 0.5B1 + 3.9L2 - 0.5L2
# Crossing ahead of a target on port              | 1.75L1 - 0.5B1          | 6.1L2 - 0.5L2               | 6.1L2 - 0.5L2             | 1.75L1 - 0.5B1 + 6.1L2 - 0.5L2
# Crossing astern of a target from port           | 3.25L1 - 0.5B1          | 3.9L2 - 0.5L2               | 3.9L2 - 0.5L2             | 3.25L1 - 0.5B1 + 3.9L2 - 0.5L2
# Overtaking (port to a target or starboard)      | 1.75L1 - 0.5B1          | 1.75L2 - 0.5B2              | 1.75L2 - 0.5B2            | 1.75L1 - 0.5B1 + 1.75L2 - 0.5B2
