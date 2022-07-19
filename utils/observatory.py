from typing import Tuple

from skyfield.toposlib import GeographicPosition, iers2010
from skyfield.vectorlib import VectorSum

from utils import SkyfieldConstants


class Observatories:
    def __init__(self, lat, long, alt, in_name):
        self.name = in_name
        self.lat = lat
        self.long = long
        self.alt = alt
        self.values = [self.lat, self.long, self.alt]

    def __iter__(self):
        yield from self.values

    @property
    def sf(self) -> GeographicPosition:
        return iers2010.latlon(self.lat, self.long, elevation_m=float(self.alt))

    @property
    def sf_vector_sum(self) -> VectorSum:
        return SkyfieldConstants.earth + self.sf

    @property
    def lat_long(self) -> Tuple[float, float]:
        return self.lat, self.long
