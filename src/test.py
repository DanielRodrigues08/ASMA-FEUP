import json


a = json.dumps({"type": "ORDERS_READY", "orders": 2})

b = json.loads(a)
print(b)