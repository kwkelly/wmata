import http.client
import urllib.request
import urllib.parse
import urllib.error
import json
import time
import itertools
import random
import api_key
import csv


headers = {
    # Request headers
    'api_key': api_key.wmata_key,
}


def query_api(endpoint, params, headers):
    try:
        conn = http.client.HTTPSConnection('api.wmata.com')
        conn.request("GET", endpoint % params, "{body}", headers)
        response = conn.getresponse()
        data = response.read().decode('utf-8')
        parsed = json.loads(data)
        conn.close()
        return parsed
    except Exception as e:
        print("[Errno {0}] {1}".format(e.errno, e.strerror))


def get_positions():
    # Positions
    params = urllib.parse.urlencode({
    })
    return query_api("/TrainPositions/TrainPositions?contentType=json&%s",
                     params, headers)


def get_station_list(line_code):
    # Positions
    params = urllib.parse.urlencode({
        'LineCode': line_code,
    })
    return query_api("/Rail.svc/json/jStations?%s",
                     params, headers)


def get_times():
    # Time predictions
    params = urllib.parse.urlencode({
    })
    return query_api("/StationPrediction.svc/json/GetPrediction/All?%s",
                     params, headers)


def get_circuits():
    # Cricuits
    params = urllib.parse.urlencode({
    })
    return query_api("/TrainPositions/TrackCircuits?contentType=json&%s",
                     params, headers)


def get_routes():
    # Standard Routes
    params = urllib.parse.urlencode({
    })
    return query_api("/TrainPositions/StandardRoutes?contentType=json&%s",
                     params, headers)


class TrainInfo():

    def __init__(self):
        self.routes = get_routes()
        self.circuits = get_circuits()
        # get all the lines
        self.line_codes = ['RD', 'YL', 'BL', 'OR', 'GR', 'SV']
        self.track_nums = [1, 2]
        self.directions = [1, 2]
        self.stations_dict = self.create_stations_dict()
        self.circ_seq_dict = self.get_circuit_to_sequence_dict()
        self.circ_track_dict = self.get_circuit_to_track_dict()
        print(self.stations_dict)

    def create_stations_dict(self):
        """
        creates a dict that maps station codes to names
        """
        stations_dict = {}
        for line_code in self.line_codes:
            stations = get_station_list(line_code)
            for station in stations['Stations']:
                stations_dict[station['Code']] = station['Name']
        return stations_dict

    def get_circuit_to_sequence_dict(self):
        """
        returns a dict that maps line_codes and track nums to sequence numbers
        """
        circ_seq_dict = {}
        for line_code in self.line_codes:
            for track_num in self.track_nums:
                circuits = [route for route in self.routes['StandardRoutes']
                            if route['LineCode'] == line_code
                            and route['TrackNum'] == track_num]
                circuits = circuits[0]['TrackCircuits']  # should only be one
                circ_seq_dict['{}{}'.format(line_code, track_num)] =\
                    {circuit['CircuitId']: circuit['SeqNum']
                     for circuit in circuits}
        return circ_seq_dict

    def get_circuit_to_track_dict(self):
        circuits = self.circuits['TrackCircuits']
        return {circuit['CircuitId']: circuit['Track'] for circuit in circuits}

    def get_next_station(self, train):
        track = train['Track']
        seq_num = train['SeqNum']
        line_code = train['LineCode']
        direction = train['DirectionNum']
        line = [route for route in self.routes['StandardRoutes'] if
                route['TrackNum'] == track and
                route['LineCode'] == line_code]
        line = line[0]['TrackCircuits']  # should be only one
        # we should get the next station too
        if direction == 1:
            for circuit in line[seq_num:]:
                if circuit['StationCode'] is not None:
                    return circuit['StationCode']
        if direction == 2:
            for circuit in line[seq_num::-1]:
                if circuit['StationCode'] is not None:
                    return circuit['StationCode']
        return None

    def get_trains(self):
        """
        gets train position and time info and combines them and returns them
        """
        positions = get_positions()
        arrivals = get_times()

        # we have to work on trains by line and direction in order to be able
        # to properly match them
        # not concerned about trains not in service
        all_trains = []
        for line_code in self.line_codes:
            for direction in self.directions:
                # filte trains by line and dir
                trains = [train for train in positions['TrainPositions']
                          if train['LineCode'] == line_code
                          and train['DirectionNum'] == direction
                          and train['ServiceType'] == 'Normal']
                for train in trains:
                    # first we assign the sequence num to each train
                    circuit_id = train['CircuitId']
                    track = self.circ_track_dict[circuit_id]
                    train['DestinationName'] = \
                        self.stations_dict \
                        .get(train['DestinationStationCode'])
                    if track not in [1, 2]:
                        seq_num = None
                    else:
                        seq_num =\
                            self.circ_seq_dict['{}{}'
                                .format(line_code, track)]\
                                .get(circuit_id)
                    train['SeqNum'] = seq_num
                    train['Track'] = track
                    if seq_num is None:
                        continue
                    train['LocationCode'] = self.get_next_station(train)
                    train['LocationName'] = self.stations_dict\
                        .get(train['LocationCode'])

                # remove trains without well defined seq num
                trains = [train for train in trains
                          if train['SeqNum'] is not None]
                # order them
                trains = sorted(trains, key=lambda x: x['SeqNum'])
                # reverse order if going other way
                if direction == 2:
                    trains = trains[::-1]

                # now we can assign time estimates to each of the trains
                for i, arrival in enumerate(arrivals['Trains']):
                    arrival['index'] = i
                for train in trains[::-1]:
                    location_code = train['LocationCode']
                    line_code = train['LineCode']
                    destination = train['DestinationStationCode']
                    # only the times for trains matching these
                    possible_times = [arrival for arrival in arrivals['Trains']
                                      if arrival['DestinationCode'] == destination
                                      and arrival['Line'] == line_code
                                      and arrival['LocationCode'] == location_code]
                    if possible_times:
                        # get the train closest to the station as the one with
                        # the minimum time
                        arrival = min(possible_times, key=time_to_sortable)
                        mins = arrival['Min']
                        index = arrival['index']
                        arrivals['Trains'].pop(index)
                        # reassign indices
                        for i, arrival in enumerate(arrivals['Trains']):
                            arrival['index'] = i
                    else:
                        mins = 0
                    train['Min'] = mins
                all_trains = all_trains + trains
        return all_trains


def time_to_sortable(time):
    if time['Min'] == 'ARR':
        return 0.5
    elif time['Min'] == 'BRD':
        return 0
    elif time['Min'] == '':
        return -1
    else:
        return int(time['Min'])


def get_and_save_trains():
    info = TrainInfo()
    f = open('log.csv', 'a')
    fieldnames = ['Time', 'LineCode', 'DirectionNum', 'Track', 'LocationCode',
                  'LocationName', 'DestinationStationCode', 'DestinationName',
                  'SeqNum', 'SecondsAtLocation', 'Min', 'ServiceType',
                  'CarCount', 'CircuitId', 'TrainId']
    writer = csv.DictWriter(f, fieldnames)
    writer.writeheader()
    f.close()
    for i in itertools.count():
        if i > 0:
            delay = 15
            time.sleep(delay)

        try:
            trains = info.get_trains()
            num = len(trains)
            now = time.time()  # unix time
            for train in trains:
                train['Time'] = now

            print("got {} trains".format(num))

            f = open('log.csv', 'a')
            writer = csv.DictWriter(f, fieldnames)
            writer.writerows(trains)
            f.close()
        except Exception as e:
            print(e)
            continue

if __name__ == "__main__":
    get_and_save_trains()
