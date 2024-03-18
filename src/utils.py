import pandas as pd
import numpy as np
import re

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
        

def main():
    res = csv_centers_to_system("../centers/delivery_center1.csv")    
    print(res)
    
if __name__ == "__main__":
    main()    
         
