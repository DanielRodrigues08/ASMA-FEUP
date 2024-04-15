from spade.agent import Agent
from spade.behaviour import FSMBehaviour, State, CyclicBehaviour
from spade.message import Message
from utils import haversine_distance, rearrange_orders_base
import json

WAITING_1_MSG = "WAITING_1_MSG"
WAITING_2_MSG = "WAITING_2_MSG"
WAITING_MEETING = "WAITING_MEETING"
REARRANGEMENT = "REARRANGEMENT"
        
class StateBehaviour(FSMBehaviour):
    async def on_start(self):
        print(f"FSM starting at initial state {self.current_state}")

    async def on_end(self):
        print(f"FSM finished at state {self.current_state}")
        await self.agent.stop()
        
class Waiting_1_msg(State):
    async def run(self):
        self.agent.drones_close = []
        msg = await self.receive(timeout=5)
        
        if msg is None:
            self.set_next_state(WAITING_1_MSG)
            return
        
        payload = json.loads(msg.body)
        
        match payload["type"]:
            case "PRESENCE":
                print(f"Base received 1 message")
                self.agent.drones_close.append(msg.sender)
                self.set_next_state(WAITING_2_MSG)
                return 
        
        self.set_next_state(WAITING_1_MSG)
        return    
    
class Waiting_2_msg(State):
    async def run(self):
        msg = await self.receive(timeout=5) #timeout de espera por 2 msg
        
        if msg is None:
            self.set_next_state(WAITING_1_MSG)
            return
        
        payload = json.loads(msg.body)
        
        match payload["type"]:
            case "PRESENCE":
                if msg.sender not in self.agent.drones_close:
                    print(f"Base received 2 message")
                    self.agent.drones_close.append(msg.sender)
                    self.set_next_state(WAITING_MEETING) 
                else:
                    self.set_next_state(WAITING_1_MSG)    
                return 
        
        self.set_next_state(WAITING_1_MSG)
        return
    
class Waiting_Meeting(State):
    async def run(self):   
        print(self.agent.drones_close)
        for drone in self.agent.drones_close:
            msg = Message(to=str(drone))
            msg.body = json.dumps({"type": "UPDATE_ORDERS", "position": self.agent.position})
            await self.send(msg)        
        
        msg_1 = await self.receive(timeout=100)
        msg_2 = await self.receive(timeout=100)
        
        if msg_1 is None or msg_2 is None:
            self.set_next_state(WAITING_1_MSG)
            return
        
        payload_1 = json.loads(msg_1.body)
        payload_2 = json.loads(msg_2.body)
        
        print("PAY1",payload_1)
        print("PAY2",payload_2)
              
        if payload_1["type"] == "ARRIVED" and payload_2["type"] == "ARRIVED":
            print("INCRIVEL")
            self.set_next_state(REARRANGEMENT)
            return 
        else:
            self.set_next_state(WAITING_MEETING)
            return
        
#class Rearrangement(State):
 #   async def run(self):
  #      utility_drone_1, utility_drone_2 = rearrange_orders_base(self.drones_close[0], self.drones_close[0].orders[1:], self.drones_close[1], self.drones_close[1].orders[1:])      
        
        #sacar 1 order de ambos, e garantir q todas as orders tao la           
        
        
        
class SupportBase(Agent):
    
    def __init__(self, jid, password, position):
        super().__init__(jid, password)
        self.position = position
        self.drones_close = []        
    
    async def setup(self):

        s_machine = StateBehaviour()

    
        s_machine.add_state(name=WAITING_1_MSG, state=Waiting_1_msg(), initial=True)
        s_machine.add_state(name=WAITING_2_MSG, state=Waiting_2_msg())
        s_machine.add_state(name=WAITING_MEETING, state=Waiting_Meeting())
        #s_machine.add_state(name=NO_BATTERY, state=NoBattery())

        s_machine.add_transition(source=WAITING_1_MSG, dest=WAITING_2_MSG)
        s_machine.add_transition(source=WAITING_1_MSG, dest=WAITING_1_MSG)
        s_machine.add_transition(source=WAITING_2_MSG, dest=WAITING_1_MSG)
        s_machine.add_transition(source=WAITING_2_MSG, dest=WAITING_MEETING)
        s_machine.add_transition(source=WAITING_MEETING, dest=WAITING_1_MSG)
        s_machine.add_transition(source=WAITING_MEETING, dest=WAITING_MEETING)

        self.add_behaviour(s_machine)    