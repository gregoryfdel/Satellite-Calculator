from typing import Union

import numpy
from numpy.typing import ArrayLike


def two_object_distance(
    ra1: Union[float, ArrayLike],
    dec1: Union[float, ArrayLike],
    ra2: Union[float, ArrayLike],
    dec2: Union[float, ArrayLike],
) -> Union[float, ArrayLike]:
    """
    Calculate the angular distance between two coordinates.

    Parameters
    ----------
    ra1 : float, array
            Right ascension of the first object in degrees.
    dec1 : float, array
            Declination of the first object in degrees.
    ra2 : float, array
            Right ascension of the second object in degrees.
    dec2 : float, array
            Declination of the second object in degrees.
    Returns
    -------
    Angle : float, array
            The angular distance in DEGREES between the first
            and second coordinate in the sky.

    """
    delta_lon = numpy.deg2rad(ra1 - ra2)
    delta_lat = numpy.deg2rad(dec1 - dec2)
    # Haversine formula
    dist = 2.0 * numpy.arcsin(
        numpy.sqrt(
            numpy.sin(delta_lat / 2.0) ** 2
            + numpy.cos(dec1 * numpy.pi / 180.0)
            * numpy.cos(dec2 * numpy.pi / 180.0)
            * numpy.sin(delta_lon / 2.0) ** 2
        )
    )
    return numpy.rad2deg(dist)
