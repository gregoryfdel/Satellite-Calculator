import argparse
import configparser
import json
import os
import pathlib
from operator import attrgetter
from typing import List

import pytz
from tqdm import tqdm
from tzlocal import get_localzone

from utils import DayTransits, SingleCulmination, build_obs_sat, get_day_transits, today


class ColumnDefinition:
    """Creates the column name and value getter from a definition"""

    def __init__(self, *column_definition):
        self.column_name = column_definition[0]
        self.attr_getter = attrgetter(".".join(column_definition[1:]))
        self.index = -1

    def get_ini_key(self):
        return self.column_name.lower()

    def get_value(self, in_transit_data: SingleCulmination):
        return self.attr_getter(in_transit_data)


def write_to_csv_file(
    in_file_name: str,
    in_config_section: str,
    in_days: List[DayTransits],
    ignore_day: bool,
) -> None:
    in_file_name = os.path.join("output", in_file_name)

    with open("col_defs.json", "r") as fp:
        csv_col_defs = json.load(fp)

    csv_col_defs = [ColumnDefinition(*arg_defs) for arg_defs in csv_col_defs]
    # Filter the columns using the .ini file
    csv_config_parser = configparser.ConfigParser(allow_no_value=True)
    csv_config_parser.read_file(open(os.path.join("config", "csv_config.ini")))

    good_col_defs = []
    for option_ind, option in enumerate(csv_config_parser.options(in_config_section)):
        for csv_col_def in csv_col_defs:
            if csv_col_def.get_ini_key() == option:
                csv_col_def.index = option_ind
                good_col_defs.append(csv_col_def)

    # Sort based on config file
    good_col_defs.sort(key=lambda x: x.index)

    # Create the .csv file
    csv_head = ",".join(x.column_name for x in good_col_defs) + "\n"
    with open(in_file_name, "w") as fp:
        fp.write(csv_head)
        for day_transits in in_days:
            for single_culmination in day_transits:
                if single_culmination.culmination.is_daytime and ignore_day:
                    continue

                row = [
                    str(csv_column.get_value(single_culmination))
                    for csv_column in good_col_defs
                ]
                row_s = ",".join(row) + "\n"
                fp.write(row_s)


def parse_arguments(in_args):
    n_days = in_args.days
    reload_sat = in_args.reload
    use_all_ = getattr(in_args, "all", False)
    in_alt_amt = getattr(in_args, "alt", 30.0)
    in_config_section = getattr(in_args, "csv", "ALL")
    ignore_day = getattr(in_args, "ignore_daytime", False)

    input_tz = getattr(in_args, "set_timezone", None)
    input_tz = get_localzone() if input_tz is None else pytz.timezone(input_tz)
    input_tz = input_tz.zone

    return (
        n_days,
        reload_sat,
        input_tz,
        use_all_,
        in_alt_amt,
        in_config_section,
        ignore_day,
    )


def main(input_args) -> None:
    (
        n_days,
        reload_sat,
        input_tz,
        use_all_,
        in_alt_amt,
        in_config_section,
        ignore_day,
    ) = parse_arguments(input_args)
    today_utc = today()
    today_utc.set_local_timezone(input_tz)

    sat_obs_objects = build_obs_sat(reload_sat, use_all_)
    final_day = today_utc.get_off(days=n_days)

    print(f"Calculating culminations of {len(sat_obs_objects)} satellites")

    culmination_data = []
    for sat_obs in sat_obs_objects:
        print(
            f"Looking for {sat_obs.sat_name} at {sat_obs.obs_name} from {today_utc} to {final_day}"
        )

        for day_num in tqdm(range(n_days)):
            day_start = today_utc.get_off(days=day_num).get_start_day()
            day_end = day_start.get_off(days=1)

            day_transits = get_day_transits(sat_obs, day_start, day_end, in_alt_amt)
            culmination_data.extend(day_transits)

    write_to_csv_file(
        "culmination_output.csv", in_config_section, culmination_data, ignore_day
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Calculate Satellite rises, sets, and culminations for observatories found in config/obs_data.yaml"
    )

    parser.add_argument(
        "days",
        type=int,
        nargs="?",
        default=120,
        help="The number of days to calculate for, default of 120 days",
    )

    parser.add_argument(
        "-tz",
        "--set-timezone",
        type=str,
        help="The timezone to calculate with respect to, default is your local timezone",
    )

    parser.add_argument(
        "-r",
        "--reload",
        action="store_true",
        help="Re-download the TLE file from the internet",
    )
    parser.add_argument(
        "-a",
        "--alt",
        nargs=1,
        type=float,
        default=30.0,
        help="Change the altitude at which the calculations for rising and falling occur",
    )

    parser.add_argument(
        "-c",
        "--csv",
        type=str,
        default="ALL",
        help="Specifies the section in csv_config.ini to use when building the csv files",
    )

    parser.add_argument(
        "-i",
        "--ignore-daytime",
        action="store_true",
        help="ignore the data points which occur during the day",
    )

    parser.add_argument(
        "-l", "--all", action="store_true", help="Use all satellites from database"
    )

    args = parser.parse_args()

    pathlib.Path("output").mkdir(parents=True, exist_ok=True)
    main(args)
