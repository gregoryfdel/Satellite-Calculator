from typing import List, Sequence

import pandas
import yaml
from skyfield.sgp4lib import EarthSatellite

from utils import (
    SkyfieldConstants,
    DayTransits,
    Observatories,
    ObservatorySatellite,
    TimeDeltaObj,
    TimeObj,
    today,
    get_off_list,
)


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
    sf_list = get_off_list(start_time, end_time, time_step, 2)
    rv_df = get_off_list(start_time, end_time, time_step, 4)

    toc_list = in_obs_sat.diff.at(sf_list)
    ra, dec, _ = toc_list.radec()
    rv_df["ra"] = ra.degrees
    rv_df["dec"] = dec.degrees

    alt, az, _ = toc_list.altaz()
    rv_df["alt"] = alt.degrees
    rv_df["az"] = az.degrees

    return rv_df


def build_sat_list(reload_sat: bool, use_all_: bool = False) -> List[EarthSatellite]:
    today_utc = today().get_start_day()

    sat_url = "https://celestrak.com/NORAD/elements/active.txt"
    if reload_sat:
        satellites = SkyfieldConstants.load.tle_file(sat_url, reload=True)
    else:
        satellites = SkyfieldConstants.load.tle_file(sat_url)

    if use_all_:
        return satellites

    with open("config/sat_list.txt", "r") as fp:
        sat_names = [x.strip() for x in fp.readlines()]

    satellite_array = []
    for sat in satellites:
        days = today_utc.sf - sat.epoch
        if days < 14 and any(sat_name in sat.name for sat_name in sat_names):
            satellite_array.append(sat)

    if not satellite_array:
        print(
            "No inputted satellite from config/sat_list.txt was not found, "
            "please retry with --reload or check to ensure each are still active"
        )
        sys.exit(1)

    return satellite_array


def build_obs_sat(
    reload_sat_: bool, use_all_: bool = False
) -> List[ObservatorySatellite]:
    satellite_array = build_sat_list(reload_sat_, use_all_)

    with open("config/obs_data.yaml", "r") as fp:
        obs_data = yaml.load(fp, Loader=yaml.SafeLoader)

    rv = []
    for obs_name in obs_data:
        obs_lat, obs_long, obs_ele = obs_data[obs_name]
        current_obs = Observatories(obs_lat, obs_long, obs_ele, obs_name)
        for satellite in satellite_array:
            rv.append(ObservatorySatellite(current_obs, satellite))

    return rv


def find_sat_events(
    in_obs_sat: ObservatorySatellite,
    in_start: TimeObj,
    in_end: TimeObj,
    limit_alt: float,
) -> List[DayTransits]:
    event_times, event_flags = in_obs_sat.sat.find_events(
        in_obs_sat.observatory.sf, in_start.sf, in_end.sf, altitude_degrees=limit_alt
    )

    events_zipped = list(zip(event_times, event_flags))
    rv_transits = []
    for time, flag in events_zipped:
        if flag == 0:
            new_transit = DayTransits(in_obs_sat, limit_alt)
            new_transit.start = TimeObj(time, in_local_tz=in_start.local_tz)
            rv_transits.append(new_transit)

    for time, flag in events_zipped:
        if flag == 2:
            test_time_obj = TimeObj(time, in_local_tz=in_start.local_tz)
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
