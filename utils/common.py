from collections import defaultdict, deque
from datetime import datetime
from itertools import chain
from typing import Iterator, Optional, Sequence

import numpy
import pandas
import yaml
from skyfield.sgp4lib import EarthSatellite
from skyfield.timelib import Time as SkyfieldTime
from skyfield.toposlib import iers2010
from tzlocal import get_localzone

from utils.datafile import make_locally_active_sats
from utils.observatory import Observatories
from utils.satellite import ObservatorySatellite
from utils.time_utils import TimeDeltaObj, TimeObj, get_off_list, today
from utils.transit import DayTransits


def make_bounded_time_list(
    start_time: TimeObj, end_time: TimeObj, step_size: TimeDeltaObj
) -> deque[TimeObj]:
    start = start_time
    end = end_time
    time_list = deque(
        [
            x
            for x in get_off_list(start, end, step_size, 5)
            if ((start < x) and (x < end))
        ]
    )
    time_list.appendleft(start)
    time_list.append(end)
    return time_list


def get_day_transits(
    in_obs_sat: ObservatorySatellite,
    start_time: TimeObj,
    end_time: TimeObj,
    input_alt: float,
) -> Sequence[DayTransits]:
    return find_sat_events(in_obs_sat, start_time, end_time, input_alt)


def get_obs_coord_between(
    in_obs_sat: ObservatorySatellite,
    start_time: TimeObj,
    end_time: TimeObj,
    time_step: TimeDeltaObj,
) -> pandas.DataFrame:
    sf_list: SkyfieldTime = get_off_list(start_time, end_time, time_step, 2)
    toc_list = in_obs_sat.diff.at(sf_list)
    ra, dec, _ = toc_list.radec()
    rv_df = {
        "mjd": sf_list.to_astropy().to_value("mjd"),
        "ra": ra._degrees,
        "dec": dec._degrees,
    }

    alt, az, _ = toc_list.altaz()
    rv_df["alt"] = alt._degrees
    rv_df["az"] = az._degrees

    subpts = iers2010.subpoint(in_obs_sat.sat.at(sf_list))
    rv_df["sub_lat"] = subpts.latitude._degrees
    rv_df["sub_long"] = subpts.longitude._degrees

    return pandas.DataFrame(data=rv_df)


def find_sat_events(
    in_obs_sat: ObservatorySatellite,
    in_start: TimeObj,
    in_end: TimeObj,
    limit_alt: float,
) -> list[DayTransits]:
    event_times, event_flags = in_obs_sat.sat.find_events(
        in_obs_sat.observatory.sf, in_start.sf, in_end.sf, altitude_degrees=limit_alt
    )

    events_zipped = list(zip(event_times, event_flags))
    rv_transits = []
    for time, flag in events_zipped:
        if flag == 0:
            new_transit = DayTransits(in_obs_sat, limit_alt)
            new_transit.start = TimeObj(time, local_tz=in_start.local_tz)
            rv_transits.append(new_transit)

    for time, flag in events_zipped:
        if flag == 2:
            test_time_obj = TimeObj(time, local_tz=in_start.local_tz)
            test_i = 0
            while test_i < len(rv_transits):
                if (
                    (rv_transits[test_i].end is None)
                    or (rv_transits[test_i].end.time < test_time_obj)
                ) and (rv_transits[test_i].start.time < test_time_obj):
                    rv_transits[test_i].end = test_time_obj
                    test_i = 0
                else:
                    test_i += 1

    for test_trans in rv_transits:
        for time, flag in events_zipped:
            if flag == 1:
                test_trans.add(time)

    return rv_transits


class ObservatorySatelliteFactory:
    def __init__(
        self,
        local_tz: str = "UTC",
        reload_sat: bool = True,
        cache_sat: bool = False,
        use_all: bool = False,
        start_date: Optional[str] = "today",
        end_days: float = 120,
        ignore_limit: bool = False,
        tles: Optional[list[str]] = None,
        chain_tles: bool = False,
    ):
        self.start_date: str = start_date
        self.local_tz: str = get_localzone().zone if local_tz == "local" else local_tz
        self.today_utc: TimeObj = today()
        self.start_utc: Optional[TimeObj] = None
        self.end_days: float = end_days
        self.end_utc: Optional[TimeObj] = None
        self.tles: list[str] = (
            ["https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=csv"]
            if tles is None
            else tles
        )
        self.reload_sat: bool = reload_sat
        self.cache_sat: bool = cache_sat
        self.use_all: bool = use_all
        self.ignore_limit: bool = ignore_limit
        self.chain_tles: bool = chain_tles
        self.active_sats: list[EarthSatellite] = []
        self.active_observatories: list[Observatories] = []

        self._sat_list: Optional[
            (list[tuple[TimeObj, float, EarthSatellite]] | list[EarthSatellite])
        ] = None

        self._make_start_utc()
        self._make_active_sats()
        self._make_active_obs()

    def _make_start_utc(self):
        try:
            self.start_utc = TimeObj(
                datetime.strptime(self.start_date, "%Y-%m-%d")
            ).get_start_day()
        except ValueError:
            self.start_utc = self.today_utc.get_start_day()

        self.start_utc.local_tz = self.local_tz
        self.end_utc = self.start_utc + TimeDeltaObj(days=self.end_days)

    def _make_active_sats(self):
        local_active_sats = list(
            chain.from_iterable(
                make_locally_active_sats(
                    self.reload_sat,
                    self.cache_sat,
                    self.use_all,
                    self.ignore_limit,
                    self.start_utc,
                    local_tle,
                )
                for local_tle in self.tles
            )
        )
        uniq_sats = {
            sat.name + "_" + str(sat.model.jdsatepoch): sat for sat in local_active_sats
        }
        self.active_sats = list(uniq_sats.values())

    def _make_active_obs(self) -> None:
        with open("config/obs_data.yaml", "r") as fp:
            obs_data = yaml.load(fp, Loader=yaml.SafeLoader)

        for obs_name in obs_data:
            obs_lat, obs_long, obs_ele = obs_data[obs_name]
            self.active_observatories.append(
                Observatories(
                    float(obs_lat), float(obs_long), float(obs_ele), str(obs_name)
                )
            )

    def _make_sat_list(self):
        if self._sat_list is not None:
            return
        if self.chain_tles:
            organized_sats: defaultdict[str, list[EarthSatellite]] = defaultdict(list)
            for sat in self.active_sats:
                organized_sats[sat.name].append(sat)

            chained_sats: list[tuple[TimeObj, float, EarthSatellite]] = []
            for sat_list in organized_sats.values():
                sat_list = sorted(sat_list, key=lambda x: x.model.jdsatepoch)

                start_dates = [TimeObj(x.epoch, self.local_tz) for x in sat_list]
                start_dates = [x for x in start_dates if x < self.end_utc]
                dates_diff = numpy.diff(
                    numpy.array([x.get_mjd() for x in start_dates])
                ).tolist()
                dates_diff.append((self.end_utc - start_dates[-1]).total_days())
                chained_sats.extend(zip(start_dates, dates_diff, sat_list))
            self._sat_list = chained_sats
        else:
            self._sat_list = self.active_sats

    def __len__(self) -> int:
        self._make_sat_list()
        return len(self._sat_list) * len(self.active_observatories)

    def __iter__(self) -> Iterator[tuple[TimeObj, float, ObservatorySatellite]]:
        self._make_sat_list()

        if self.chain_tles:
            return chain.from_iterable(
                (
                    (
                        (
                            start_day,
                            calc_day,
                            ObservatorySatellite(current_obs, satellite),
                        )
                        for start_day, calc_day, satellite in self._sat_list
                    )
                    for current_obs in self.active_observatories
                )
            )
        else:
            return chain.from_iterable(
                (
                    (
                        (
                            self.start_utc,
                            self.end_days,
                            ObservatorySatellite(current_obs, satellite),
                        )
                        for satellite in self._sat_list
                    )
                    for current_obs in self.active_observatories
                )
            )
