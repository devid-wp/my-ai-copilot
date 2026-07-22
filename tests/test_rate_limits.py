from core.rate_limits import RateLimitMonitor


def test_limit_check_refreshes_once_per_minute():
    monitor = RateLimitMonitor(refresh_seconds=60)
    monitor.record_error("nvidia", RuntimeError("ResourceExhausted: limit 16/16"), now=100)
    assert monitor.can_check("nvidia", now=159) is False
    assert monitor.seconds_until_refresh("nvidia", now=159) == 1
    assert "limit reached" in monitor.describe("nvidia", now=159)
    assert monitor.can_check("nvidia", now=160) is True


def test_successful_check_is_also_cached_for_one_minute():
    monitor = RateLimitMonitor(refresh_seconds=60)
    monitor.record_success("gemini", now=10)
    assert monitor.can_check("gemini", now=20) is False
    assert monitor.can_check("gemini", now=70) is True


def test_failed_key_check_is_not_reported_as_available_and_can_be_cleared():
    monitor = RateLimitMonitor(refresh_seconds=60)
    monitor.record_error("gemini", RuntimeError("invalid API key"), now=10)
    assert "failed" in monitor.describe("gemini", now=20)

    monitor.clear("gemini")
    assert monitor.describe("gemini", now=20) == "not checked"
