import http.client
import urllib.request
import urllib.parse
import urllib.error
import json
import time
import itertools
import random
import api_key


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


def get_line_stations(routes, line_code):
    line = get_line(routes, line_code)
    order = [circuit['StationCode'] for circuit
             in line['TrackCircuits'] if circuit['StationCode'] is not None]
    return order


def get_line(routes, line_code):
    line = [route for route in routes['StandardRoutes'] if
            route['LineCode'] == line_code][0]
    return line


def get_seq_num(line, circuit_id):
    for circuit in line['TrackCircuits']:
        if circuit['CircuitId'] == circuit_id:
            return circuit['SeqNum']
    return -1


def order_trains_line(positions, routes, line_code, direction):
    # put the trains on a given line in order

    # first get the trains for a given line
    trains = [train for train in positions['TrainPositions']
              if train['LineCode'] == line_code
              and train['DirectionNum'] == direction]
    # for each train, get the SeqNum corresponding to the CircuitID
    line = get_line(routes, line_code)
    for train in trains:
        train['SeqNum'] = get_seq_num(line, train['CircuitId'])
    # sort based on the SeqNum
    trains = sorted(trains, key=lambda x: x['SeqNum'])
    # if the direction is 2, we need to reverse the sort
    if direction == 2:
        trains = trains[::-1]
    return trains


def get_next_station(train, routes):
    line_code = train['LineCode']
    direction = train['DirectionNum']
    seq_num = train['SeqNum']
    line = get_line(routes, line_code)
    # iterate through the list of circuits, starting at seq_num, until we get a
    # circuit with a station code that is not null. We iterate forward for
    # direction==1 and backwards for 2
    if direction == 1:
        for circuit in line['TrackCircuits'][seq_num:]:
            if circuit['StationCode'] is not None:
                return circuit['StationCode']
    if direction == 2:
        for circuit in line['TrackCircuits'][seq_num::-1]:
            if circuit['StationCode'] is not None:
                return circuit['StationCode']
    return None


def get_train_times(times, positions, routes, line_code, direction):
    trains = order_trains_line(positions, routes, line_code, direction)
    for train in trains:
        train['StationCode'] = get_next_station(train, routes)

    # for each train in reverse order, we filter the times array, selecting
    # only trains with matching destination code and line
    # then select the train with the LocationCode with matching location code
    # and shortest time.
    for i, train_time in enumerate(times['Trains']):
        train_time['index'] = i
    for train in trains[::-1]:
        location_code = train['StationCode']
        line = train['LineCode']
        destination = train['DestinationStationCode']
        possible_times = [time for time in times['Trains']
                          if time['DestinationCode'] == destination
                          and time['Line'] == line
                          and time['LocationCode'] == location_code]
        if possible_times:
            time = min(possible_times, key=time_to_sortable)
            mins = time['Min']
            index = time['index']
            times['Trains'].pop(index)
            for i, time_item in enumerate(times['Trains']):
                time_item['index'] = i
        else:
            mins = 0
        train['Min'] = mins
    return trains


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
    lines = ['RD', 'YL', 'BL', 'OR', 'GR', 'SV']
    stations_dict = {}
    for line in lines:
        stations = get_station_list(line)
        stations_dict[line] = {station['Code']: station['Name'] for station
                               in stations['Stations']}
    routes = get_routes()

    for i in itertools.count():
        if i > 0:
            delay = 15 + 10 * random.random()
            print('sleeping {}s...'.format(delay))
            time.sleep(delay)

        try:
            times = get_times()
            positions = get_positions()
            now = time.time()
            data = {}
            data['time'] = now
            for line in lines:
                data['line'] = line
                for direction in [1, 2]:
                    trains = get_train_times(times, positions,
                                             routes, line, direction)
                    for train in trains:
                        train['StationName'] = stations_dict. \
                            get(line).get(train['StationCode'])
                        data["{} {}".format(line, direction)] = trains
            num = sum(len(value) for key, value in data.items()
                      if key != 'time')
            print("got {} trains".format(num))

            f = open('log.jsons', 'a')
            json.dump(data, f)
            f.write('\n')
            f.close()
        except Exception as e:
            print(e)
            continue

if __name__ == "__main__":
    get_and_save_trains()
