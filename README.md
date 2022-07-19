# Satellite Calculator
A set of scripts whose goal is to calculate satellite positions given various conditions. This repository is a WIP, future scripts may be added. Pull Requests are welcomed.


## Find Satellite Events (find_satellite_events.py)

This is a script which calculates the various characteristics of a satellite when it rises, culminates, and falls . Outputs in a .csv file called `culmination_output.csv`

### File Inputs
#### obs_data.yaml
This file is in the `YAML` format, and specifies the list of observatories to calculate with respect to. The elements are (`<latitude in deg>`, `<longitude in deg>`, `<altitude in meters>`) with the keys being the observatory name.

#### sat_list.txt
This file lists the names of the satellites to look for on each line.

#### csv_config.ini
This file specifies the columns to activate for the CSV file and in what order the columns should be in, just list the column headers in a new section.

### Command Line Inputs
`python find_satellite_events.py [-h] [-tz SET_TIMEZONE] [-r] [-a ALT] [-c CSV] [-i] [-l] [days]`

All arguments are optional. The one positional argument, `<days>` determines how many days into the future to calculate the culminations for. By default it is 120.

Here is the list of non-positional arguments:
* `-h`, `--help` will print the help message
* `-tz`, `--set-timezone` will set the timezone to use in the output with; you can find a list of possible inputs 
  [here](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones). By default, it uses the one your computer is set to.
* `-r`, `--reload` will re-download the TLE file from https://celestrak.com/NORAD/elements/active.txt as opposed to using a cached version.
* `-s`, `--solve` will calculate the satellite positions around culmination based on the next four parameters which are `<start time in seconds before culmination> <duration in seconds> <timestep in seconds> <alt/az flag>` and are all required. If `<alt/az flag>` is set to 1, then alt/az data will be added. Setting any other number will prevent this.
* `-a`, `--alt` will set the altitude at which the calculations for rising and falling occur; by default it will be 30.
* `-c`, `--csv` will specify the section in `csv_config.ini` to use. The default is "ALL"
* `-i`, `--ignore-daytime` if there is a series of columns specifying a datapoint being in daytime or not, will use them to determine if the row is in the day. If it is, the script skips that row.
* `-l`, `--all` will use all satellites found in the current TLE file

## Get Satellite Positions (get_satellite_pos.py)
This script calculates the positions of the given satellites wrt the observatories and if those satellites go within a specified radius around a specified coordinate, then those coordinates and times will be written into a `.hdf5` file in `output/sat_pos`. 

### Note
This script accomplishes it's task through calculating the positon of the satellite for every second of every day you ask of it. This means that it will run slow, so even if the progress bar isn't going up; that doesn't mean it stopped. Also before the file is written all the data is stored in RAM, so watch out for running out of RAM.

### File Inputs

#### obs_data.yaml
This file is in the `YAML` format, and therefore should be human-readable, specifies the list of observatories to calculate with respect to. The elements are (`<latitude in deg>`, `<longitude in deg>`, `<altitude in meters>`) with the keys being the observatory name.

#### sat_list.txt
This file lists the names of the satellites to look for on each line.

### Command Line Inputs
`python get_satellite_pos.py [-h] [-r] [-a] [-m] [-i] days coordinate_1 coordinate_2 radius flag`

All positional arguments are required.

Here is the list of positional arguments:
* `days` - The number of days to calculate into the future
* `Coordinate 1` - The search area's center's first coordinate either RA or Alt depending on `<Flag>`
* `Coordinate 2` - The search area's center's second coordinate either Dec or Az depending on `<Flag>`
* `Radius` - The radius of the search area
* `Flag` - Indicates what type of position is being specified where 0 = RA/Dec and 1 = Alt/Az

Here is the list of non-positional arguments:
* `-h`, `--help` will print the help message
* `-r`, `--reload` will re-download the TLE file from https://celestrak.com/NORAD/elements/active.txt as opposed to using a cached version.
* `-a`, `--all` will use all satellites found in the TLE file
* `-m`, `--merge` will cause all satellite data to be inside the same file for a given radius, observatory, and date range.
* `-i`, `--ignore-empty` will prevent empty datasets from being written

## HDF5 Note
If any script calculates the positions of a satellite, it will place those positions inside an individual table in an HDF5 file. Each table corresponds to a culmination or day (depending on the script). Each table is referenced by a key which is the time of the first element in [ISO-8601 format](https://en.wikipedia.org/wiki/ISO_8601) The [wikipedia page for HDF5](https://en.wikipedia.org/wiki/Hierarchical_Data_Format) has a list of languages which have HDF5 parsers for them already written.

## Dependencies
### Python Version
These scripts uses features from the `typing` module which was introduced in python 3.7, so that is the minimum 
recommended python version required to run these scripts. 
### Formatting
All scripts have been formatted with [black](https://github.com/psf/black).
### Packages
This repository contains a `pipfile` which is used by the dependency management system [pipenv](https://pipenv.pypa.
io/en/latest/). Otherwise, here is a list of the packages needed to run these scripts
* numpy
* skyfield
* pandas
* astropy
* geopy
* tqdm
* pytz
* tzlocal
* cached-property
* pyyaml
* h5py (If storing satellite positions)
