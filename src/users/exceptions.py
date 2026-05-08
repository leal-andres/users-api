from src.core.exceptions import AppException


class UserNotFound(AppException):
    status_code = 404
    title = "User not found"
    type_ = "https://api.example.com/errors/user-not-found"


class UserAlreadyExists(AppException):
    status_code = 409
    title = "User already exists"
    type_ = "https://api.example.com/errors/user-already-exists"
