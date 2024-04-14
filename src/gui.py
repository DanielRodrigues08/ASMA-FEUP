import tkinter as tk

def create_buttons(root, dict_objects, start_row, max_per_row):
    buttons = []
    current_row = start_row
    i = 0
    for key, value in dict_objects.items():
        status = value["status"] == "on"
        button = tk.Button(root, text=f'{key}', bg='green' if status else 'red', command=lambda k=key: create_submenu(root, k, dict_objects))
        button.grid(row=current_row, column=i % max_per_row, padx=5, pady=5)
        if (i + 1) % max_per_row == 0:
            current_row += 1
        buttons.append(button)
        i += 1
    return buttons

def create_submenu(root, key, objects):
    menu = tk.Menu(root, tearoff=0)
    for option in ["On", "Off", "View WebPage"]:
        menu.add_command(label=option, command=lambda o=option: submenu_action(root, key, o, objects))
    root.config(menu=menu)

def submenu_action(root, key, option, objects):
    button = None
    for widget in root.winfo_children():
        if widget['text'] == key:
            button = widget
            break
    if button:
        if option == "On":
            objects[key]["status"] = "on"
            button.config(bg="green")
        elif option == "Off":
            objects[key]["status"] = "off"
            button.config(bg="red")
        elif option == "View WebPage":
            print(objects[key]["webpage"])

def main(drones=None, centers=None):
    drones = {
        "Drone 1": {
            "status": "on",
            "class": None,
            "webpage": "localhost:5000",
        },
        "Drone 2": {
            "status": "on",
            "class": None,
            "webpage": "localhost:5000",
        },
        "Drone 3": {
            "status": "off",
            "class": None,
            "webpage": "localhost:5000",
        },
        "Drone 4": {
            "status": "on",
            "class": None,
            "webpage": "localhost:5000",
        },
        "Drone 5": {
            "status": "off",
            "class": None,
            "webpage": "localhost:5000",
        },
    }

    centers = {
        "Center 1": {
            "status": "on",
            "class": None,
            "webpage": "localhost:5000",
        },
        "Center 2": {
            "status": "off",
            "class": None,
            "webpage": "localhost:5000",
        },
        "Center 3": {
            "status": "on",
            "class": None,
            "webpage": "localhost:5000",
        },
        "Center 4": {
            "status": "on",
            "class": None,
            "webpage": "localhost:5000",
        }
    }

    root = tk.Tk()
    root.title("Drone Control")

    # Create drone buttons
    max_per_row = 7
    drone_buttons = create_buttons(root, drones, 0, max_per_row)

    # Add a space between drones and centers
    tk.Label(root, text="").grid(row=1)

    # Create center buttons
    center_buttons = create_buttons(root, centers, 2, max_per_row)

    root.mainloop()

if __name__ == "__main__":
    main()
