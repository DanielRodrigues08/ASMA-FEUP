import asyncio
import spade
import platform
import multiprocessing
import os
import random
from drone import DroneAgent
from ambient import Ambient
from center import Center
from monitor import create_window
from carto import create_gui
from support_bases import SupportBase
from utils import csv_centers_to_system, csv_orders_to_system, csv_drones_to_system, position_drones, centers_to_dict, orders_to_dict

CENTERS_DIR = "../data/centers/"
DRONES_DIR = "../data/drones/"

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

print("CENTERS", centers_data)
print("ORDERS", orders_data)

def get_values():

    min_lat = 999999
    max_lat = -999999
    min_lon = 999999
    max_lon = -999999

    for center in centers_data:
        min_lat = min(min_lat, center['lat'])
        max_lat = max(max_lat, center['lat'])
        min_lon = min(min_lon, center['lon'])
        max_lon = max(max_lon, center['lon'])
    
    for order in orders_data[0]['orders']:
        min_lat = min(min_lat, order[1])
        max_lat = max(max_lat, order[1])
        min_lon = min(min_lon, order[2])
        max_lon = max(max_lon, order[2])

    return {
        "min_lat": min_lat,
        "max_lat": max_lat,
        "min_lon": min_lon,
        "max_lon": max_lon
    }
    
def create_system():

    drones      = []

    support_bases = []
    
    values = get_values()
    
    for i in range(1,16):
        base_jid = "support_base_" + str(i) + "@localhost"
        support_base = SupportBase(base_jid, "support_base", (random.uniform(values["min_lat"], values["max_lat"]), random.uniform(values["min_lon"], values["max_lon"])))
        support_bases.append(support_base)
        
    centers_dict = {center["id"] + "@localhost": {"id": center["id"] + "@localhost", "type": "CENTER", "lat": center["lat"], "lon": center["lon"]} for center in centers_data}
    for drone_data in drones_data:
        
        drones.append(
            DroneAgent(
                drone_data["id"] + "@localhost",
                drone_data["password"],
                drone_data["position"],
                drone_data["autonomy"],
                drone_data["autonomy"],
                drone_data["velocity"],
                drone_data["capacity"],
                centers_dict,
                support_bases
            )
        )

    drones_jids = set([x.jid for x in drones])
    ambient = Ambient("ambient@localhost", "ambient", drones_jids)

    centers = []

    for center_data in centers_data:
        matching_order = [
            order for order in orders_data if order["center"] == center_data["id"]
        ][0]
        centers.append(
            Center(
                center_data["id"] + "@localhost",
                center_data["id"],
                (center_data["lat"], center_data["lon"]),
                matching_order["orders"],
                drones_jids,
            )
        )

    return ambient, centers, drones, support_bases

ambient, centers, drones, support_bases = create_system()

async def main():

    await ambient.start(auto_register=True)

    for drone in drones:
        await drone.start(auto_register=True)

    for center in centers:
        await center.start(auto_register=True)

    for base in support_bases:
        await base.start(auto_register=True)
   
    


def get_position(id=0):
    drones[id].set_flag()
    return drones[id].get_position()

def update_position(position, id=0):
    drones[id].update_position(position)

def run_spade():
    spade.run(main())

        
if __name__ == "__main__":

    values  = get_values()
    manager = multiprocessing.Manager()
    proxy   = manager.list()


    for drone in drones:

        new_xy      = manager.dict()
        new_xy['x'] = 0
        new_xy['y'] = 0
        drone.xy = new_xy
        drone.standby = multiprocessing.Value('b', False)
        proxy.append(drone.xy)
        drone.sim_speed = multiprocessing.Value('i', 1)


    for center in centers:
        center.standby = multiprocessing.Value('b', False)

    drones_stands  = [drone.standby for drone in drones]
    centers_stands = [center.standby for center in centers]
    speeds_values  = [drone.sim_speed for drone in drones]
    ambient.trigger = manager.dict()
    ambient.trigger['Raining'] = False
    ambient.trigger['Windy']   = False
    ambient.trigger['Sunny']   = False

    p1 = multiprocessing.Process(target=create_window, args=(drones_stands, centers_stands, ambient.trigger, speeds_values))
    p3 = multiprocessing.Process(target=create_gui, args=(len(drones), proxy, values, [center.position for center in centers], [base.position for base in support_bases]))

    p1.start()    
    p3.start()
    run_spade()
    p1.join()
    p3.join()
