from core.prompt_cache import PromptCache


def test_prompt_cache_rebuilds_only_after_invalidation():
    calls = []
    cache = PromptCache(lambda: calls.append(1) or f"prompt-{len(calls)}")
    assert cache.get() == "prompt-1"
    assert cache.get() == "prompt-1"
    assert calls == [1]
    cache.invalidate()
    assert cache.get() == "prompt-2"
