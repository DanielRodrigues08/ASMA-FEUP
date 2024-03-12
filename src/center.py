import spade
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message


class Center(Agent):
    def __init__(self, jid, password, orders, position):
        super().__init__(jid, password)
        self.orders = orders #for now, without supplier
        self.position = position 
        
    class AssignOrdersBehav(CyclicBehaviour):
        async def on_start(self):
            print(f"Center starts working")
            
        async def on_end(self):
            print(f"Center finished working")
            await self.agent.stop() 
            
        async def run(self):
            msg = await self.receive(timeout=100)
            if msg.body == "Ready to deliver":
                msg_ready = Message(to=str(msg.sender)) #msg to the drone (drone jid)
                msg_ready.body = "OK"
                await self.send(msg_ready)
                msg2 = await self.receive(timeout=10)
                if msg2.body == "Orders for me":
                    msg_conf = Message(to=str(msg2.sender)) #msg to the drone (drone jid)
                    msg_conf.body = "order1_1 order1_2 order1_3" #we have to make the logic for the center to assign orders to the drones according to capacity, location..
                    await self.send(msg_conf)
                    #await self.receive(timeout=10) 
                    #do something when receive confirmation from the drone that he received the orders ?
    
    async def setup(self):
        print(f"Center starting at {self.position}")
        self.add_behaviour(self.AssignOrdersBehav())                
                    
              