"""
Calculates the volume for a survey raster and minimum surface. If lower elevation is
null then the calculation is up to the upper elevation. If the upper elevation is null
then the analysis is above the lower elevation. If both are valid then the analysis is
greater than or equal to the lower elevation and less than the upper elevation. i.e.
"""
from typing import Dict
import copy
import numpy as np


def get_vol_and_area(ar_survey: np.array, ar_minimum: np.array, lower_elev: float, upper_elev: float, cell_size: float) -> tuple:
    """
    Calculates the volume for a survey raster and minimum surface. If lower elevation is
    null then the calculation is up to the upper elevation. If the upper elevation is null
    then the analysis is above the lower elevation. If both are valid then the analysis is
    greater than or equal to the lower elevation and less than the upper elevation. i.e.

    Lower is null then analysis < upper
    Upper is null then analysis >= lower
    Both valid then analysis >= lower and < upper
    """
    if lower_elev is None:
        assert upper_elev is not None, 'An upper elevation must be provided if the lower elevation is not provided.'
    else:
        assert lower_elev >= 0, 'The lower elevation ({lower_elev}) must be greater than or equal to zero.'
        if upper_elev is not None:
            assert lower_elev < upper_elev, 'The lower elevation ({lower_elev}) must be less than the upper elevation ({upper_elev}).'

    if upper_elev is not None:
        assert upper_elev >= 0, 'The upper elevation ({upper_elev}) must be greater than or equal to zero.'

    # Only proceed and calculate the area and volume if the survey is not entirely masked.
    # This shouldn't be needed, but the Workbench might have sections for surveys where no data were collected.
    if np.ma.MaskedArray.count(ar_survey) == 0:
        return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    # We will create a new, custom minimum surface:
    ar_new_min_srf = np.empty_like(ar_minimum)

    # Quick Deep copy of arMinimum:
    ar_new_min_srf[:] = ar_minimum
    ar_new_min_srf = np.ma.masked_where(ar_survey.mask, ar_new_min_srf, True)

    template = {'area': 0.0, 'volume': 0.0}
    survey_above_upper = copy.copy(template)
    min_surf_above_upper = copy.copy(template)

    new_lower_elev = lower_elev
    if lower_elev is None:
        new_lower_elev = np.min(ar_survey)

    survey_above_lower = get_above_elev(ar_survey, new_lower_elev, cell_size)
    min_surf_above_lower = get_above_elev(ar_new_min_srf, new_lower_elev, cell_size)

    if upper_elev:
        survey_above_upper = get_above_elev(ar_survey, upper_elev, cell_size)
        min_surf_above_upper = get_above_elev(ar_new_min_srf, upper_elev, cell_size)

    survey_net_vol = survey_above_lower['volume'] - survey_above_upper['volume']
    min_surf_net_vol = min_surf_above_lower['volume'] - min_surf_above_upper['volume']
    net_volume = survey_net_vol - min_surf_net_vol

    area = survey_above_lower['area'] - survey_above_upper['area']

    return (area, net_volume, survey_above_lower['volume'], min_surf_above_lower['area'], min_surf_above_lower['volume'], min_surf_net_vol)


def get_above_elev(ar_values: np.array, elevation: float, cell_size: float) -> Dict[float, float]:
    """
    Get the area and volume above the elevation
    """

    area_above_elev = np.ma.MaskedArray.count(ar_values[ar_values > elevation]) * cell_size**2

    vol_above_elev = 0.0
    if area_above_elev > 0:
        vol_above_elev = np.nansum(
            ar_values[ar_values > elevation]) * cell_size**2 - (area_above_elev * elevation)

    return {'area': area_above_elev, 'volume': vol_above_elev}


def get_bin_area(ar_survey: np.array, lower_elev: float, upper_elev: float, cell_size: float) -> float:
    """
    Finds the area of the raster between the lower and upper elevations.
    This is a simplified version of get_vol_and_area() that only calculates the area.
    It is used by the campsite analysis.

       Lower is null then analysis < upper
    Upper is null then analysis >= lower
    Both valid then analysis >= lower and < upper
    """

    if lower_elev is None:
        assert upper_elev is not None, 'An upper elevation must be provided if the lower elevation is not provided.'
    else:
        assert lower_elev >= 0, 'The lower elevation ({lower_elev}) must be greater than or equal to zero.'
        if upper_elev is not None:
            assert lower_elev < upper_elev, 'The lower elevation ({lower_elev}) must be less than the upper elevation ({upper_elev}).'

    if upper_elev is not None:
        assert upper_elev >= 0, 'The upper elevation ({upper_elev}) must be greater than or equal to zero.'

    # Only proceed and calculate the area and volume if the survey is not entirely masked.
    # This shouldn't be needed, but the Workbench might have sections for surveys where no data were collected.
    if np.ma.MaskedArray.count(ar_survey) == 0:
        return 0.0

    template = {'area': 0.0}
    survey_above_upper = copy.copy(template)

    new_lower_elev = lower_elev
    if lower_elev is None:
        new_lower_elev = np.min(ar_survey)

    survey_above_lower = get_above_elev(ar_survey, new_lower_elev, cell_size)

    if upper_elev:
        survey_above_upper = get_above_elev(ar_survey, upper_elev, cell_size)

    area = survey_above_lower['area'] - survey_above_upper['area']

    return area
