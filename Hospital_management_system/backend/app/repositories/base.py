"""
app/repositories/base.py
========================
Abstract repository interface.

WHY an abstract interface?
  The dashboard now reads SQL Server through app/repositories/sql_repo.py
  (function-based queries over the app.db.database.Database handle).  This
  interface is kept for any future entity-style repositories.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseRepository(ABC):
    """
    Minimal interface that every repository must satisfy.
    Concrete CSV (and future SQL) repositories inherit from this.
    """

    @abstractmethod
    def get_all(self, filters: dict[str, Any] | None = None) -> list[dict]:
        """
        Return all records, optionally filtered.

        Parameters
        ----------
        filters : Optional dict of column → value pairs (all ANDed together).
                  None means "return everything".

        Returns
        -------
        List of row dicts, each keyed by the CSV column name.
        """

    @abstractmethod
    def get_by_id(self, record_id: str) -> dict | None:
        """
        Return a single record by its primary key, or None if not found.
        """
