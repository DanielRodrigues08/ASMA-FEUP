import spade
import json
from spade.agent import Agent
from spade.behaviour import FSMBehaviour, State, CyclicBehaviour
from spade.message import Message
from utils import msg_orders_to_list, haversine_distance, delta
import datetime

LISTEN           = "LISTEN"
DELIVERING       = "DELIVERING"
RETURNING_CENTER = "RETURNING_CENTER"
NO_BATTERY       = "NO_BATTERY"
WAITING_BID      = "WAITING_BID"
TIMEOUT          = 10



class StateBehaviour(FSMBehaviour):
    async def on_start(self):
        print(f"FSM starting at initial state {self.current_state}")

    async def on_end(self):
        print(f"FSM finished at state {self.current_state}")
        await self.agent.stop()


class Listen(State):
    async def run(self):

        if self.agent.battery == 0:
            self.set_next_state(NO_BATTERY)
            return

        msg = await self.receive(timeout=0)
        
        if msg is None:
            self.set_next_state(LISTEN)
            return
        
        payload = json.loads(msg.body)

        match payload["type"]:

            case "NEW_ORDER":

                print(f"Drone received orders from center")
                ans      = Message(to=str(msg.sender))
                ans.body = json.dumps({"type": "BID", "payload": self.agent.utility(payload["order"])})
                ans.set_metadata("performative", "propose")

                await self.send(ans)

                self.agent.pending = (msg.sender, payload["order"])
                self.set_next_state(WAITING_BID)
        return


class WaitingBid(State):

    async def run(self):


        msg           = None
        center, order = self.agent.pending
        found         = False


        while delta(self.timer, TIMEOUT) and not found:
            msg = await self.receive(timeout=0)
            if msg.sender == center:
                found = True

        if not found:
            self.set_next_state(LISTEN)
            return

        payload = json.loads(msg.body)

        if payload["type"] == "ACCEPT":
            
            print(f"Drone received bid from center")
            self.agent.orders.append(order)
            await self.send(Message(to=center, body=json.dumps({"type": "OK"}), performative="inform"))
    
        self.set_next_state(LISTEN)  
        return



class Delivering(State):

    async def run(self):
        print(f"Drone delivering orders")
        while len(self.agent.orders) > 0:
            # implement logic for delivering
            # drone going to the points of the orders, and when reaching, the order is deleted from the attribute, until the attribute has 0 orders
            self.agent.orders.pop(0)
            self.set_next_state(LISTEN)


class ReturningCenter(State):
    async def run(self):
        print(f"Drone returning to the center")
        # implement logic for returning to the center (point of the last order -> point of the center)
        # after going to center replenish battery
        self.agent.battery = self.agent.autonomy
        self.set_next_state(LISTEN)


class NoBattery(State):
    async def run(self):
        print(f"Drone has no battery/finished its deliveries")
        await self.agent.stop()


class DroneAgent(Agent):

    def __init__(
        self,
        jid,
        password,
        position,
        battery,
        autonomy,
        velocity,
        max_capacity,
        orders=None,
    ):

        super().__init__(jid, password)

        self.orders   = [] if orders is None else orders
        self.position = position  # initial position of the center
        self.battery  = (
            battery  # percentage calculated with the autonomy and distance traveled (?)
        )

        self.pending      = None
        self.autonomy     = autonomy  # on the csv
        self.velocity     = velocity  # on the csv
        self.max_capacity = max_capacity  # on the csv
        self.timer        = datetime.datetime.now()

        self.target    = None

    class UpdatePosition(CyclicBehaviour):
        async def on_start(self):
            print(f"Drone starts working")

        async def on_end(self):
            print(f"Drone finished working")
            await self.agent.stop()

        async def run(self):

            if self.agent.target:

                delta     = datetime.datetime.now() - self.agent.timer
                vector    = self.agent.target - self.agent.position
                offset    = delta * self.agent.velocity * vector.normalize()

                self.agent.position += offset

        
    def utility(self, order):
        #distance from the drone position to the center position (to pickup order)
        distance_1 = haversine_distance(self.position[0], self.position[1], order["d_lat"], order["d_long"])
        
        #distance from center to order target
        distance_2 = haversine_distance(order["d_lat"], order["d_long"], order["o_lat"], order["o_long"])
        
        #total distance traveled
        total_distance = distance_1 + distance_2
        
        #don't need to calculate capacity
        if (total_distance > self.autonomy):
            return 0
        
        utility_distance = self.autonomy - total_distance
        
        utility_capacity = self.max_capacity - order["weight"]
        
        utility_final_score = utility_distance + utility_capacity*2
        
        return utility_final_score        
        
        
    async def setup(self):

        s_machine = StateBehaviour()
        cyclic    = self.UpdatePosition()


        s_machine.add_state(name=LISTEN, state=Listen(), initial=True)
        s_machine.add_state(name=WAITING_BID, state=WaitingBid())
        s_machine.add_state(name=DELIVERING, state=Delivering())
        s_machine.add_state(name=RETURNING_CENTER, state=ReturningCenter())
        s_machine.add_state(name=NO_BATTERY, state=NoBattery())
        s_machine.add_transition(source=LISTEN, dest=LISTEN)
        s_machine.add_transition(source=DELIVERING, dest=RETURNING_CENTER)
        s_machine.add_transition(source=RETURNING_CENTER, dest=NO_BATTERY)

        self.add_behaviour(cyclic)
        self.add_behaviour(s_machine)


