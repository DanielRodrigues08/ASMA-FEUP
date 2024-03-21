import datetime
import json
from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour
from spade.message import Message
import random

MAX_BATCH_SIZE = 10


class Center(Agent):

    def __init__(self, jid, password, position, orders, coord_jid):
        super().__init__(jid, password)
        self.position = position
        self.orders = orders
        self.coord_jid = coord_jid

    class SendBehav(PeriodicBehaviour):

        async def run(self):

            if len(self.agent.orders) == 0:
                print("No orders to send")
                self.agent.stop()
            
            msg = Message(to=str(self.agent.coord_jid))

            i = int(random.randint(1, min(len(self.agent.orders), MAX_BATCH_SIZE)))
            orders = [{"id": (o[0]), "d_lat": float(o[1]), "d_long": float(o[2]), "o_lat": float(self.agent.position[0]), "o_long": float(self.agent.position[1]), "weight": float(o[3])} for o in self.agent.orders[-i:]]            
            msg.body = json.dumps({"orders": orders})
            msg.set_metadata("performative", "inform")
            self.agent.orders = self.agent.orders[:-i]

            await self.send(msg)

        async def on_end(self):
            await self.agent.stop()

        async def on_start(self):
            self.counter = 0

    async def setup(self):
        print(f"Center starting at {self.position}")

        start_date = datetime.datetime.now()

        b = self.SendBehav(period=10, start_at=start_date)
        self.add_behaviour(b)
