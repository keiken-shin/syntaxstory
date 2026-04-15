import pytest
import asyncio
from app.pipeline.retry import async_retry

class TransientError(Exception):
    pass

class PermanentError(Exception):
    pass

@pytest.mark.anyio
async def test_async_retry_success_after_failures():
    attempts = []
    
    @async_retry(max_retries=3, base_delay=0.01, jitter=0.01, exceptions=(TransientError,))
    async def flawed_function():
        attempts.append(1)
        if len(attempts) < 3:
            raise TransientError("Service unavailable")
        return "success"
        
    result = await flawed_function()
    assert result == "success"
    assert len(attempts) == 3

@pytest.mark.anyio
async def test_async_retry_raises_after_max_retries():
    attempts = []
    
    @async_retry(max_retries=2, base_delay=0.01, jitter=0.01, exceptions=(TransientError,))
    async def always_fails():
        attempts.append(1)
        raise TransientError("Service permanently unavailable")
        
    with pytest.raises(TransientError):
        await always_fails()
        
    assert len(attempts) == 3  # Initial execution + 2 retries = 3

@pytest.mark.anyio
async def test_async_retry_ignores_unspecified_exceptions():
    attempts = []
    
    @async_retry(max_retries=3, base_delay=0.01, jitter=0.01, exceptions=(TransientError,))
    async def fails_badly():
        attempts.append(1)
        raise PermanentError("Critical failure")
        
    with pytest.raises(PermanentError):
        await fails_badly()
        
    assert len(attempts) == 1  # Should not retry for an unhandled exception type
