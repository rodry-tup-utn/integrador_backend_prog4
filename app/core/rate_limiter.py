import threading
import time
from dataclasses import dataclass, field


@dataclass
class TokenBucket:
    """
    Implementación del algoritmo Token Bucket para UN cliente.
    """

    capacity: float
    refill_rate: float  # tokens por segundo
    tokens: float = field(init=False)
    last_refill: float = field(init=False)
    _lock: threading.Lock = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Inicializa el estado mutable DESPUÉS de __init__ (dataclass idiom)."""
        self.tokens = float(self.capacity)  # Arrancamos con el balde lleno.
        self.last_refill = time.perf_counter()
        self._lock = threading.Lock()

    def try_consume(self, tokens: float = 1.0) -> bool:
        """
        Intenta consumir tokens. Devuelve True si los había, False si no.

        Thread-safe: usa un lock para evitar race conditions cuando
        múltiples requests del mismo cliente llegan concurrentemente.
        """
        with self._lock:
            now = time.perf_counter()
            elapsed = now - self.last_refill
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.refill_rate,
            )
            self.last_refill = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def get_tokens(self) -> float:
        """
        Refills y devuelve la cantidad actual de tokens (sin consumir).
        Thread-safe.
        """
        with self._lock:
            now = time.perf_counter()
            elapsed = now - self.last_refill
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.refill_rate,
            )
            self.last_refill = now
            return self.tokens

    def reset(self) -> None:
        """
        Resetea el balde a su estado inicial (lleno).

        Útil para tests: cada test empieza con el bucket "como nuevo".
        """
        with self._lock:
            self.tokens = float(self.capacity)
            self.last_refill = time.perf_counter()


class RateLimiter:
    """
    Rate limiter que mantiene un TokenBucket por cliente.
    """

    def __init__(self, capacity: int, refill_rate_per_minute: int | float) -> None:
        """
        Args:
            capacity: tamaño del bucket (burst máximo). Ej: 10.
            refill_rate_per_minute: tokens agregados por minuto. Ej: 60.
                                    Se convierte a /segundo internamente.
        """
        self.capacity = float(capacity)

        self.refill_rate = refill_rate_per_minute / 60.0
        self._buckets: dict[str, TokenBucket] = {}
        self._buckets_lock = threading.Lock()

    def _get_bucket(self, key: str) -> TokenBucket:
        """
        Obtiene (o crea) el bucket para una key.
        """
        with self._buckets_lock:
            if key not in self._buckets:
                self._buckets[key] = TokenBucket(
                    capacity=self.capacity,
                    refill_rate=self.refill_rate,
                )
            return self._buckets[key]

    def is_allowed(self, key: str) -> bool:
        """
        Verifica si el cliente identificado por `key` puede hacer una request.
        """
        bucket = self._get_bucket(key)
        return bucket.try_consume(1.0)

    def get_remaining(self, key: str) -> int:
        """
        Devuelve cuántos tokens le quedan al cliente
        """
        bucket = self._get_bucket(key)
        return max(0, int(bucket.get_tokens()))

    def reset_all(self) -> None:
        """
        Resetea TODOS los buckets. Solo se usa en tests.
        """
        with self._buckets_lock:
            for bucket in self._buckets.values():
                bucket.reset()

    def reset_key(self, key: str) -> None:
        """
        Resetea el bucket de UNA key específica. Útil para tests dirigidos.
        """
        with self._buckets_lock:
            if key in self._buckets:
                self._buckets[key].reset()
