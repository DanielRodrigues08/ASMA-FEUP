import tkinter as tk



def update_event():
    print("Event updated")

def update_drone(obj):
    print(obj)
    obj.value = True
    print("Drone updated")

def update_center(obj):
    obj.value = True
    print("Center updated")

def update_base():
    print("Base updated")


def change_drone(input1, input2):
    print("Drone changed")

def change_center(input1, input2):
    print("Center changed")
    print(input1.get())

def change_base(input1, input2):
    print("Base changed")
    print(input1.get())


methods = {

    'drone' : update_drone,
    'center': update_center,
    'base'  : update_base,
    'event' : update_event,
}

properties = {

    'drone' : change_drone,
    'center': change_center,
    'base'  : change_base,
}


def throw_event(event):

    if event["status"] == "on":
        event["status"] = "off"
    else:
        event["status"] = "on"
    print(event["status"])

def update_element(objects, key):

    if objects[key]["status"] == "on":
        objects[key]["status"] = "off"
    else:
        objects[key]["status"] = "on"
    print(objects[key]["status"])



def create_buttons(root, objects, row):

    buttons = []
    counter = 0
    for key in objects:
        button = tk.Button(root, text=key, command=lambda: throw_event(objects[key]))
        button.grid(row=row, column=counter)
        counter += 1
        buttons.append(button)

    return buttons


def create_dropdown(root, stands, objects, row, input = False):

    var      = tk.StringVar()
    dropdown = tk.OptionMenu(root, var, *objects)

    dropdown.grid(row=row, column=0)

    def callback(*args):

        if input:
            create_text_input(objects[var.get()], root, row + 1)
        button = tk.Button(root, text=var.get(), command=lambda: methods[objects[var.get()]["type"]](stands[objects[var.get()]["id"]]))
        button.grid(row=row +2, column=0)
        
    
    var.trace_add("write", callback)

    return dropdown



def create_text_input(object, root, row):

    input1 = tk.Entry(root)
    input1.grid(row=row, column=0)

    input2 = tk.Entry(root)
    input2.grid(row=row, column=1)
    submit = tk.Button(root, text="Submit", command=lambda: properties[object["type"]](input1, input2))
    submit.grid(row=row, column=3)

    return input1, input2, submit



def destroy_buttons(button):
    button.destroy()


def create_window(drones_stands, center_stands, ambient=None):


    drones = {}

    for i in range(len(drones_stands)):
        drones[f'Drone {i}'] = {"status": drones_stands[i], "id": i, "type": "drone"}

    centers = {}

    for i in range(len(center_stands)):
        centers[f'Center {i}'] = {"status": center_stands[i], "type": "center"}

    
    events = {
        'Raining': {
            "status": "off",
            "type": "event"
        },

        'Sunny': {
            "status": "on",
            "type": "event"
        },

        'Windy': {
            "status": "off",
            "type": "event"
        },
    }

    root = tk.Tk()
    root.title("Drone Control")
    root.geometry("500x500")

    create_dropdown(root, drones_stands, drones,  0)
    create_dropdown(root, center_stands, centers, 3, True)
    #create_dropdown(root, bases,   6)
    create_buttons(root, events,  9)

    root.mainloop()
