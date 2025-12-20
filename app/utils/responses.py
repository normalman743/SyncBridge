def success(data=None, message: str = "OK"):
    return {"status": "success", "message": message, "data": data or {}}


def error(message: str = "Error", code: str = "INTERNAL_ERROR"):
    return {"status": "error", "message": message, "code": code}
