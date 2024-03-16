import pandas as pd
import numpy as np

def msg_orders_to_list(msg):
    orders = msg.body.split(" ")
    return orders

def xsl_centers_to_system(xsl):
    df = pd.read_excel(xsl, header = None)
    centers = []
    for i in range(len(df)):
        if pd.isnull(df.iloc[i, 0]):
            break
        centers.append(df.iloc[i].values.tolist())
    return centers  

def xsl_orders_to_system(xsl):
    df = pd.read_excel(xsl, header = None)
    header_row = [np.nan, 'weight', 'latitude', 'longitude']
    orders = []
    start_saving = False
    for i in range(len(df)):
        current_row = df.iloc[i].values.tolist()
        if current_row == header_row:
            start_saving = True
            continue 
        if start_saving:
            orders.append(current_row)
    return orders     
         
