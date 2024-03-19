import time
import json
from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour
from spade.message import Message
import random

MAX_BATCH_SIZE = 10


class Center(Agent):

    def __init__(self, jid, password, orders, coordinator):
        super().__init__(jid, password)
        self.orders = orders
        self.coordinator = coordinator

    class InformBehav(PeriodicBehaviour):

        async def run(self):

            if len(self.agent.orders) == 0:
                print("No orders to send")
                self.agent.stop()

            msg = Message(to=self.agent.coordinator)

            i = random.randint(1, min(len(self.agent.orders), MAX_BATCH_SIZE))
            orders = self.agent.orders[-i:]
            self.agent.orders = self.agent.orders[:-i]

            msg.body = json.dumps(orders)
            msg.set_metadata("performative", "inform")
            await self.send(msg)

        async def on_end(self):
            await self.agent.stop()

        async def on_start(self):
            self.counter = 0

    async def setup(self):
        print(f"Supplier started at {time.time()}")
        b = self.InformBehav(period=10, start_at=time.time() + 5)
        self.add_behaviour(b)
