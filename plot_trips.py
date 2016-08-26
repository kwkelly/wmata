import json
import datetime
from datetime import timezone
import pytz
import pandas as pd
import collections
import itertools
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import run

counter = itertools.count()

eastern = pytz.timezone('US/Eastern')

train_info = run.TrainInfo()
stations_dict = train_info.create_stations_dict()


def date_parse(unixtime):
    time = datetime.datetime.fromtimestamp(float(unixtime))
    time = time.replace(tzinfo=timezone.utc).astimezone(tz=eastern)
    return time

filename = 'log_stat.csv'
all_data = pd.read_csv(filename, parse_dates=[0], date_parser=date_parse)
print(all_data.describe())
data = all_data.dropna()
# get only the trains that are boarding
data = data[data['Min']=='BRD']

id_dest_map = {}
def id_dest(row, id_dest_map):
    """
    If the trian id and destination exists, then it is part of the same trip.
    If it is a new destination or the train is not in there, it is a new trip.
    """
    train_id = row['TrainId']
    cur_dest = row['DestinationStationCode']
    cur_time = row['Time']
    if train_id not in id_dest_map.keys():
        id_dest_map[train_id] = (cur_dest, cur_time)
        return cur_time
    else:
        old_dest, old_time = id_dest_map[train_id]
        if cur_dest != old_dest:
            id_dest_map[train_id] = (cur_dest, cur_time)
            return cur_time
        else:
            return old_time

trip_dict = {}
def unique_trips(row, trip_set):
    train_id = row['TrainId']
    dest = row['DestinationStationCode']
    start = row['StartTime']
    trip = (train_id, dest, start)
    if trip not in trip_dict:
        trip_id = next(counter)
        trip_dict[trip] = trip_id
        return trip_id
    else:
        return trip_dict[trip]

data['StartTime'] = data.apply(lambda row: id_dest(row, id_dest_map), axis=1)
data['TripId'] = data.apply(lambda row: unique_trips(row, trip_dict), axis=1)
# Loop through the trains and get the start times for each trip
data = data.drop_duplicates(['LocationCode','LineCode','DestinationStationCode', 'StartTime'])


start = datetime.datetime(2016, 7, 29, 3, tzinfo=eastern)
end = datetime.datetime(2016, 7, 29, 10, tzinfo=eastern)

data = data[data['Time'].between(start, end)]

# lets look at red line, direction 1
line_code = 'OR'
direction = 1
data = data[(data['LineCode']==line_code)]
#need to map station order to index
#red_stations = run.get_station_list('RD')
# station list api no longer returns in order?
routes = run.get_routes()
circuits = [route for route in routes['StandardRoutes']
        if route['LineCode'] == line_code
        and route['TrackNum'] == 1]
circuits = circuits[0]['TrackCircuits']  # should only be one
red_stations = [circuit['StationCode'] for circuit in circuits if circuit['StationCode'] is not None]
print(red_stations)
station_names = [stations_dict[code] for code in red_stations]
plt.figure(figsize=(24, 6))
for trip_id in data.TripId.unique():
    trip = data[data['TripId']==trip_id]
    #print(trip)
    stop_times = [stop['Time'] for _, stop in trip.iterrows()]
    stop_nums = [red_stations.index(stop['LocationCode']) for _, stop in trip.iterrows()]
    plt.plot(stop_times, stop_nums, color='#476E96')

plt.xlim([start, end])
plt.yticks([i for i in range(len(station_names))], station_names)
plt.tight_layout()
plt.savefig('trips.png')


# We need to identify the different trips from the trains
# Trip identifies:
#  - TrainId
#  - DestinationStationCode
#  - Get trip start time. This is the time stamp at which the combination of TrainId / DestinationCode
#    first appears.
#  From this we can generate a TripId which is a combination of TrainId/Destination/Counter


