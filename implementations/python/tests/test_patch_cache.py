"""Unit tests for in-memory PatchCache with TTL expiration and lifecycle states."""

from __future__ import annotations

import time
import uuid

import pytest

from core.patch_cache import PatchCache, PatchProposal, PatchStatus
from errors import PatchAlreadyAppliedError, PatchExpiredError, PatchNotFoundError


def test_patch_cache_store_and_get():
    """Verify storing a patch generates a valid UUID patch_id and retrieves the proposal."""
    cache = PatchCache(default_ttl_seconds=900)
    proposal = cache.store(
        path="src/main.py",
        base_hash="a" * 64,
        new_content="print('hello')",
        diff="--- a/src/main.py\n+++ b/src/main.py\n@@ -1 +1 @@\n-old\n+new\n",
    )

    assert isinstance(proposal, PatchProposal)
    assert uuid.UUID(proposal.patch_id)
    assert proposal.path == "src/main.py"
    assert proposal.base_hash == "a" * 64
    assert proposal.new_content == "print('hello')"
    assert proposal.status == PatchStatus.PENDING

    retrieved = cache.get(proposal.patch_id)
    assert retrieved.patch_id == proposal.patch_id
    assert retrieved.status == PatchStatus.PENDING


def test_patch_cache_not_found():
    """Verify looking up an unknown patch_id raises PatchNotFoundError."""
    cache = PatchCache()
    non_existent = str(uuid.uuid4())

    with pytest.raises(PatchNotFoundError) as exc_info:
        cache.get(non_existent)
    assert exc_info.value.code == -32020


def test_patch_cache_expiration():
    """Verify proposals older than TTL expire and raise PatchExpiredError."""
    cache = PatchCache(default_ttl_seconds=1)
    proposal = cache.store(
        path="test.py",
        base_hash="b" * 64,
        new_content="updated",
        diff="unified diff",
        ttl_seconds=1,
    )

    # Force expiration by adjusting created_at timestamp back in time
    proposal.created_at = time.time() - 2

    with pytest.raises(PatchExpiredError) as exc_info:
        cache.get(proposal.patch_id)
    assert exc_info.value.code == -32021
    assert exc_info.value.recoverable is True


def test_patch_cache_mark_applied():
    """Verify transitioning status to applied and rejecting duplicate application."""
    cache = PatchCache()
    proposal = cache.store(
        path="app.py",
        base_hash="c" * 64,
        new_content="def run(): pass",
        diff="diff snippet",
    )

    applied = cache.mark_applied(proposal.patch_id)
    assert applied.status == PatchStatus.APPLIED

    # Duplicate mark_applied must raise PatchAlreadyAppliedError
    with pytest.raises(PatchAlreadyAppliedError) as exc_info:
        cache.mark_applied(proposal.patch_id)
    assert exc_info.value.code == -32022
    assert exc_info.value.recoverable is False


def test_patch_cache_prune_expired():
    """Verify pruning expired proposals clears memory correctly."""
    cache = PatchCache(default_ttl_seconds=10)
    p1 = cache.store("f1.py", "1" * 64, "content1", "diff1")
    p2 = cache.store("f2.py", "2" * 64, "content2", "diff2")

    # Expire p1
    p1.created_at = time.time() - 20

    pruned = cache.prune_expired()
    assert pruned == 1
    assert p2.patch_id in cache
    assert p1.patch_id not in cache
