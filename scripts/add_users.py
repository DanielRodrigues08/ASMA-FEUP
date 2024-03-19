import csv
import subprocess

def create_prosody_user(username, password):
    # Execute prosodyctl command to add user
    try:
        subprocess.run(['sudo', 'prosodyctl', 'register', username, 'localhost', password], check=True)
        print(f"User '{username}' created successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error creating user '{username}': {e}")

def main(csv_file):
    # Read CSV file and create users
    with open(csv_file, newline='') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            username = row['id']
            password = row['id']  # Using id as password
            create_prosody_user(username, password)

if __name__ == "__main__":
    csv_file = '../data/drones/delivery_drones.csv'  # Change this to your CSV file name
    main(csv_file)
