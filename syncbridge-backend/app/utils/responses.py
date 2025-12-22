ERROR_CODES: tuple[str, ...] = (
    "UNAUTHORIZED",
    "FORBIDDEN",
    "NOT_FOUND",
    "VALIDATION_ERROR",
    "CONFLICT",
    "INTERNAL_ERROR",
)


def success(data=None, message: str = "OK"):
    return {"status": "success", "message": message, "data": data or {}}


def error(message: str = "Error", code: str = "INTERNAL_ERROR"):
    if code not in ERROR_CODES:
        raise ValueError(f"Unsupported error code: {code}")
    return {"status": "error", "message": message, "code": code}
