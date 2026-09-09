"""Domain errors raised by services and mapped to HTTP in routers."""


class NotFoundError(Exception):
    """Referenced entity does not exist."""

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class DuplicateError(Exception):
    """Unique constraint would be violated."""

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)
