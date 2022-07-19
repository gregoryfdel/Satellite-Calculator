from datetime import datetime
from typing import Tuple, Union

from cached_property import cached_property
from geopy import distance
from skyfield.almanac import dark_twilight_day, fraction_illuminated
from skyfield.sgp4lib import EarthSatellite
from skyfield.toposlib import GeographicPosition, iers2010

from utils import (
    two_object_distance,
    SkyfieldConstants,
    TimeObj,
    MetaFormatter,
    Observatories,
)


class ObservatorySatellite:
    def __init__(self, in_observatory: Observatories, satellite_: EarthSatellite):
        self.observatory = in_observatory
        self.sat = satellite_
        self.diff = self.sat - self.observatory.sf
        self.sat_name = self.sat.name
        self.obs_name = self.observatory.name

    def at(self, in_time: TimeObj):
        return SatellitePosition(self, in_time)


class SatellitePosition(metaclass=MetaFormatter):
    def __init__(self, in_obs_sat, in_time: TimeObj):
        self.obs: Observatories = in_obs_sat.observatory
        self.sat: EarthSatellite = in_obs_sat.sat

        self.twilight_checker = dark_twilight_day(
            SkyfieldConstants.ephemeris, self.obs.sf
        )
        self.time = in_time

        self._sat_toc = in_obs_sat.diff.at(self.time.sf)

    @cached_property
    def local_tz(self) -> Union[None, str]:
        return self.time.local_tz

    @cached_property
    def local_datetime(self) -> datetime:
        return self.time.get_local_time()

    @cached_property
    def utc_datetime(self) -> datetime:
        return self.time.dt

    @cached_property
    def utc_str(self) -> str:
        return self.time.utc_formatted_str()

    @cached_property
    def local_time_str(self) -> str:
        return self.time.local_formatted_str()

    @cached_property
    def obs_name(self) -> str:
        return self.obs.name

    @cached_property
    def obs_lat(self) -> float:
        return self.obs.lat

    @cached_property
    def obs_long(self) -> float:
        return self.obs.long

    @cached_property
    def sat_name(self) -> str:
        return self.sat.name

    @cached_property
    def sat_epoch(self) -> TimeObj:
        return TimeObj(self.sat.epoch)

    @cached_property
    def sat_ra_dec(self) -> Tuple[float, float]:
        sat_ra, sat_dec, _ = self._sat_toc.radec(
            epoch=SkyfieldConstants.timescale.J2000
        )
        return sat_ra._degrees, sat_dec._degrees

    @cached_property
    def sat_alt_az(self) -> Tuple[float, float]:
        sat_alt, sat_az, _ = self._sat_toc.altaz()
        return sat_alt._degrees, sat_az._degrees

    @cached_property
    def sat_ra(self) -> float:
        ra, _ = self.sat_ra_dec
        return ra

    @cached_property
    def sat_dec(self) -> float:
        _, dec = self.sat_ra_dec
        return dec

    @cached_property
    def sat_alt(self) -> float:
        alt, _ = self.sat_alt_az
        return alt

    @cached_property
    def sat_az(self) -> float:
        _, az = self.sat_alt_az
        return az

    @cached_property
    def moon_ra_dec(self) -> Tuple[float, float]:
        moon_ra, moon_dec, _ = (
            self.obs.sf_vector_sum.at(self.time.sf)
            .observe(SkyfieldConstants.moon)
            .apparent()
            .radec(epoch=SkyfieldConstants.timescale.J2000)
        )

        return moon_ra._degrees, moon_dec._degrees

    @cached_property
    def moon_ra(self) -> float:
        moon_ra, _ = self.moon_ra_dec
        return moon_ra

    @cached_property
    def moon_dec(self) -> float:
        _, moon_dec = self.moon_ra_dec
        return moon_dec

    @cached_property
    def moon_fraction(self) -> float:
        return fraction_illuminated(SkyfieldConstants.ephemeris, "moon", self.time.sf)

    @cached_property
    def moon_distance(self) -> float:
        return two_object_distance(
            self.sat_ra, self.sat_dec, self.moon_ra, self.moon_dec
        )

    @cached_property
    def is_daytime(self) -> bool:
        return self.twilight_checker(self.time.sf) > 1

    @cached_property
    def is_daytime_str(self) -> str:
        return "Y" if self.is_daytime else "N"

    @cached_property
    def is_sat_sunlit(self) -> bool:
        return self.sat.at(self.time.sf).is_sunlit(SkyfieldConstants.ephemeris)

    @cached_property
    def is_sat_sunlit_str(self) -> str:
        return "Y" if self.is_sat_sunlit else "N"

    @cached_property
    def sat_geo_position(self) -> GeographicPosition:
        return iers2010.subpoint(self.sat.at(self.time.sf))

    @cached_property
    def sat_lat_long(self) -> Tuple[float, float]:
        return (
            self.sat_geo_position.latitude._degrees,
            self.sat_geo_position.longitude._degrees,
        )

    @cached_property
    def sat_lat(self) -> float:
        geo_lat, _ = self.sat_lat_long
        return geo_lat

    @cached_property
    def sat_long(self) -> float:
        _, geo_long = self.sat_lat_long
        return geo_long

    @cached_property
    def sat_obs_distance(self) -> float:
        return distance.distance(self.sat_lat_long, self.obs.lat_long).km
