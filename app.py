from flask import Flask, request, jsonify, abort
from pymongo import MongoClient
from bson.objectid import ObjectId
from commands_handler import CommandHandler
import datetime
from flask_cors import CORS

from bson.objectid import ObjectId


def stringify_object_ids(data):
    """
    Recursively converts all ObjectId instances in the given data structure to strings.

    :param data: The data structure (dict or list) containing ObjectId instances.
    :return: A new data structure with ObjectId instances converted to strings.
    """
    if isinstance(data, dict):
        return {k: stringify_object_ids(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [stringify_object_ids(item) for item in data]
    elif isinstance(data, ObjectId):
        return str(data)
    elif isinstance(data, str):
        return data
    else:
        print(data)
        return data

app = Flask(__name__)
CORS(app, origins="*")

# Connect to MongoDB (modify URI to your setup)
client = MongoClient("mongodb://95.216.148.93:27017")
db = client.device_management

# Initialize command handler
command_handler = CommandHandler(db)
@app.route('/register', methods=['POST'])
def register_device():
    data = request.json
    location = data.get('location', None)
    if location is None:
        name = data.get('name', None)
        if name is None:
            abort(400)
    device_type = data.get('device_type')

    if not location or not device_type:
        return jsonify({"error": "Location and device_type are required"}), 400

    # Count devices in the specified location
    device_count = db.devices.count_documents({"location": location})
    
    # Generate the new device name
    name = f"{location}-{device_count + 1}"

    device = {
        "name": name,
        "device_type": device_type,
        "location": location,
        "registered_at": datetime.datetime.utcnow(),
        "status": "active",
        "last_report": None
    }
    device_id = db.devices.insert_one(device).inserted_id

    return jsonify({"device_id": str(device_id), "device_name": name})


@app.route('/report_status', methods=['POST'])
def report_status():
    data = request.json
    device_id = data.get('device_id')
    cpu_usage = data.get('cpu_usage')
    ram_usage = data.get('ram_usage')
    memory_usage = data.get('memory_usage')
    status = data.get('status')

    if not device_id or not status:
        return jsonify({"error": "device_id and status are required"}), 400

    try:
        # Update device information
        db.devices.update_one(
            {"_id": ObjectId(device_id)},
            {"$set": {
                "cpu_usage": cpu_usage,
                "ram_usage": ram_usage,
                "memory_usage": memory_usage,
                "status": status,
                "last_report": datetime.datetime.utcnow()
            }}
        )

        # Insert status report
        db.statuses.insert_one({
            "device_id": ObjectId(device_id),
            "timestamp": datetime.datetime.utcnow(),  # Use UTC datetime directly
            "cpu_usage": cpu_usage,
            "ram_usage": ram_usage,
            "memory_usage": memory_usage,
            "status": status,
            "ip_address": request.remote_addr
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500  # Return 500 for server errors

    # Check for pending commands
    commands = command_handler.get_pending_commands(device_id)

    return jsonify({"commands": stringify_object_ids(commands)}), 200  # Return 200 for successful requests



@app.route('/disableLogging', methods=['POST'])
def disable_logging():
    data = request.json
    device_id = data.get('device_id')

    if not device_id:
        return jsonify({"error": "device_id is required"}), 400

    command_handler.add_command(device_id, {"action": "disable_logging"})
    return jsonify({"message": "Logging disabled command sent."}), 200

@app.route('/issue_command', methods=['POST'])
def issue_command():
    data = request.json
    device_id = data.get('device_id')
    command = data.get('command')

    if not device_id or not command:
        return jsonify({"error": "device_id and command are required"}), 400

    command_handler.issue_command(device_id, command)

    return jsonify({"message": "Command issued successfully"})

@app.route('/issue_global_command', methods=['POST'])
def issue_global_command():
    data = request.json
    command = data.get('command')

    if not command:
        return jsonify({"error": "command is required"}), 400

    command_handler.issue_global_command(command)

    return jsonify({"message": "Global command issued successfully"})

@app.route('/command_result', methods=['POST'])
def command_result():
    data = request.json
    device_id = data.get('device_id')
    command = data.get('command')
    result = data.get('result')

    if not device_id or not command or not result:
        return jsonify({"error": "device_id, command, and result are required"}), 400

    command_handler.store_command_result(device_id, command, result)

    return jsonify({"message": "Command result received successfully"})

@app.route('/query/<device_id>', methods=['GET'])
def query_device(device_id):
    device = db.devices.find_one({"_id": ObjectId(device_id)})
    if not device:
        return jsonify({"error": "Device not found"}), 404

    commands = command_handler.get_pending_commands(device_id)

    return jsonify({
        "status": {
            "cpu_usage": device.get('cpu_usage'),
            "ram_usage": device.get('ram_usage'),
            "memory_usage": device.get('memory_usage'),
            "status": device.get('status')
        },
        "commands": commands
    })

@app.route('/query', methods=['GET'])
def query_devices():
    devices = list(db.devices.find())
    
    # Convert ObjectId to string
    for device in devices:
        device["_id"] = str(device["_id"])
    
    return jsonify({"devices": devices})



if __name__ == '__main__':
    app.run(debug=True)
