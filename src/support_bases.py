from spade.agent import Agent
from spade.behaviour import FSMBehaviour, State, CyclicBehaviour
from spade.message import Message
from utils import haversine_distance, find_missing_orders, find_orders_with_ids
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
        self.agent.orders_rearrange = []
        msg = await self.receive(timeout=0)
        
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
        msg = await self.receive(timeout=1) #timeout de espera por 2 msg
        
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
        for drone in self.agent.drones_close:
            msg = Message(to=str(drone))
            msg.body = json.dumps({"type": "UPDATE_ORDERS", "position": self.agent.position})
            await self.send(msg)  
        
        msg_1 = await self.receive(timeout=120)
        msg_2 = await self.receive(timeout=120)
        
        if msg_1 is None or msg_2 is None:
            self.set_next_state(WAITING_1_MSG)
            return
        
        payload_1 = json.loads(msg_1.body)
        payload_2 = json.loads(msg_2.body)

        if payload_1["type"] == "ARRIVED" and payload_2["type"] == "ARRIVED":

            self.agent.orders_rearrange = payload_1["orders"] + payload_2["orders"]
            self.set_next_state(REARRANGEMENT)
            return 
        else:
            self.set_next_state(WAITING_MEETING)
            return
        
class Rearrangement(State):

    async def assing_orders(self, payload_1, payload_2, msg1, msg2):
        
        print("PREF1", payload_1["reordered"])
        print("PREF2", payload_2["reordered"]) 
        print(payload_1["reordered"][0][1]) 

        if (payload_1["reordered"][0][1] >= payload_2["reordered"][0][1]):
            best_option   = payload_1["reordered"][0]
            best_drone    = msg1.sender
            worst_drone   = msg2.sender
            second_option = payload_2["reordered"]
        else:
            best_option   = payload_2["reordered"][0]
            best_drone    = msg2.sender
            worst_drone   = msg1.sender
            second_option = payload_1["reordered"]

        second_arrange_orders = find_missing_orders(best_option, self.agent.orders_rearrange)   
        second_arrange_ids    = []

        for element in second_arrange_orders:
            second_arrange_ids.append(element["id"])

        second_arrange        = find_orders_with_ids(second_option, second_arrange_ids)
        second_arrange        = sorted(second_arrange, key=lambda x: x[1], reverse=True)
        second_arrange_option = second_arrange[0]
        
        msg = Message(to=str(best_drone))
        msg.body = json.dumps({"type": "REARRANGE_DONE", "new_orders": best_option[0]})
        await self.send(msg)
        
        msg = Message(to=str(worst_drone))
        msg.body = json.dumps({"type": "REARRANGE_DONE", "new_orders": second_arrange_option[0]})
        await self.send(msg)
        
    async def run(self):

        for drone in self.agent.drones_close:
            msg = Message(to=str(drone))
            msg.body = json.dumps({"type": "REARRANGE_ORDERS", "orders": self.agent.orders_rearrange})
            await self.send(msg)
            
        msg1      = await self.receive(timeout=100)
        msg2      = await self.receive(timeout=100)
        
        payload_1 = json.loads(msg1.body)
        payload_2 = json.loads(msg2.body)
        
        if payload_1["type"] == "REARRANGE_PROPOSAL" and payload_2["type"] == "REARRANGE_PROPOSAL":
            await self.assing_orders(payload_1, payload_2, msg1, msg2)
            self.set_next_state(WAITING_1_MSG)
            return 
        
        else:
            self.set_next_state(REARRANGEMENT)
            return
        
        
class SupportBase(Agent):
    
    def __init__(self, jid, password, position):
        super().__init__(jid, password)
        self.position = position
        self.drones_close = []   
        self.orders_rearrange = []     
    
    async def setup(self):

        s_machine = StateBehaviour()

    
        s_machine.add_state(name=WAITING_1_MSG, state=Waiting_1_msg(), initial=True)
        s_machine.add_state(name=WAITING_2_MSG, state=Waiting_2_msg())
        s_machine.add_state(name=WAITING_MEETING, state=Waiting_Meeting())
        s_machine.add_state(name=REARRANGEMENT, state=Rearrangement())

        s_machine.add_transition(source=WAITING_1_MSG, dest=WAITING_2_MSG)
        s_machine.add_transition(source=WAITING_1_MSG, dest=WAITING_1_MSG)
        s_machine.add_transition(source=WAITING_2_MSG, dest=WAITING_1_MSG)
        s_machine.add_transition(source=WAITING_2_MSG, dest=WAITING_MEETING)
        s_machine.add_transition(source=WAITING_MEETING, dest=WAITING_1_MSG)
        s_machine.add_transition(source=WAITING_MEETING, dest=WAITING_MEETING)
        s_machine.add_transition(source=WAITING_MEETING, dest=REARRANGEMENT)
        s_machine.add_transition(source=REARRANGEMENT, dest=WAITING_1_MSG)
        s_machine.add_transition(source=REARRANGEMENT, dest=REARRANGEMENT)

        self.add_behaviour(s_machine)    