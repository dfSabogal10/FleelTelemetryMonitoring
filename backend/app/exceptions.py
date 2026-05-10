"""Lightweight domain errors with stable API codes."""


class DomainError(Exception):
    """Business/domain failure mapped to HTTP status and a stable error code."""

    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class VehicleNotFoundError(DomainError):
    def __init__(self, vehicle_id: str) -> None:
        self.vehicle_id = vehicle_id
        super().__init__(
            code="vehicle_not_found",
            message=f"Vehicle {vehicle_id} was not found",
            status_code=404,
        )
