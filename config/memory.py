# Конфигурация для MemoryActor
MEMORY_CONFIG = {
    "stm_limit": 25,                    # Кольцевой буфер лимит
    "cleanup_batch_size": 10,           # Размер batch для cleanup
    "query_timeout_seconds": 30,        # Timeout для DB запросов
    "retry_attempts": 3,                # Попытки retry при ошибках
    "retry_delay_seconds": 1,           # Задержка между retry
    "context_max_length": 5000,         # Максимальная длина контекста
    "importance_threshold": 5,          # Порог важности для LTM готовности
    "performance_log_enabled": True     # Логирование производительности
}