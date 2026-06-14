class AppError(Exception):
    status_code: int = 500
    code: str = "internal_error"

    def __init__(
        self,
        message: str = "Error interno de la aplicación",
        status_code: int | None = None,
        code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code


class ResourceNotFoundError(AppError):
    status_code = 404
    code = "not_found"

    def __init__(
        self,
        message: str | None = None,
        resource: str | None = None,
        identifier: str | int | None = None,
    ) -> None:
        if message is None and resource is not None:
            message = f"No se encontró {resource}"
            if identifier is not None:
                message += f" con identificador '{identifier}'"
            message += "."
        if message is None:
            message = "Recurso no encontrado"
        super().__init__(message=message)
        self.resource = resource
        self.identifier = str(identifier) if identifier is not None else None


class DuplicateResourceError(AppError):
    status_code = 409
    code = "duplicate_resource"

    def __init__(
        self,
        message: str | None = None,
        resource: str | None = None,
        field: str | None = None,
        value: str | int | None = None,
    ) -> None:
        if message is None and resource is not None:
            message = f"Ya existe un {resource}"
            if field is not None:
                message += f" con {field}='{value}'"
            message += "."
        if message is None:
            message = "El recurso ya existe"
        super().__init__(message=message)
        self.resource = resource
        self.field = field
        self.value = str(value) if value is not None else None


class BusinessRuleError(AppError):
    status_code = 400
    code = "business_rule_violation"

    def __init__(
        self, message: str = "La operación viola una regla de negocio"
    ) -> None:
        super().__init__(message=message)


class AuthenticationError(AppError):
    status_code = 401
    code = "authentication_error"
    headers: dict[str, str] | None = None

    def __init__(
        self, message: str = "No autenticado", headers: dict[str, str] | None = None
    ) -> None:
        super().__init__(message=message)
        self.headers = headers


class AuthorizationError(AppError):
    status_code = 403
    code = "authorization_error"

    def __init__(self, message: str = "Permisos insuficientes") -> None:
        super().__init__(message=message)


class RateLimitExceededError(AppError):
    status_code = 429
    code = "rate_limit_exceeded"

    def __init__(
        self,
        message: str = "Demasiadas peticiones. Intenta de nuevo más tarde.",
        retry_after: int = 60,
        limit: int | None = None,
        remaining: int | None = None,
    ) -> None:
        super().__init__(message=message)
        self.retry_after = retry_after
        self.limit = limit
        self.remaining = remaining
