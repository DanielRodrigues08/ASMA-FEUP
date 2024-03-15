import spade
from spade.agent import Agent
from spade.behaviour import FSMBehaviour, State
from spade.message import Message
from utils import msg_orders_to_list


BEGIN = "BEGIN"
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

        if self.agent.battery == 0:
            self.set_next_state(NO_BATTERY)
            return
    
        msg = await self.receive(timeout=0) # waits for a confirmation from the center that he will receive orders
        
        if msg.body == "ORDER_READY":
            ans       = Message(to=str(msg.sender))
            ans.body  = "OK"
            await self.send(ans)        
        
        if msg.body == "RECEIVE_ORDER":
            self.set_next_state(RETURNING_CENTER)
        else:
            await self.agent.stop()

            
class Delivering(State):

    async def run(self):
        print(f"Drone delivering orders")
        while len(self.agent.orders) > 0:
            #implement logic for delivering
            #drone going to the points of the orders, and when reaching, the order is deleted from the attribute, until the attribute has 0 orders
            self.agent.orders.pop(0)
            self.set_next_state(BEGIN)

class ReturningCenter(State):
    async def run(self):
        print(f"Drone returning to the center")
        #implement logic for returning to the center (point of the last order -> point of the center)
        #after going to center replenish battery
        self.agent.battery = self.agent.autonomy
        self.set_next_state(BEGIN)
        
class NoBattery(State):
    async def run(self):
        print(f"Drone has no battery/finished its deliveries")
        await self.agent.stop()        
        
class DroneAgent(Agent):

    def __init__(self, jid, password, position, battery, autonomy, velocity, max_capacity, center_jid, orders=None):
        
        super().__init__(jid, password) 

        self.orders       = [] if orders is None else orders
        self.position     = position # initial position of the center
        self.battery      = battery  # percentage calculated with the autonomy and distance traveled (?)
        self.autonomy     = autonomy # on the csv
        self.velocity     = velocity # on the csv
        self.max_capacity = max_capacity # on the csv
        
        
        
    async def setup(self):

        drone = StateBehaviour()
        drone.add_state(name=BEGIN, state=Begin(), initial=True)
        drone.add_state(name=DELIVERING, state=Delivering())
        drone.add_state(name=RETURNING_CENTER, state=ReturningCenter())
        drone.add_state(name=NO_BATTERY, state=NoBattery())
        drone.add_transition(source=DELIVERING, dest=RETURNING_CENTER)
        drone.add_transition(source=RETURNING_CENTER, dest=NO_BATTERY)
        self.add_behaviour(drone)
