import argparse
import os
import pathlib

import numpy
from tqdm import tqdm

from utils import (
    build_obs_sat,
    get_obs_coord_between,
    two_object_distance,
    TimeDeltaObj,
    today,
)

try:
    import h5py
except ImportError as err:
    print(
        "In order to store satellite positions please install h5py https://pypi.org/project/h5py/\n\n"
    )
    raise err


class HDF5FileNotSetup(IOError):
    pass


class HDF5FileHandler:
    def __init__(self):
        self.file_cache = {}
        self.cur_file = ""
        self.cur_group = None
        self.is_working = False

    def open_file(self, file_name):
        self.is_working = True
        self.cur_file = file_name
        self.cur_group = None
        if file_name in self.file_cache and self.file_cache[file_name]:
            return
        else:
            self.file_cache[file_name] = h5py.File(file_name, mode="a")

    def add_group(self, group_name):
        if not self.is_working:
            raise HDF5FileNotSetup
        if self.cur_group is None:
            self.cur_group = self.file_cache[self.cur_file].require_group(group_name)
        else:
            self.cur_group = self.cur_group.require_group(group_name)

    def add_dataset(self, dataset_name, data_input):
        if not self.is_working:
            raise HDF5FileNotSetup
        if self.cur_group is None:
            self.file_cache[self.cur_file].create_dataset(dataset_name, data=data_input)
        else:
            self.cur_group.create_dataset(dataset_name, data=data_input)

    def finish_all(self):
        for file_name in self.file_cache.keys():
            if self.file_cache[file_name]:
                self.file_cache[file_name].close()

    def close_working_file(self):
        if self.is_working:
            self.file_cache[self.cur_file].close()
        self.cur_file = ""
        self.cur_group = None
        self.is_working = False


def make_coord_check(in_radius, in_coord, use_alt_az):
    df_ind = ("alt", "az") if bool(use_alt_az) else ("ra", "dec")

    def coord_check(in_df):
        return (
            two_object_distance(
                in_df[df_ind[0]], in_df[df_ind[1]], in_coord[0], in_coord[1]
            )
            < in_radius
        )

    return coord_check


def parse_arguments(in_args):
    n_days = in_args.days
    reload_sat = in_args.reload
    use_all_ = in_args.all
    merge_ = in_args.merge
    in_coord_ = (in_args.coordinate_1, in_args.coordinate_2)
    in_rad_ = in_args.radius
    f_alt_az_ = in_args.flag
    ignore_empty = in_args.ignore_empty

    return (
        n_days,
        reload_sat,
        use_all_,
        merge_,
        in_coord_,
        in_rad_,
        f_alt_az_,
        ignore_empty,
    )


def main(in_args) -> None:
    (
        n_days,
        reload_sat,
        use_all_,
        merge_,
        in_coord_,
        in_rad_,
        f_alt_az_,
        ignore_empty,
    ) = parse_arguments(in_args)

    today_utc = today()

    start_day = today_utc.get_start_day()
    final_day = start_day.get_off(days=n_days)
    step_t = TimeDeltaObj(seconds=1)

    observatory_sats = build_obs_sat(reload_sat, use_all_)

    coord_checker = make_coord_check(in_rad_, in_coord_, bool(f_alt_az_))

    file_handler = HDF5FileHandler()

    for obs_sat_obj in observatory_sats:
        if merge_:
            out_file = os.path.join("output", "calculated_satellite_data.hdf5")
            file_handler.open_file(out_file)
            file_handler.add_group(obs_sat_obj.obs_name)
            file_handler.add_group(obs_sat_obj.sat_name)
            file_handler.add_group(str(numpy.around(in_rad_, 3)))
        else:
            out_file = os.path.join(
                "output",
                "sat_pos",
                f"{obs_sat_obj.sat_name}_{obs_sat_obj.obs_name}_"
                f"{int(in_rad_ * 100)}_{today_utc.get_file_format()}-"
                f"{final_day.get_file_format()}.hdf5",
            )
            file_handler.open_file(out_file)

        print(
            f"Looking for {obs_sat_obj.sat_name} at "
            f"{obs_sat_obj.obs_name} from {today_utc} to {final_day} "
            f"around {in_coord_} at a radius of {in_rad_}"
        )

        for day_num in tqdm(range(n_days)):
            start_t = start_day.get_off(days=day_num)
            end_t = start_t.get_off(days=1)
            pd_sat_data = get_obs_coord_between(obs_sat_obj, start_t, end_t, step_t)
            pd_sat_data = pd_sat_data[coord_checker(pd_sat_data)]

            # Storage step
            if ignore_empty and (0 in pd_sat_data.shape):
                continue
            dataset_name = start_t.iso_format()
            file_handler.add_dataset(dataset_name, pd_sat_data.to_numpy())

    file_handler.finish_all()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="search the inputted satellites track for how close each will get to your input."
    )
    parser.add_argument("days", type=int, help="The number of days to calculate for")
    parser.add_argument(
        "coordinate_1", type=float, help="RA or Alt depending on <flag>"
    )
    parser.add_argument(
        "coordinate_2", type=float, help="Dec or Az depending on <flag>"
    )
    parser.add_argument("radius", type=float, help="The radius around the coordinate")
    parser.add_argument("flag", type=int, help="0 = RA/Dec; 1 = Alt/Az")
    parser.add_argument(
        "-r",
        "--reload",
        action="store_true",
        help="Re-download the TLE file from the internet",
    )
    parser.add_argument(
        "-a", "--all", action="store_true", help="Use all satellites from database"
    )
    parser.add_argument(
        "-m", "--merge", action="store_true", help="write all data into a single file"
    )
    parser.add_argument(
        "-i",
        "--ignore-empty",
        action="store_true",
        help="If the dataset is empty, it will not be written to the file",
    )

    args = parser.parse_args()

    pathlib.Path(os.path.join("output", "sat_pos")).mkdir(parents=True, exist_ok=True)
    main(args)
