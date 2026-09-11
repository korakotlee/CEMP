"""In-memory PatchCache with TTL expiration, state tracking, and UUID generation."""

from __future__ import annotations

import time
import uuid
from enum import Enum

from pydantic import BaseModel, Field

from errors import (
    PatchAlreadyAppliedError,
    PatchExpiredError,
    PatchNotFoundError,
)


class PatchStatus(str, Enum):
    """Lifecycle states of a patch proposal."""

    PENDING = "pending"
    APPLIED = "applied"
    EXPIRED = "expired"


class PatchProposal(BaseModel):
    """Represents an in-memory staged patch proposal."""

    patch_id: str
    path: str
    base_hash: str
    new_content: str
    diff: str
    created_at: float = Field(default_factory=time.time)
    ttl_seconds: int = 900
    status: PatchStatus = PatchStatus.PENDING

    def is_expired(self) -> bool:
        """Check whether proposal age has exceeded TTL."""
        return (time.time() - self.created_at) > self.ttl_seconds


class PatchCache:
    """Thread-safe in-memory cache for staged patch proposals with TTL expiration."""

    def __init__(self, default_ttl_seconds: int = 900) -> None:
        self.default_ttl_seconds = default_ttl_seconds
        self._proposals: dict[str, PatchProposal] = {}

    def store(
        self,
        path: str,
        base_hash: str,
        new_content: str,
        diff: str,
        ttl_seconds: int | None = None,
    ) -> PatchProposal:
        """Stage a new patch proposal and generate a unique UUID patch_id.

        Args:
            path: Target file path within workspace.
            base_hash: SHA-256 hash of the target file at proposal time.
            new_content: Fully assembled replacement content.
            diff: Unified diff preview showing proposed modifications.
            ttl_seconds: Optional custom TTL in seconds (defaults to 900s / 15m).

        Returns:
            Staged PatchProposal instance.
        """
        patch_id = str(uuid.uuid4())
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        proposal = PatchProposal(
            patch_id=patch_id,
            path=path,
            base_hash=base_hash,
            new_content=new_content,
            diff=diff,
            ttl_seconds=ttl,
            status=PatchStatus.PENDING,
        )
        self._proposals[patch_id] = proposal
        return proposal

    def get(self, patch_id: str) -> PatchProposal:
        """Retrieve a staged patch proposal by patch_id.

        Args:
            patch_id: UUID identifier of the staged patch.

        Returns:
            PatchProposal if found and active.

        Raises:
            PatchNotFoundError: If patch_id is unknown.
            PatchExpiredError: If patch proposal has exceeded its TTL.
        """
        proposal = self._proposals.get(patch_id)
        if proposal is None:
            raise PatchNotFoundError(
                message=f"Patch proposal '{patch_id}' was not found in staging cache.",
                data={"patch_id": patch_id},
            )

        if proposal.is_expired():
            proposal.status = PatchStatus.EXPIRED
            raise PatchExpiredError(
                message=f"Patch proposal '{patch_id}' has expired (TTL {proposal.ttl_seconds}s).",
                data={"patch_id": patch_id, "ttl_seconds": proposal.ttl_seconds},
            )

        return proposal

    def mark_applied(self, patch_id: str) -> PatchProposal:
        """Mark a patch proposal as committed/applied.

        Args:
            patch_id: UUID identifier of the staged patch.

        Returns:
            Updated PatchProposal with status APPLIED.

        Raises:
            PatchNotFoundError: If patch_id is unknown.
            PatchExpiredError: If patch proposal has exceeded its TTL.
            PatchAlreadyAppliedError: If patch was previously applied.
        """
        proposal = self.get(patch_id)
        if proposal.status == PatchStatus.APPLIED:
            raise PatchAlreadyAppliedError(
                message=f"Patch proposal '{patch_id}' has already been committed.",
                data={"patch_id": patch_id},
            )

        proposal.status = PatchStatus.APPLIED
        return proposal

    def prune_expired(self) -> int:
        """Remove all expired patch proposals from cache.

        Returns:
            Count of expired proposals removed.
        """
        expired_ids = [pid for pid, prop in self._proposals.items() if prop.is_expired()]
        for pid in expired_ids:
            del self._proposals[pid]
        return len(expired_ids)

    def clear(self) -> None:
        """Clear all proposals from memory."""
        self._proposals.clear()

    def __contains__(self, patch_id: str) -> bool:
        """Check if patch_id exists in cache and is not expired."""
        if patch_id not in self._proposals:
            return False
        return not self._proposals[patch_id].is_expired()
