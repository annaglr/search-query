#!/usr/bin/env python3
"""BEALS API class."""
from __future__ import annotations

from abc import ABC, abstractmethod
import typing

import colrev

class BEALS_API(ABC):
    def __init__(
        self,
        *,
        params: dict,
        rerun: bool = False,
    ):
        self.params = params

        _, self.email = (
            colrev.env.environment_manager.EnvironmentManager.get_name_mail_from_git()
        )
        self.rerun = rerun
        
    @abstractmethod
    def build_url(self, query: str) -> str:
        """Build query url"""

    @abstractmethod
    def check_availability(self, raise_service_not_available: bool = True) -> None:
        """Check the availability of the API"""
        pass

    @abstractmethod
    def get_len_total(self) -> int:
        """Get the total number of records from Crossref based on the parameters"""
        pass

    @abstractmethod
    def get_records(self) -> typing.Iterator[colrev.record.record.Record]:
        """Get records from Crossref based on the parameters"""
        pass