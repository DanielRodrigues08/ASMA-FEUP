import asyncio
import spade
import os
from drone import  DroneAgent
from center import Center
from ambient import Ambient
from supplier import Supplier
from utils import csv_centers_to_system, csv_orders_to_system, csv_drones_to_system

CENTERS_DIR = "../centers/"
DRONES_DIR = "../drones/"

async def main():
    center_data = []
    orders_data = []
    drones_data = []
    for filename in os.listdir(CENTERS_DIR):
        center_data = center_data + [csv_centers_to_system(CENTERS_DIR+filename)]
        orders_data = orders_data + [csv_orders_to_system(CENTERS_DIR+filename)]
    for filename in os.listdir(DRONES_DIR):
        drones_data = csv_drones_to_system(DRONES_DIR+filename)
        
    #NOT DEALED YET    
    center       = Center(center_data[0][0]+"@localhost", "pass", orders_data, center_data[0][-2:])
    first_drone  = DroneAgent("drone1@localhost", "pass", "pos", 100, 100, 100, 100, center.jid)
    second_drone = DroneAgent("drone2@localhost", "pass", "pos", 100, 100, 100, 100, center.jid)
    ambient      = Ambient("ambient@localhost", "pass", set((first_drone.jid, second_drone.jid)))
    supplier     = Supplier("supplier@localhost", "pass", set(center.jid))
    print(center.orders)
    await center.start()
    await ambient.start()
    await supplier.start()
    
    print("Center started")
    print("Ambient started")
    print("Supplier started")


    

    center.add_drone(first_drone.jid)
    center.add_drone(second_drone.jid)


    await first_drone.start()
    await second_drone.start()

    print("Drones started")




if __name__ == "__main__":
    spade.run(main())