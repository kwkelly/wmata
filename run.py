import json
import http.client, urllib.request, urllib.parse, urllib.error, base64
from itertools import tee

headers = {
    # Request headers
    'api_key': 'ee40c31d5b524b8c839a91280aebaccc',
}

params = urllib.parse.urlencode({
})

def min_to_num(time):
    if time == "BRD" or time == "ARR":
        return 0
    if time == "---" or time == "":
        return float('Inf')
    else:
        try:
            return int(time)
        except ValueError:
            return float('Inf')

def is_empty_car(train):
    return (train['Car'] is None or train['Car'] == '-')

def is_destination(train, destination):
    return train['DestinationName'] == destination

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


# Get the path from Shady Grove to Glenmont
# A15 - Shady Grove
# B11 - Glenmont

params = urllib.parse.urlencode({
    # Request parameters
    'FromStationCode': 'A15',
    'ToStationCode': 'B11',
})

try:
    conn = http.client.HTTPSConnection('api.wmata.com')
    conn.request("GET", "/Rail.svc/json/jPath?%s" % params, "{body}", headers)
    response = conn.getresponse()
    data = response.read().decode('utf-8')
    path = json.loads(data)
    for station in path['Path']:
        print(station['StationName'])
    conn.close()
except Exception as e:
    print("[Errno {0}] {1}".format(e.errno, e.strerror))

####################################
print('###################################')


# Get the schedule information
for station1, station2 in pairwise(path['Path']):
    params = urllib.parse.urlencode({
        # Request parameters
        'FromStationCode': station1['StationCode'], # Woodley Park
        'ToStationCode': station2['StationCode'], # Dupont --> Glenmont bound train
    })


    try:
        conn = http.client.HTTPSConnection('api.wmata.com')
        conn.request("GET", "/Rail.svc/json/jSrcStationToDstStationInfo?%s" % params, "{body}", headers)
        response = conn.getresponse()
        data = response.read().decode('utf-8')
        parsed = json.loads(data)
        #print(json.dumps(parsed['StationToStationInfos'], indent=4))
        time_between_stations = int(parsed['StationToStationInfos'][0]['RailTime'])*2
        conn.close()
    except Exception as e:
        print("[Errno {0}] {1}".format(e.errno, e.strerror))

    ####################################

    # Get the real time predictions

    try:
        conn = http.client.HTTPSConnection('api.wmata.com')
        conn.request("GET", "/StationPrediction.svc/json/GetPrediction/All?%s" % params, "{body}", headers)
        response = conn.getresponse()
        data = response.read().decode('utf-8')
        parsed = json.loads(data)
        # get only those trains arriving to Dupont
        for train in parsed['Trains']:
            if is_destination(train, 'Glenmont') and is_location(train, station2['StationName']) and arrive_time_less(train, time_between_stations) and not is_empty_car(train):
                print(json.dumps(train))
        #print(json.dumps(parsed, indent=4))
        conn.close()
    except Exception as e:
        print("[Errno {0}] {1}".format(e.errno, e.strerror))

