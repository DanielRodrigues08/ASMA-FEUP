import pandas as pd
import numpy as np

def msg_orders_to_list(msg):
    orders = msg.body.split(" ")
    return orders

def csv_centers_to_system(csv):
    df = pd.read_csv(csv, sep=';')
    return df.values[0].tolist()

def csv_orders_to_system(csv):
    df = pd.read_csv(csv, sep=';')
    orders = []
    for i in range(1,len(df)):
        current_row = df.iloc[i].values.tolist()
        orders.append(current_row)
    return orders   

def csv_drones_to_system(csv):
    df = pd.read_csv(csv, sep=';')
    drones = []
    for i in range(len(df)):
        current_row = df.iloc[i].values.tolist()
        drones.append(current_row)
    return drones
        

def main():
    res = csv_orders_to_system("../delivery_center1.csv")    
    print(res)
    
if __name__ == "__main__":
    main()    
         
