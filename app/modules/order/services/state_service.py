from app.modules.order.unit_of_work import OrderUnitOfWork
from app.core.exceptions import BusinessRuleError


class OrderStateService:
    PENDING = "PENDING"
    CANCELLED = "CANCELLED"
    IN_PREP = "IN_PREP"
    CONFIRMED = "CONFIRMED"
    DELIVERED = "DELIVERED"

    TERMINAL_CLIENT = {CANCELLED, DELIVERED, IN_PREP}
    TERMINAL_STAFF = {CANCELLED, DELIVERED}

    def check_state_order(self, uow: OrderUnitOfWork, state_code: str):
        state = uow.states.get_by_code(state_code)
        if not state:
            raise BusinessRuleError(
                f"Estado {state_code} no configurado",
            )
        return state

    def check_update_state(self, old_state: str, terminal_states: set[str]):
        if old_state in terminal_states:
            raise BusinessRuleError(
                "La orden se encuentra en un estado no modificable",
            )
