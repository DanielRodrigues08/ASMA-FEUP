import pandas as pd
import numpy as np
import re
import math
import datetime
from itertools import permutations
from spade.message import Message



def delta(timer, seconds):
    return timer < datetime.datetime.now() - datetime.timedelta(seconds=seconds)


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

def centers_to_dict(centers):
    centers_data = []
    for center in centers:
        center_data = {'id': center[0], 'latitude': center[1], 'longitude': center[2]}
        centers_data.append(center_data)
    return centers_data

def orders_to_dict(orders):
    orders_data = []
    for order in orders:
        order_data = {'center': order[0][0], 'orders': order[1:]}
        orders_data.append(order_data)
    return orders_data

def csv_orders_to_system(csv):
    df = pd.read_csv(csv, sep=';')
    orders = []
    df['latitude'] = df['latitude'].str.replace(',', '.')
    df['longitude'] = df['longitude'].str.replace(',', '.')  
    df['latitude'] = df['latitude'].astype(float)
    df['longitude'] = df['longitude'].astype(float)  
    for i in range(0,len(df)):
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

def position_drones(drones, center):


    drones_data = []
    
    for i in range(len(drones)):

        drone      = drones[i]
        drone_data = {'id': drone[0], 'password': drone[0], 'capacity': drone[1], 'autonomy': drone[2], 'velocity': drone[3]}

        for j in range(len(center)):
            if drone[4] == center[j]['id']:
                drone_data['position'] = (center[j]['latitude'],center[j]['longitude'])
                break

        drones_data.append(drone_data)
    return drones_data
            

def haversine_distance(lat1, lon1, lat2, lon2):
    dLat = (lat2 - lat1) * math.pi / 180.0
    dLon = (lon2 - lon1) * math.pi / 180.0
    
    lat1 = (lat1) * math.pi / 180.0
    lat2 = (lat2) * math.pi / 180.0
    
    a = (pow(math.sin(dLat / 2), 2) +
         pow(math.sin(dLon / 2), 2) *
             math.cos(lat1) * math.cos(lat2))
    rad = 6371
    c = 2 * math.asin(math.sqrt(a))
    return rad * c       

def rearrange_orders_base(drone1, pending_orders_1, drone2, pending_orders_2):
    pending_orders = pending_orders_1 + pending_orders_2
    
    all_combos = []
    utility_drone_1 = []
    utility_drone_2 = []
    
    for r in range(1, len(pending_orders)+1):
        all_combos.extend([list(perm) for perm in permutations(pending_orders, r)])

    #checkar melhores combos para drone 1
    for combo in all_combos:
        utility_1 = 0
        utility_2 = 0
        for element in combo:
            utility_1 = utility_1 + drone1.utility(element) 
            utility_2 = utility_2 + drone2.utility(element) 

        utility_data_1 = (combo, utility_1)
        utility_data_2 = (combo, utility_2)
        
        utility_drone_1.append(utility_data_1)
        utility_drone_2.append(utility_data_2)
        
    utility_drone_1 = sorted(utility_drone_1, key=lambda x: x["utility"], reverse=True)
    utility_drone_2 = sorted(utility_drone_2, key=lambda x: x["utility"], reverse=True)  
    
    return utility_drone_1, utility_drone_2