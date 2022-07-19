from typing import Any, Union

from utils import ObservatorySatellite, SatellitePosition, TimeObj, MetaFormatter


class SingleCulmination(metaclass=MetaFormatter):
    """Helper class returned by DayTransits Iterator which stores information about a single culmination"""

    def __init__(self, parent_, start_, culmination_, end_):
        self.parent = parent_
        self.start = start_
        self.culmination = culmination_
        self.end = end_

    @property
    def duration(self) -> float:
        return self.parent.get_duration()

    @property
    def duration_minutes(self) -> float:
        return self.duration / 60.0

    @property
    def threshold(self) -> float:
        return self.parent.threshold


class DayTransits:
    """Helper class which stores the culmination times and associated information"""

    def __init__(self, in_obs_sat: ObservatorySatellite, in_threshold: float):
        self.obs_sat = in_obs_sat
        self.threshold = in_threshold
        self._start = None
        self.culminations = []
        self._end = None

    def __iter__(self) -> SingleCulmination:
        yield from (
            SingleCulmination(self, self.start, culmination, self.end)
            for culmination in self.culminations
        )

    def __repr__(self) -> str:
        return (
            f"<class 'DayTransits': {len(self.culminations)} culminations of "
            f"{self.obs_sat.sat_name} above {self.obs_sat.obs_name}; "
            f"rising above {self.threshold} at {self.start.time} "
            f"and falling below {self.threshold} at {self.end.time}>"
        )

    @property
    def start(self) -> Union[SatellitePosition, None]:
        return self._start

    @start.setter
    def start(self, other: Any) -> None:
        self._start = self.obs_sat.at(TimeObj(other))

    @property
    def end(self) -> Union[SatellitePosition, None]:
        return self._end

    @end.setter
    def end(self, other: Any) -> None:
        self._end = self.obs_sat.at(TimeObj(other))

    def add(self, in_time: Any) -> int:
        in_time = TimeObj(in_time, in_local_tz=self._start.time.local_tz)
        if self.start.time <= in_time <= self.end.time:
            self.culminations.append(self.obs_sat.at(in_time))
            self.culminations.sort(key=lambda x: x.time)
            return 1
        return -1

    def get_duration(self) -> float:
        return (self.end.time - self.start.time).total_seconds()
