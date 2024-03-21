import spade
import json
from spade.agent import Agent
from spade.behaviour import FSMBehaviour, State, CyclicBehaviour
from spade.message import Message
from utils import msg_orders_to_list
import datetime

BEGIN            = "BEGIN"
DELIVERING       = "DELIVERING"
RETURNING_CENTER = "RETURNING_CENTER"
NO_BATTERY       = "NO_BATTERY"


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

        msg = await self.receive(timeout=0)
        
        if msg is None:
            self.set_next_state(BEGIN)
            return
        
        payload = json.loads(msg.body)

        match payload["type"]:

            case "ORDERS_READY":

                print(f"Drone received orders from coordinator")
                ans      = Message(to=str(msg.sender))
                ans.body = json.dumps({"type": "BID", "payload": self.agent.calculate_orders_utility(payload["orders"])})
                ans.set_metadata("performative", "propose")

                await self.send(ans)

            case "RECEIVE_ORDER": self.set_next_state(RETURNING_CENTER)
            case "INCIDENT"     : self.set_next_state(BEGIN)
        return

class Delivering(State):

    async def run(self):
        print(f"Drone delivering orders")
        while len(self.agent.orders) > 0:
            # implement logic for delivering
            # drone going to the points of the orders, and when reaching, the order is deleted from the attribute, until the attribute has 0 orders
            self.agent.orders.pop(0)
            self.set_next_state(BEGIN)


class ReturningCenter(State):
    async def run(self):
        print(f"Drone returning to the center")
        # implement logic for returning to the center (point of the last order -> point of the center)
        # after going to center replenish battery
        self.agent.battery = self.agent.autonomy
        self.set_next_state(BEGIN)


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
        coord_jid,
        orders=None,
    ):

        super().__init__(jid, password)

        self.orders   = [] if orders is None else orders
        self.position = position  # initial position of the center
        self.battery  = (
            battery  # percentage calculated with the autonomy and distance traveled (?)
        )
        self.autonomy     = autonomy  # on the csv
        self.velocity     = velocity  # on the csv
        self.max_capacity = max_capacity  # on the csv
        self.timer        = datetime.datetime.now()

        self.target    = None
        self.coord_jid = coord_jid

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


    def calculate_orders_utility(self, orders):
        return []
        
    def utility(self, position):
        return 0
    
    
    async def setup(self):

        s_machine = StateBehaviour()
        cyclic    = self.UpdatePosition()


        s_machine.add_state(name=BEGIN, state=Begin(), initial=True)
        s_machine.add_state(name=DELIVERING, state=Delivering())
        s_machine.add_state(name=RETURNING_CENTER, state=ReturningCenter())
        s_machine.add_state(name=NO_BATTERY, state=NoBattery())
        s_machine.add_transition(source=BEGIN, dest=BEGIN)
        s_machine.add_transition(source=DELIVERING, dest=RETURNING_CENTER)
        s_machine.add_transition(source=RETURNING_CENTER, dest=NO_BATTERY)

        self.add_behaviour(cyclic)
        self.add_behaviour(s_machine)


