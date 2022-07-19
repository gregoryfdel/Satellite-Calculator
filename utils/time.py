from datetime import datetime, timedelta
from typing import Optional, Any, Union, List

import numpy as np
import pandas
from astropy.time import Time as AstropyTime
from astropy.time import TimeDelta as AstropyTimeDelta
from astropy.timeseries import TimeSeries as AstropyTimeSeries
from numpy.typing import ArrayLike
from pandas import Timedelta as PandasTimeDelta
from pandas import Timestamp as PandasTimeStamp
from pytz import timezone
from skyfield.timelib import Time as SkyfieldTime

from utils import SkyfieldConstants


def timezone_converter(
    input_dt: datetime,
    current_tz: Optional[str] = "UTC",
    target_tz: Optional[str] = "UTC",
) -> datetime:
    current_tz = timezone(current_tz)
    target_tz = timezone(target_tz)
    if (getattr(input_dt, "tzinfo", None) is not None) and (
        input_dt.tzinfo.utcoffset(input_dt) is not None
    ):
        target_dt = input_dt.astimezone(target_tz)
    else:
        target_dt = current_tz.localize(input_dt).astimezone(target_tz)
    return target_tz.normalize(target_dt)


class TimeObj:
    def __init__(self, input_time: Any, in_local_tz="UTC") -> None:
        """
        Create a custom time object which is used to switch between
        inputs to the various packages used, as well as simplify
        common time associated functions

        :param input_time:
        """
        self.dt = None
        self.local_tz = in_local_tz

        if isinstance(input_time, TimeObj):
            self.dt = input_time.dt
            self.local_tz = input_time.local_tz
        elif isinstance(input_time, datetime):
            self.dt = timezone_converter(input_time)
        elif isinstance(input_time, SkyfieldTime):
            self.dt = input_time.utc_datetime()
        elif isinstance(input_time, np.datetime64):
            self.dt = timezone_converter(input_time.astype(datetime))
        elif isinstance(input_time, AstropyTime):
            self.dt = timezone_converter(input_time.to_datetime())
        elif isinstance(input_time, PandasTimeStamp):
            self.dt = timezone_converter(input_time.to_pydatetime())

        if self.dt is None:
            raise TypeError(
                "Only datetime, numpy.datetime64, skyfield.timelib.Time, "
                "pandas.Timestamp or astropy.time.Time objects are allowed!, "
                f"inputTime was of type {type(input_time)}"
            )

        self.sf = SkyfieldConstants.timescale.from_datetime(self.dt)
        self.np = np.datetime64(self.dt)
        self.ap = AstropyTime(self.dt)
        self.pd = PandasTimeStamp(self.dt)

    def __repr__(self) -> str:
        return (
            "TimeObj(datetime=%r, skyfield.timelib.Time=%r, numpy.datetime64=%r, astropy.time.Time=%r, pandas.Timestamp=%r)"
            % (self.dt, self.sf, self.np, self.ap, self.pd)
        )

    def __str__(self) -> str:
        return str(self.dt)

    def __sub__(self, other):
        return TimeDeltaObj(self.dt - other.dt)

    def __ge__(self, other) -> bool:
        return self.dt >= other.dt

    def __gt__(self, other) -> bool:
        return self.dt > other.dt

    def __lt__(self, other) -> bool:
        return self.dt < other.dt

    def __le__(self, other) -> bool:
        return self.dt <= other.dt

    def __eq__(self, other) -> bool:
        return self.dt == other.dt

    def set_local_timezone(self, in_tz):
        self.local_tz = in_tz

    def get_start_day(self):
        return TimeObj(
            datetime.combine(self.dt.date(), datetime.min.time()),
            in_local_tz=self.local_tz,
        )

    def get_off(self, **kwargs: int):
        return TimeObj(self.dt + timedelta(**kwargs), in_local_tz=self.local_tz)

    def get_off_center(self, **kwargs: int):
        time_d = timedelta(**kwargs) / 2
        return TimeObj(self.dt - time_d, in_local_tz=self.local_tz), TimeObj(
            self.dt + time_d, in_local_tz=self.local_tz
        )

    def get_datetime(self) -> datetime:
        return self.dt

    def get_skyfield(self) -> SkyfieldTime:
        return self.sf

    def get_numpy(self) -> np.datetime64:
        return self.np

    def get_astropy(self) -> AstropyTime:
        return self.ap

    def get_pandas(self) -> PandasTimeStamp:
        return self.pd

    def iso_format(self) -> str:
        return self.dt.isoformat()

    def get_file_format(self) -> str:
        return self.dt.strftime("%Y%m%d")

    def get_jd(self) -> float:
        return self.ap.jd

    def get_mjd(self) -> float:
        return self.ap.mjd

    def get_local_time(self) -> datetime:
        return timezone_converter(self.dt, target_tz=self.local_tz)

    def utc_formatted_str(self) -> str:
        return self.dt.strftime("%Y %b %d %H:%M:%S")

    def local_formatted_str(self) -> str:
        return self.get_local_time().strftime("%Y %b %d %H:%M:%S")


class TimeDeltaObj:
    def __init__(self, input_delta=None, **delta_args) -> None:
        """
        Create a custom time delta object which is used to switch between
        inputs to the various packages used, as well as simplify
        common time associated functions

        :param input_delta:
        """
        if len(delta_args) > 0:
            self.dt = timedelta(**delta_args)
        elif isinstance(input_delta, timedelta):
            self.dt = input_delta
        elif isinstance(input_delta, np.timedelta64):
            self.dt = input_delta.astype(timedelta)
        elif isinstance(input_delta, AstropyTimeDelta):
            self.dt = input_delta.to_datetime()
        elif isinstance(input_delta, PandasTimeDelta):
            self.dt = input_delta.to_pytimedelta()
        else:
            raise TypeError(
                "Input delta keyword args, a datetime, numpy.timedelta64, "
                "pandas.Timedelta or astropy.time.TimeDelta! "
                f"inputTime was of type {type(input_delta)} and "
                f"inputted keyword args were {delta_args}"
            )

        self.np = np.timedelta64(self.dt)
        self.pd = pandas.to_timedelta(self.dt)
        self.ap = AstropyTimeDelta(self.dt)

    def total_seconds(self) -> float:
        return self.dt.total_seconds()

    def get_datetime(self) -> timedelta:
        return self.dt

    def get_numpy(self) -> np.timedelta64:
        return self.np

    def get_astropy(self) -> AstropyTimeDelta:
        return self.ap

    def get_pandas(self) -> PandasTimeDelta:
        return self.pd


def get_off_list(
    t_start: TimeObj, t_end: TimeObj, t_step: TimeDeltaObj, final_type: int = 0
) -> Union[
    AstropyTimeSeries, ArrayLike, List[datetime], SkyfieldTime, pandas.DataFrame
]:
    """
    Create a list of times for use by different astronomical packages

    numpy array of dtype=numpy.datetime64 if final_type=0

    python list of UTC datetimes if final_type=1

    skyfield Time object if final_type=2

    astropy Time object if final_type=3

    pandas DataFrame if final_type=4

    Parameters
    ----------
    t_start
    t_end
    t_step
    final_type

    Returns
    -------
    """
    if final_type in {3, 4}:
        ap_step = t_step.get_astropy()
        n_steps = (t_end.get_numpy() - t_start.get_numpy()) // t_step.get_numpy() + 1
        ap_ts = AstropyTimeSeries(
            time_start=t_start.ap, time_delta=ap_step, n_samples=n_steps
        )
        return ap_ts if final_type == 3 else ap_ts.to_pandas()
    num_list = np.arange(t_start.get_numpy(), t_end.get_numpy(), t_step.get_numpy())
    if final_type == 0:
        return num_list

    dt_list = [timezone_converter(t) for t in num_list.astype(datetime)]
    if final_type == 1:
        return dt_list

    if final_type == 2:
        return SkyfieldConstants.timescale.from_datetimes(dt_list)

    raise TypeError(
        "Please select a type 0 (numpy.datetime64), 1 (datetime), 2 (skyfield.timelib.Time), 3 (astropy.time.Time), or 4 (pandas.DataFrame)! "
    )


def today() -> TimeObj:
    dt_today = datetime.combine(datetime.now().date(), datetime.min.time())
    return TimeObj(dt_today)
