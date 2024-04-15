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

def main():
    print(find_orders_with_ids([[[{'id': 'order1_79', 'd_lat': 18.977584, 'd_long': 72.882585, 'o_lat': 18.994237, 'o_long': 72.825553, 'weight': 5}, {'id': 'order1_78', 'd_lat': 19.017584, 'd_long': 72.922585, 'o_lat': 18.994237, 'o_long': 72.825553, 'weight': 5}], 103.00345356589233], [[{'id': 'order1_78', 'd_lat': 19.017584, 'd_long': 72.922585, 'o_lat': 18.994237, 'o_long': 72.825553, 'weight': 5}, {'id': 'order1_79', 'd_lat': 18.977584, 'd_long': 72.882585, 'o_lat': 18.994237, 'o_long': 72.825553, 'weight': 5}], 103.00345356589233], [[{'id': 'order1_79', 'd_lat': 18.977584, 'd_long': 72.882585, 'o_lat': 18.994237, 'o_long': 72.825553, 'weight': 5}, {'id': 'order2_78', 'd_lat': 19.007584, 'd_long': 72.912585, 'o_lat': 18.927584, 'o_long': 72.832585, 'weight': 10}], 83.85516740075536], [[{'id': 'order2_78', 'd_lat': 19.007584, 'd_long': 72.912585, 'o_lat': 18.927584, 'o_long': 72.832585, 'weight': 10}, {'id': 'order1_79', 'd_lat': 18.977584, 'd_long': 72.882585, 'o_lat': 18.994237, 'o_long': 72.825553, 'weight': 5}], 83.85516740075536], [[{'id': 'order1_78', 'd_lat': 19.017584, 'd_long': 72.922585, 'o_lat': 18.994237, 'o_long': 72.825553, 'weight': 5}, {'id': 'order2_78', 'd_lat': 19.007584, 'd_long': 72.912585, 'o_lat': 18.927584, 'o_long': 72.832585, 'weight': 10}], 79.60480655754694], [[{'id': 'order2_78', 'd_lat': 19.007584, 'd_long': 72.912585, 'o_lat': 18.927584, 'o_long': 72.832585, 'weight': 10}, {'id': 'order1_78', 'd_lat': 19.017584, 'd_long': 72.922585, 'o_lat': 18.994237, 'o_long': 72.825553, 'weight': 5}], 79.60480655754694], [[{'id': 'order1_79', 'd_lat': 18.977584, 'd_long': 72.882585, 'o_lat': 18.994237, 'o_long': 72.825553, 'weight': 5}], 53.62690720455038], [[{'id': 'order1_78', 'd_lat': 19.017584, 'd_long': 72.922585, 'o_lat': 18.994237, 'o_long': 72.825553, 'weight': 5}], 49.37654636134195], [[{'id': 'order2_78', 'd_lat': 19.007584, 'd_long': 72.912585, 'o_lat': 18.927584, 'o_long': 72.832585, 'weight': 10}], 30.228260196204978]], ['order2_78', 'order1_79']))

if __name__ == "__main__":
    main()