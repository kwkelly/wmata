import train
import pandas as pd
import numpy as np
import time
import datetime
import itertools
from collections import namedtuple
np.set_printoptions(suppress=True)

train_data = namedtuple('train_data',['timestamp','trains'])
train_list = []


red_line_B11 = pd.read_pickle("RD_B11.pkl")
print(red_line_B11.head(100))
for i in range(2):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    train_df = train.get_trains(train.get_predictions(), red_line_B11, ["B08", "B11"], "RD")
    if i == 0:
        train_df['ID'] = train_df.apply(lambda row: train.new_id(), axis=1)
        train_list.append(train_data(timestamp,train_df))
    else:
        for j in range(0,min(i,1)):
            train_df = train.assign_matches(train_list[-i].trains, train_df, red_line_B11)
        #still couldn't match anythin
        train_df['ID'] = train_df.apply((lambda row: row['ID'] if row['ID'] >=0 else train.new_id()), axis=1)
        train_list.append(train_data(timestamp,train_df))


    print(train_list[-1].timestamp)
    print(train_list[-1].trains.head(100))
    time.sleep(30)

