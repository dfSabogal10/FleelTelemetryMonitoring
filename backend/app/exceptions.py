class VehicleNotFoundError(LookupError):
    def __init__(self, vehicle_id: str) -> None:
        self.vehicle_id = vehicle_id
        super().__init__(f"Vehicle {vehicle_id!r} not found")
