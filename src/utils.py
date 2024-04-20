import pandas as pd
import numpy as np
import re
import math
import datetime
import heapq
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
        center_data = {'id': center[0], 'lat': center[1], 'lon': center[2]}
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
                drone_data['position'] = (center[j]['lat'],center[j]['lon'])
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

def find_orders_with_ids(orders, order_ids):
    result = []
    order_ids_set = set(order_ids)  # Convert list to set for expected IDs
    required_length = len(order_ids_set)  # The number of unique order IDs required in the sub-list

    for order_list in orders:
        current_order_ids = {order['id'] for order in order_list[0]}

        if current_order_ids == order_ids_set:
            result.append(order_list)

    return result
   

def find_missing_orders(sub_list, pending_orders):
    existing_order_ids = {order['id'] for order in sub_list[0]}  # sub_list[0] contains the orders

    missing_orders = [order for order in pending_orders if order['id'] not in existing_order_ids]
    return missing_orders

def get_all_stats(stats, times_drones, total_time_working):
    total_time = 0
    min_time = 0
    max_time = 0
    mean_time = 0
    
    times = [item['time'] for sublist in stats for item in sublist]
    
    mean_time = np.mean(times)
    max_time = np.max(times)
    min_time = np.min(times)
    total_time = np.sum(times)
    
    dict_drone_time = []
    
    for drone in times_drones:
        time_working = drone['time'] / total_time_working
        if time_working > 1.0:
            time_working = 1.0
        dict_drone_time.append({'drone': drone['drone'], 'total_time': total_time, 'min_time': min_time, 'max_time': max_time, 'mean_time': mean_time, 'time_working': time_working})    
        print(f"Drone {drone['drone']} occupation rate {time_working}")
    
    dict_drone_time = sorted(dict_drone_time, key=lambda x: x['drone'])
    
    print(f"Total time:", total_time, "s")
    print(f"Minimum time:", min_time, "s")
    print(f"Maximum time:", max_time, "s")
    print(f"Mean time:", mean_time, "s")
    
    df = pd.DataFrame(dict_drone_time)
    
    df.to_csv('../stats/drone_stats.csv', sep=';', index=False)
    
    return total_time, min_time, max_time, mean_time, dict_drone_time