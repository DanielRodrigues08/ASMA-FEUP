import asyncio
import spade
import os
from drone import DroneAgent
from ambient import Ambient
from center import Center
from support_bases import SupportBase
from utils import csv_centers_to_system, csv_orders_to_system, csv_drones_to_system, position_drones, centers_to_dict, orders_to_dict, rearrange_orders_base

CENTERS_DIR = "../data/centers/"
DRONES_DIR = "../data/drones/"


async def main():
    centers_data = []
    orders_data = []
    drones_data = []


    for filename in os.listdir(CENTERS_DIR):
        centers_data = centers_data + [csv_centers_to_system(CENTERS_DIR + filename)]
        orders_data = orders_data + [csv_orders_to_system(CENTERS_DIR + filename)]


    for filename in os.listdir(DRONES_DIR):
        drones_data = csv_drones_to_system(DRONES_DIR + filename)

    centers_data = centers_to_dict(centers_data)
    orders_data = orders_to_dict(orders_data)
    drones_data = position_drones(drones_data, centers_data)
    drones      = []

    support_bases = []
    support_base = SupportBase("support_base@localhost", "support_base", (0, 0))
    support_bases.append(support_base)
    
    for drone_data in drones_data:
        
        drones.append(DroneAgent(drone_data['id'] + '@localhost', drone_data['password'], drone_data["position"], drone_data['autonomy'],  drone_data['autonomy'], drone_data['velocity'], drone_data['capacity'], support_bases))
    
    drones_jids  = set([x.jid for x in drones])
    ambient      = Ambient("ambient@localhost", "ambient", drones_jids)
    
    centers = []
    
    for center_data in centers_data:
        matching_order = [order for order in orders_data if order['center'] == center_data['id']][0]
        centers.append(Center(center_data['id'] + '@localhost', center_data['id'], (center_data['latitude'], center_data['longitude']), matching_order['orders'], drones_jids))

    await ambient.start(auto_register=True)
    
    await asyncio.sleep(2)

    for center in centers:
        await center.start(auto_register=True)

    for drone in drones:
        await drone.start(auto_register=True)

    await support_base.start(auto_register=True)
    
    print("Center started")
    print("Ambient started")
    print("Supplier started")
    print("Drones started")


if __name__ == "__main__":
    spade.run(main())
