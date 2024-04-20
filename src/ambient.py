import datetime
import getpass
import json
import spade
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import random


class Ambient(Agent):

    def __init__(self, jid, password, drones=set()):
        super().__init__(jid, password)
        self.drones = drones

        self.trigger = {}
        self.incidents = ["Raining", "Windy", "Sunny"]

    class InformBehav(CyclicBehaviour):

        async def run(self):

            prevent_key = None
            for key in self.agent.trigger:
                if self.agent.trigger[key] == True:
                    self.agent.trigger[key] = False
                    prevent_key = key
                    break

            if prevent_key:

                print(f"Ambient Warning Incoming at {datetime.datetime.now()} of type {prevent_key}")

                for drone in self.agent.drones:
                    msg = Message(to=str(drone))
                    msg.body = json.dumps({'type': "AMBIENT", 'condition': prevent_key})
                    msg.set_metadata("performative", "inform")
                    await self.send(msg)

        async def on_end(self):

            await self.agent.stop()

        async def on_start(self):
            self.counter = 0

    async def setup(self):

        print(f"Ambient started at {datetime.datetime.now()}")
        b = self.InformBehav()
        self.add_behaviour(b)
