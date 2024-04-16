import datetime
import getpass
import json
import spade
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import random

class Ambient(Agent):

    def __init__(self, jid, password, drones = set()):
        super().__init__(jid, password)
        self.drones    = drones       
        self.trigger   = -1 
        self.incidents = ["Raining", "Windy", "Sunny"]

    class InformBehav(CyclicBehaviour):

        
        async def run(self):
            

            if self.agent.trigger >= 0:

                print(f"Ambient Warning Incoming at {datetime.datetime.now()} of type {self.agent.incidents[self.agent.trigger]}")

                for drone in self.agent.drones:

                    msg          = Message(to=str(drone))
                    msg.body     = json.dumps({'type': "AMBIENT", 'condition': self.agent.incidents[self.agent.trigger]})
                    msg.set_metadata("performative", "inform")
                    await self.send(msg)
                
                self.agent.trigger = -1
                    

        async def on_end(self):

            await self.agent.stop()

        async def on_start(self):
            self.counter = 0

    async def setup(self):

        print(f"Ambient started at {datetime.datetime.now()}")
        b = self.InformBehav()
        self.add_behaviour(b)