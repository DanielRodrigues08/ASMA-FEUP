import pandas as pd
import numpy as np
import re
import math
import datetime
from spade.message import Message



def delta(timer, seconds):
    return timer < datetime.datetime.now() - datetime.timedelta(seconds=seconds)


async def receive_msg(agent, jid, timeout):

    timer = datetime.datetime.now()


    # TODO: check template

    while delta(timer, timeout):
         msg = await agent.receive(0)
         if msg and msg.sender == jid:
             return msg

    return None

def msg_orders_to_list(msg):
    orders = msg.body.split(" ")
    return orders

def csv_centers_to_system(csv):
    df = pd.read_csv(csv, sep=';')
    df['latitude'] = df['latitude'].str.replace(',', '.')
    df['longitude'] = df['longitude'].str.replace(',', '.')  
    df['latitude'] = df['latitude'].astype(float)
    df['longitude'] = df['longitude'].astype(float)  
    return df.values[0].tolist()

def csv_orders_to_system(csv):
    df = pd.read_csv(csv, sep=';')
    orders = []
    df['latitude'] = df['latitude'].str.replace(',', '.')
    df['longitude'] = df['longitude'].str.replace(',', '.')  
    df['latitude'] = df['latitude'].astype(float)
    df['longitude'] = df['longitude'].astype(float)  
    for i in range(1,len(df)):
        current_row = df.iloc[i].values.tolist()
        orders.append(current_row)
    return orders   

def csv_drones_to_system(csv):
    df = pd.read_csv(csv, sep=';')
    df['capacity'] = df['capacity'].str.replace('kg', '')
    df['autonomy'] = df['autonomy'].str.replace('Km', '')
    df['velocity'] = df['velocity'].str.replace('m/s', '')
    df['capacity'] = df['capacity'].astype(float)
    df['autonomy'] = df['autonomy'].astype(float)
    df['velocity'] = df['velocity'].astype(float)
    drones = []
    for i in range(len(df)):
        current_row = df.iloc[i].values.tolist()
        drones.append(current_row)
    return drones

def haversine_distance(lat1, lon1, lat2, lon2):
    dLat = (lat2 - lat1) * math.pi / 180.0
    dLon = (lon2 - lon1) * math.pi / 180.0
    
    lat1 = (lat1) * math.pi / 180.0
    lat2 = (lat2) * math.pi / 180.0
    
    a = (pow(math.sin(dLat / 2), 2) +
         pow(math.sin(dLon / 2), 2) *
             math.cos(lat1) * math.cos(lat2));
    rad = 6371
    c = 2 * math.asin(math.sqrt(a))
    return rad * c
        

if __name__ == "__main__":
    lat1 = 19.01
    lon1 = 72.92
    lat2 = 18.994
    lon2 = 72.8255
     
    print(haversine_distance(lat1, lon1,lat2, lon2), "K.M.")  
         
