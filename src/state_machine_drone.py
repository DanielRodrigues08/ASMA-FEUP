import spade
from spade.agent import Agent
from spade.behaviour import FSMBehaviour, State
from spade.message import Message
from utils import msg_orders_to_list


BEGIN = "BEGIN"
NEGOTIATING = "NEGOTIATING"
DELIVERING = "DELIVERING"
RETURNING_CENTER = "RETURNING_CENTER"
NO_BATTERY = "NO_BATTERY"


class StateBehaviour(FSMBehaviour):
    async def on_start(self):
        print(f"FSM starting at initial state {self.current_state}")

    async def on_end(self):
        print(f"FSM finished at state {self.current_state}")
        await self.agent.stop()


class Begin(State):
    async def run(self):
        print(f"Drone ready to receive orders")
        msg = Message(to=str(self.agent.center_jid))#msg to the center (center jid)
        msg.body = "Ready to deliver"
        await self.send(msg)
        
        msg_recv= await self.receive(timeout=10) #waits for a confirmation from the center that he will receive orders
        if msg_recv.body == "OK":
            self.set_next_state(NEGOTIATING)
        else:
            await self.agent.stop()
            
class Negotiating(State): #for now, just receive orders without negotiation
    async def run(self):
        print(f"Drone negotiating with the center")   
        msg = Message(to=str(self.agent.center_jid)) #msg to the center (center jid)
        msg.body = "Orders for me"
        await self.send(msg)
        
        msg_conf = await self.receive(timeout=10) #waits for a confirmation from the center that he will receive orders
        if msg_conf:
            self.agent.orders = msg_orders_to_list(msg_conf) #assign the order to the attribute orders of the drone
            msg2 = Message(to=str(self.agent.center_jid)) #msg to the center (center jid)
            msg2.body = "Orders received"
            await self.send(msg2)
            self.set_next_state(DELIVERING)
        else:  
            self.set_next_state(BEGIN)  
            
class Delivering(State):
    async def run(self):
        print(f"Drone delivering orders")
        while len(self.agent.orders) > 0:
            #implement logic for delivering
            #drone going to the points of the orders, and when reaching, the order is deleted from the attribute, until the attribute has 0 orders
            self.agent.orders.pop(0)
        #implement logic for delivering
        #drone going to the points of the orders, and when reaching, the order is deleted from the attribute, until the attribute has 0 orders        
        if len(self.agent.orders) == 0:
            self.set_next_state(RETURNING_CENTER)                   


class ReturningCenter(State):
    async def run(self):
        print(f"Drone returning to the center")
        #implement logic for returning to the center (point of the last order -> point of the center)
        self.set_next_state(NO_BATTERY) #assuming that the drone "dies" and doesnt do nothing more
        
class NoBattery(State):
    async def run(self):
        print(f"Drone has no battery/finished its deliveries")
        await self.agent.stop()        
        
class DroneAgent(Agent):
    def __init__(self, jid, password, position, battery, autonomy, velocity, max_capacity, center_jid, orders=None):
        super().__init__(jid, password) #superclass Agent
        self.orders = [] if orders is None else orders
        self.position = position #initial position of the center
        self.battery = battery #percentage calculated with the autonomy and distance traveled (?)
        self.autonomy = autonomy #on the csv
        self.velocity = velocity #on the csv
        self.max_capacity = max_capacity #on the csv
        self.center_jid = center_jid   #jid of the center
        
        
        
    async def setup(self):
        drone = StateBehaviour()
        drone.add_state(name=BEGIN, state=Begin(), initial=True)
        drone.add_state(name=NEGOTIATING, state=Negotiating())
        drone.add_state(name=DELIVERING, state=Delivering())
        drone.add_state(name=RETURNING_CENTER, state=ReturningCenter())
        drone.add_state(name=NO_BATTERY, state=NoBattery())
        drone.add_transition(source=BEGIN, dest=NEGOTIATING)
        drone.add_transition(source=NEGOTIATING, dest=DELIVERING)
        drone.add_transition(source=NEGOTIATING, dest=BEGIN)
        drone.add_transition(source=DELIVERING, dest=RETURNING_CENTER)
        drone.add_transition(source=RETURNING_CENTER, dest=NO_BATTERY)
        self.add_behaviour(drone)


#async def main():
 #   droneagent = DroneAgent("drone@localhost", "pass")
  #  await droneagent.start()

  #  await spade.wait_until_finished(droneagent)
  #  await droneagent.stop()
  #  print("Agent finished")

#if __name__ == "__main__":
 #   spade.run(main())