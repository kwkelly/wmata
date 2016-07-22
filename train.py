import json
import itertools
import pandas as pd
from pandas.io.json import json_normalize
import time
import http.client, urllib.request, urllib.parse, urllib.error, base64
from itertools import tee
from os.path import isfile
import numpy as np
import datetime
import api_key

pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)



headers = {
        # Request headers
        'api_key': api_key.wmata_key,
        }


# a two way dict for a bijective mapping
# here we are using this to map station codes to names and vice versa
class TwoWayDict(dict):
    def __setitem__(self, key, value):
        # Remove any previous connections with these values
        if key in self:
            del self[key]
        if value in self:
            del self[value]
        dict.__setitem__(self, key, value)
        dict.__setitem__(self, value, key)

    def __delitem__(self, key):
        dict.__delitem__(self, self[key])
        dict.__delitem__(self, key)

    def __len__(self):
        """Returns the number of connections"""
        return dict.__len__(self) // 2


class Station:
    def __init__(self, station_code, station_name):
        self.station_code = station_code
        self.station_name = station_name

    def __str__(self):
        return "{0} ({1})".format(self.station_name, self.station_code)

class StationPair:
    def __init__(self, station1, station2, time_to_next):
        self.station1 = station1
        self.station2 = station2
        self.time_to_next = time_to_next

    def __str__(self):
        return "{0} --{1} min--> {2}".format(str(self.station1), self.time_to_next, str(self.station2))

class Line:
    def __init__(self, name, path, times):
        # path is what api returns
        self.name = name
        self.path = []
        for s1, s2 in pairwise(path['Path']):
            # time to next
            #print(json.dumps(times, indent=4))
            station_info = [station for station in times if station['StationToStationInfos'][0]['DestinationStation'] == s2['StationCode']][0]
            time_to_next = int(station_info['StationToStationInfos'][0]['RailTime'])
            station1 = Station(s1['StationCode'], s1['StationName'])
            station2 = Station(s2['StationCode'], s2['StationName'])
            station_pair = StationPair(station1, station2, time_to_next)
            self.path.append(station_pair)

    def __str__(self):
        string = ""
        for pair in self.path:
            string = string + str(pair) + "\n"
        return string

    def next_station(self, station_name):
        return [pair.station2.station_name for pair in self.path if pair.station1.statin_name == station_name][0]

    def n_next_station(self, station_name, n):
        for _ in range(n):
            station_name = self.next_station(station_name)
        return station_name


class Trip:
    def __init__(self, start_station):
        # start_station - LocationName for the train when the Trip "starts".
        # This is not necessarily where a train originates, just it's first
        # location when we start recording it
        self.start_station = start_station
        self.locations = []




def min_to_num(time):
    if time == "BRD":
        return 0.1
    if time == "ARR":
        return 0.5
    if time == "---" or time == "":
        return float('Inf')
    else:
        try:
            return int(time)
        except ValueError:
            return float('Inf')

class Train:
    def __init__(self, train_json):
        self.group            = train_json['Group']
        self.car              = train_json['Car']
        self.destination_name = train_json['DestinationName']
        self.destination_code = train_json['DestinationCode']
        self.destination      = train_json['Destination']
        self.line             = train_json['Line']
        self.location_code    = train_json['LocationCode']
        self.location_name    = train_json['LocationName']
        self.mins             = train_json['Min']

    def __str__(self):
        string = ""
        string = string + "{}: {}\n".format("Line", self.line)
        string = string + "{}: {}\n".format("\tDest", self.destination_name)
        string = string + "{}: {}\n".format("\tMin", self.mins)
        string = string + "{}: {}\n".format("\tLoc", self.location_name)
        return string

    def is_empty_car(self):
        return (self.car is None or self.car == '-')

    def is_destination(self, destination_name):
        return self.destination_name == destination_name

    def is_location(self, location_name):
        return self.location_name == location_name

    def is_destination_by_code(self, destination_code):
        return self.destination_code == destination_code

    def is_location_code(self, location_code):
        return self.location_code == location_code

    def arrive_time_less(self, time):
        return min_to_num(self.mins) < time

def is_empty_car(train):
    return (train['Car'] is None or train['Car'] == '-')

def is_destination(train, destination_name):
    return train['DestinationName'] == destination_name

def is_location(train, location):
    return train['LocationName'] == location

def is_destination_by_code(train, destination_code):
    return train['DestinationCode'] == destination_code

def is_location_code(train, location_code):
    return train['LocationCode'] == location_code

def arrive_time_less(train, time):
    return min_to_num(train['Min']) < time

def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)

# Need to make sure that the trains are unique. If the time for a train pulling into a station is

# Example
# ----- T1 --------- S1 --------------- S2
#        |---2min----|                  |
#        |---------------6min-----------|
#
# Train 1 (T1) is approaching both Station 1 (S1) and Station 2 (S2).
# When we get the time predictions, we get 2 predictions, 1 with a train that is
# 2 min from S1 and another that is 6 min from (S2). However, we know the
# estimated travel time (schedule time) in minutes between the source and destination stations,
# S1 and S2 (NB: This is not correlated to minutes (Min) in Real-Time Rail Predictions.).
# If we know that the estimated shcedule time from S1 to S2 is 4 min, we can throw away the second
# arrvival prediction since it is above the estimated schedule time. This is tricky because if
# the trains get delayed, then a train between S1 and S2 could take more than the scheduled
# 4 minutes.


# def get_line(name, start_code, end_code):
#     path = get_path(start_code, end_code)
#     #print(path)
#     times = get_time_between_stations(name, path)
#     return Line(name, path, times)

# def get_line2(origin_code, destination_code):
#     #path = get_path(start_code, end_code)

#     #print(path)
#     #times = get_time_between_stations(name, path)
#     #return Line(name, path, times)
#     pass

#path = get_path("A15", "B11")
#path = get_line2("A15", "B11")

# Get the schedule information
def get_time_between_stations(name, path):
    station_times_file = name + "_times.txt"
    if not isfile(station_times_file):
        with open(station_times_file, "w") as f:
            station_times = []
            for station1, station2 in pairwise(path['Path']):
                params = urllib.parse.urlencode({
                    # Request parameters
                    'FromStationCode': station1['StationCode'],
                    'ToStationCode': station2['StationCode'],
                    })


                try:
                    conn = http.client.HTTPSConnection('api.wmata.com')
                    conn.request("GET", "/Rail.svc/json/jSrcStationToDstStationInfo?%s" % params, "{body}", headers)
                    response = conn.getresponse()
                    data = response.read().decode('utf-8')
                    parsed = json.loads(data)
                    station_times.append(parsed)
                    conn.close()
                except Exception as e:
                    print("[Errno {0}] {1}".format(e.errno, e.strerror))

            f.write(json.dumps(station_times, indent=4))
            return station_times
    else:
        with open(station_times_file, 'r') as f:
            station_times  = f.read()
            return json.loads(station_times)

def add_next_info(df):
    df




def average_trains(destination_name, line):
    trains = get_trains(destination_name, line)
    print(trains)
    time.sleep(10)
    new_trains = get_trains(destination_name, line)
    for train_pairs in itertools.product(trains, new_trains):
        print(score_train_similarity(train_pairs[0], train_pairs[1], line, 1/6))

def score_train_similarity(train1, train2, line, time_between_query):
    score = 0
    print(train1.location_name)
    print(line)
    next_station = line.next_station(train1.location_name)
    next_2_station = line.n_next_station(train1.location_name, 2)
    if train1.location_name == train2.location_name:
        score += abs(train1.mins - train2.mins)/time_between_query
    elif train2.location_name == next_station:
        score += 1
    elif train2.location_name == next_2_station:
        score += 3
    else:
        score += 10

    return score




# Get the real time predictions

#print('###################################')
#red_line = get_line("RD","A15","B11")
#print(aed_line)
#print('###################################')
#print(get_trains("Glenmont", red_line))
#path = get_line2("A15", "B11")



def get_line(line_start_code, line_end_code):

    # Get the path from Shady Grove to Glenmont
    params = urllib.parse.urlencode({
        # Request parameters
        'FromStationCode': line_start_code,
        'ToStationCode': line_end_code,
        })

    try:
        conn = http.client.HTTPSConnection('api.wmata.com')
        conn.request("GET", "/Rail.svc/json/jPath?%s" % params, "{body}", headers)
        response = conn.getresponse()
        data = response.read().decode('utf-8')
        path = json.loads(data)
        pddata = json_normalize(path['Path'])
        conn.close()
        return pddata
    except Exception as e:
        print("[Errno {0}] {1}".format(e.errno, e.strerror))


def time_between_stations(from_station_code, to_station_code):
    params = urllib.parse.urlencode({
        'FromStationCode': from_station_code,
        'ToStationCode': to_station_code,
        # Request parameters
        })
    try:
        conn = http.client.HTTPSConnection('api.wmata.com')
        conn.request("GET", "/Rail.svc/json/jSrcStationToDstStationInfo?%s" % params, "{body}", headers)
        response = conn.getresponse()
        data = response.read().decode('utf-8')
        parsed = json.loads(data)
        pddata = json_normalize(parsed['StationToStationInfos'])
        conn.close()
        return pddata.RailTime.astype('int').sum()
    except Exception as e:
        print("[Errno {0}] {1}".format(e.errno, e.strerror))



def get_line_with_times(line_start_code, line_end_code):
    pddata = get_line(line_start_code, line_end_code)
    pddata['RailTime'] = 0
    times = [0,]
    for s1, s2 in pairwise(pddata.StationCode):
        times.append(time_between_stations(s1,s2))
    #times.append(0)
    pddata['RailTime'] = times
    return pddata


#red_line_B11 = get_line_with_times('A15','B11') # red line Glenmont train
#red_line_B11.to_pickle("RD_B11.pkl")
#red_line_B08 = get_line_with_times('A15','B08') # red line Silver Spring train
#red_line_B08.to_pickle("RD_B08.pkl")
#red_line_A15 = get_line_with_times('B11','A15')
#red_line_A15.to_pickle("RD_A15.pkl")
red_line_B11 = pd.read_pickle("RD_B11.pkl")
#print(red_line_B11.head(30))
#print(red_line_B11[red_line_B11.StationCode == "A03"])
#print(red_line_B11.head(10))
red_line_A15 = pd.read_pickle("RD_A15.pkl")
red_line_B08 = pd.read_pickle("RD_B08.pkl")
#green_line_F11 = get_line_with_times('E10','F11')
#green_line_E10 = get_line_with_times('F11','E10')
#print(green_line_E10.head(30))

def get_predictions():
    try:
        params = urllib.parse.urlencode({
            })
        conn = http.client.HTTPSConnection('api.wmata.com')
        conn.request("GET", "/StationPrediction.svc/json/GetPrediction/All?%s" % params, "{body}", headers)
        response = conn.getresponse()
        data = response.read().decode('utf-8')
        parsed = json.loads(data)
        prediction_df = json_normalize(parsed['Trains'])
        conn.close()
        return prediction_df
    except Exception as e:
        print("[Errno {0}] {1}".format(e.errno, e.strerror))


def get_trains(prediction_data, line_df, destination_codes, line_code):
    train_df = prediction_data[prediction_data.Line == line_code]
    train_df = train_df[train_df.DestinationCode.isin(destination_codes)]
    train_df = train_df.merge(line_df[['StationCode', 'RailTime']], left_on='LocationCode', right_on='StationCode')
    train_df = train_df[train_df.Min.apply(min_to_num)<(train_df.RailTime)]
    # add timestamp and initialize ID to -1
    train_df.reset_index(drop=True, inplace=True)
    train_df.index.names = ["idx"]
    train_df['ID'] = -1
    #cur_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    #train_df['timestamp'] = cur_time
    #train_df.set_index('timestamp', append=True, inplace=True)
    #train_df = train_df.swaplevel()
    return train_df

def num_away(location_code_1, location_code_2, line_df):
    idx_2 = line_df[line_df.StationCode == location_code_2].index.item()
    idx_1 = line_df[line_df.StationCode == location_code_1].index.item()
    return idx_2 - idx_1


def train_distance(train_1, train_2, line_df):
    #compare location codes
    score = 0
    location_difference = num_away(train_1.LocationCode, train_2.LocationCode, line_df)
    if location_difference < 0:
        score = score - location_difference*2
    if location_difference == 1:
        score = score + location_difference/2
        # also use time
        score = score + (line_df[line_df.StationCode == train_2.LocationCode].RailTime.item() - min_to_num(train_2.Min) + min_to_num(train_1.Min))/4
    if location_difference > 1:
        score = score + location_difference/2
    if location_difference == 0:
        # then compare Min estimates
        time_diff_score = (min_to_num(train_1.Min) - min_to_num(train_2.Min))/line_df[line_df.StationCode == train_1.LocationCode].RailTime.item()
        if time_diff_score >= 0:
            score = score + time_diff_score
        else:
            # train has gone backwards in time. Penalize
            score = score + 100
    if (train_1.Car != train_2.Car):
        score = score + 100
    if (train_1.DestinationCode != train_2.DestinationCode):
        score = score + 100
    return score

def distance_matrix(train_df_1, train_df_2, line_df):
    m = train_df_1.shape[0]
    n = train_df_2.shape[0]
    mat = np.zeros([m,n])
    for i in range(m):
        for j in range(n):
            mat[i,j] = train_distance(train_df_1.iloc[i], train_df_2.iloc[j], line_df)
    return mat

def match_trains(train_df_1, train_df_2, line_df):
    m = train_df_1.shape[0]
    n = train_df_2.shape[0]
    distances = distance_matrix(train_df_1, train_df_2, line_df)
    print(distances)
    matches = []
    for i in range(m):
        j = np.argmin(distances[i,:])
        if distances[i,j] <= 1:
            matches.append((i,j))
    return matches

def assign_matches(train_df_1, train_df_2, line_df):
    matches = match_trains(train_df_1, train_df_2, line_df)
    for match in matches:
        i,j = match
        if train_df_2.ix[j, 'ID'].item() == -1:
            train_df_2.ix[j,'ID'] = train_df_1.ix[i, 'ID'].item()

    return train_df_2

def match_back(train_df_list, line_df):
    back = 5
    l = len(train_df_list)
    cur_df = train_df_list[-1]
    prev_df = train_df_list[-2]
    # assign current matches
    cur_df = assign_matches(prev_df, cur_df, line_df)
    # see if anything is unmatched
    num_unmatched = cur_df[cur_df.ID == -1].count()
    if num_unmatched > 0:
        if l >= 3:
            prev_2_df = train_df_list[-3]
            cur_df = assign_matches(prev_2_df, cur_df, line_df)

def new_id(i=itertools.count()):
    return next(i)



#preds = get_predictions()
#print(json.dumps(json.loads(preds.to_json(orient='records')),indent=4))
#print(pd.read_json(preds).head(10))
#train_df = get_trains(preds, red_line_B11, ["B08", "B11"], "RD")
#train_df.reset_index(drop=True)
#print(train_df.head(100))
#for i in train_df.itertuples():
#    print(i)
#t1 = train_df.iloc[0]
#t1_2 = train_df.iloc[0]
#print("tain distance: {}".format(train_distance(t1, t1_2, red_line_B11)))
#time.sleep(20)
#preds = get_predictions()
#train_df = get_trains(preds, red_line_B11, ["B08", "B11"], "RD")
#print(train_df.head(100))
#for i in train_df.itertuples():
#    print(i)


#print(red_line_B11.head(27))
#print(red_line_A15.head(27))

# params = urllib.parse.urlencode({
#     # Request parameters
#     'LineCode': 'GR',
# })

# try:
#     conn = http.client.HTTPSConnection('api.wmata.com')
#     conn.request("GET", "/Rail.svc/json/jStations?%s" % params, "{body}", headers)
#     response = conn.getresponse()
#     data = response.read().decode('utf-8')
#     parsed = json.loads(data)
#     print(json.dumps(parsed, indent=4))
#     conn.close()
# except Exception as e:
#     print("[Errno {0}] {1}".format(e.errno, e.strerror))
