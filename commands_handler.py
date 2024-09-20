import datetime
from bson.objectid import ObjectId

from bson.objectid import ObjectId

def objectid_to_str(object_id):
    """Convert ObjectId to string."""
    if isinstance(object_id, ObjectId):
        return str(object_id)
    raise ValueError("Provided value is not an ObjectId.")


class CommandHandler:
    def __init__(self, db):
        self.db = db

    def issue_command(self, device_id, command):
        """Issue a command to a specific device."""
        self.db.commands.insert_one({
            "device_id": ObjectId(device_id),
            "command": command,
            "status": "pending",
            "issued_at": datetime.datetime.utcnow()
        })

    def issue_global_command(self, command):
        """Issue a global command to all devices."""
        devices = self.db.devices.find()
        for device in devices:
            self.issue_command(device["_id"], command)

    def get_pending_commands(self, device_id):
        """Retrieve pending commands for a specific device."""
        commands = self.db.commands.find({"device_id": ObjectId(device_id), "status": "pending"})
        return [command for command in commands]

    def store_command_result(self, device_id, command, result):
        """Store the result of a command execution by a device."""
        self.db.command_results.insert_one({
            "device_id": ObjectId(device_id),
            "command": command,
            "result": result,
            "reported_at": datetime.datetime.utcnow()
        })

        # Mark command as completed
        self.db.commands.update_one(
            {"device_id": ObjectId(device_id), "_id": ObjectId(command["_id"])},
            {"$set": {"status": "completed"}}
        )
