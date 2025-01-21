#!/usr/bin/env python3
"""BEALS prototype for Crossref"""
from __future__ import annotations

import datetime
import logging
import typing
import re

from colrev.packages.crossref.src import crossref_api
from colrev.record.record import Record

from search_query import AndQuery
from search_query import OrQuery
from search_query.query import Query
from search_query.query import SearchField


# pylint: disable=too-many-instance-attributes
class BEALSCrossref:
    """
    BEALS prototype for Crossref
    """

    _api_url = "https://api.crossref.org/"

    def __init__(self, query: Query) -> None:
        self.value: str = query.value
        self.operator: bool = query.operator
        self.search_field: typing.Optional[SearchField] = query.search_field
        self.children: typing.List[BEALSCrossref] = [
            BEALSCrossref(child) for child in query.children
        ]
        self.records: typing.List[Record] = []

        self.api = crossref_api.CrossrefAPI(params={})

        self.logger = logging.getLogger(__name__)

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )

        self.path_length = -1

    def retrieve(self) -> typing.List[Record]:
        """Retrieve results from the API."""

        # build query url
        url = self.build_url(self.value)
        self.api.params = {"url": url}

        num_res = self.api.get_len_total()

        # check the availability of the API
        self.api.check_availability()

        # retrieve records
        self.logger.info("Retrieve %d records", num_res)
        estimated_time = num_res * 0.007 + 5
        estimated_time_formatted = str(datetime.timedelta(seconds=int(estimated_time)))
        self.logger.info("Estimated time: %s", estimated_time_formatted)
        prep_records = list(self.api.get_records())
        records = self._search_records(term=self.value, record_list=prep_records)
        self.logger.info("Finished and retrieved %d records.", len(records))

        return records

    def build_url(self, query: str) -> str:
        """Build query url."""

        query = query.replace(" ", "+")
        url = self._api_url + "works?" + "query.title=%22" + query + "%22"

        # Add time range filter
        # filter_date = "filter=from-pub-date:2015-01-01"
        # url = self._api_url + "works?" + "query.title=%22" + query + "%22" + "&" + filter_date

        # Add journal filter
        # filter = "filter=issn:0167-9236,issn:0960-085X"
        # url = self._api_url + "works?" + filter + "&" + "query.title=%22" + query + "%22"

        return url

    def _combine_results_from_children(self) -> None:
        """Combine the records from the children (OR operator)."""

        child_records = {}
        for child in self.children:
            for record in child.records:
                # DOI is used as identifier for the records
                child_records[record.data.get("doi")] = record

        self.records = list(child_records.values())

    def run_beals(self) -> typing.List[Record]:
        """Start BEALS."""

        # base case: call self.retrieve if the query is a simple term
        if not self.operator:
            # assign the results to self.records
            self.records = self.retrieve()
            self._remove_duplicates()

        else:
            # recursive cases
            # call APIXY(x).run_beals() for x in children and combine the results
            if self.value == "AND":
                next_child = self.calculate_path()
                self.records = next_child.run_beals()

                for c in self.children:
                    if c != next_child:
                        self.records = c.filter_records(self.records)

            elif self.value == "OR":
                for child in self.children:
                    child.run_beals()
                self._combine_results_from_children()
            else:
                # NotQuery is not implemented
                raise ValueError("Operator is not yet supported.")

        self._remove_duplicates()
        return self.records

    # pylint: disable=inconsistent-return-statements
    def calculate_path(self) -> BEALSCrossref:
        """Calculate shortest path for record retrieval."""

        if not self.operator:
            self.api.params = {"url": self.build_url(self.value)}
            self.path_length = self.api.get_len_total()
            return self

        if self.operator:
            if len(self.children) == 0:
                raise ValueError("AndQuery must have at least one child.")

            if self.value == "AND":
                self.path_length = min(
                    child.calculate_path().path_length for child in self.children
                )

            elif self.value == "OR":
                self.path_length = sum(
                    child.calculate_path().path_length for child in self.children
                )

            else:
                # NotQuery is not implemented
                raise ValueError("Operator is not yet supported.")

            min_len = self.children[0].path_length
            min_len_child = self.children[0]

            for child in self.children:
                if min_len > child.path_length:
                    min_len = child.path_length
                    min_len_child = child

            return min_len_child

    def _search_records(
        self, term: str, record_list: typing.List[Record]
    ) -> typing.List[Record]:
        """Searches the title of a record for the search term."""

        rec_list = []

        for record in record_list:
            if record.data.get("title"):
                if re.search(f"(^|[^a-zA-Z]){term.lower()}([^a-zA-Z]|$)", 
                             record.data.get("title").lower(),
                             re.IGNORECASE) is not None:
                    rec_list.append(record)

        return rec_list

    def filter_records(
        self, parent_records: typing.List[Record]
    ) -> typing.List[Record]:
        """Filter record list for AND or OR subquery."""

        if self.operator:
            if self.value == "AND":
                self.records = self._and_filter(parent_records)

            elif self.value == "OR":
                self.records = self._or_filter(parent_records)

            else:
                # NotQuery is not implemented
                raise ValueError("Operator is not yet supported.")

        else:
            self.records = self._search_records(self.value, parent_records)

        return self.records

    def _and_filter(self, records: typing.List[Record]) -> typing.List[Record]:
        """Filter record list for AND subqueries."""

        for c in self.children:
            if not c.operator:
                records = self._search_records(c.value, records)

        for ch in self.children:
            if ch.operator:
                records = ch.filter_records(records)
        return records

    def _or_filter(self, records: typing.List[Record]) -> typing.List[Record]:
        """Filter record list for OR subqueries."""

        child_records = []
        for c in self.children:
            if not c.operator:
                child_records.extend(self._search_records(c.value, records))
            else:
                child_records.extend(c.filter_records(records))

        return child_records

    def _remove_duplicates(self) -> None:
        """Remove dubplicates in record list."""

        no_duplicates = {}
        for record in self.records:
            no_duplicates[record.data.get("doi")] = record

        self.records = list(no_duplicates.values())

        no_dup = {}
        for record in self.records:
            no_dup[record.data.get("title").lower()] = record

        self.records = list(no_dup.values())


if __name__ == "__main__":
    search_term1 = OrQuery(["strategy", "strategic"], search_field="ti")
    search_term2 = OrQuery(["digital", "technology"], search_field="ti")
    search_query = AndQuery([search_term1, search_term2], search_field="ti")

    results = BEALSCrossref(search_query).run_beals()

    print(len(results))

    for rec in results[:10]:
        print(f"\nDOI: {rec.data.get("doi")}\nTitle: {rec.data.get('title')}\n")

    counter_1 = 0
    all_recs_selected = True
    for rec in results:
        if not search_query.selects(record_dict=rec.data):
            all_recs_selected = False
            print(f"\nDOI: {rec.data.get("doi")}\nTitle: {rec.data.get('title')}\n")
            counter_1 = counter_1 + 1

    if all_recs_selected:
        print("All records fit to query")
    else:
        print(f"Not all records fit to query: {counter_1} false")
