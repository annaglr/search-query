#!/usr/bin/env python
"""Tests for search query BEALS Crossref"""
import typing
import unittest

from search_query.and_query import AndQuery
from search_query.beals import BEALSCrossref
from search_query.constants import Fields
from search_query.or_query import OrQuery
from search_query.query import Query
from search_query.query import SearchField


class TestBEALSCrossref(unittest.TestCase):
    """Testing class for BEALS Crossref"""

    def setUp(self) -> None:
        query_ai = OrQuery(
            ["Artificial Intelligence", "AI", "Machine Learning"],
            search_field=SearchField(Fields.TITLE),
        )

        query_big_data_analytics = OrQuery(
            ['"big data"', "data", "analytics"],
            search_field=SearchField(Fields.TITLE),
        )

        self.example_query = AndQuery(
            [query_ai, query_big_data_analytics],
            search_field=SearchField(Fields.TITLE),
        )

        class MockRecord:
            def __init__(self, data: dict) -> None:
                self.data = data

            def __eq__(self, other: object) -> bool:
                if not isinstance(other, MockRecord):
                    return False
                return self.data == other.data

            def __repr__(self) -> str:
                return f"Record(title={self.data.get('title')}, doi={self.data.get('doi')}) \n"

        self.MockRecord = MockRecord

        class MockSearchQuery(Query):
            def __init__(
                self,
                value: str,
                operator: bool,
                search_field: typing.Optional[SearchField] = None,
                children: typing.List[Query] = [],
            ) -> None:
                self.value = value
                self.operator = operator
                self.search_field = search_field
                self.children = children

        self.MockSearchQuery = MockSearchQuery

        class MockCrossrefAPI:
            @staticmethod
            def get_len_total() -> int:
                return 10

            @staticmethod
            def check_availability() -> bool:
                return True

            @staticmethod
            def get_records() -> typing.List[MockRecord]:
                return [
                    MockRecord(
                        {"title": "The gardener and the tree", "doi": "10.5678/example"}
                    ),
                    MockRecord(
                        {"title": "Big Data Analytics", "doi": "10.6789/example"}
                    ),
                    MockRecord({"title": "Big Data and AI", "doi": "10.7890/example"}),
                    MockRecord(
                        {
                            "title": "Writing systematic literature reviews",
                            "doi": "10.7891/example",
                        }
                    ),
                    MockRecord(
                        {
                            "title": "Harnessing Artificial Intelligence for Big Data Analytics in Modern Enterprises",
                            "doi": "10.7892/example",
                        }
                    ),
                    MockRecord(
                        {
                            "title": "Machine Learning Techniques for Large-Scale Data Analysis",
                            "doi": "10.7893/example",
                        }
                    ),
                    MockRecord(
                        {
                            "title": "AI-Driven Big Data Solutions for Healthcare Innovation",
                            "doi": "10.7894/example",
                        }
                    ),
                    MockRecord(
                        {
                            "title": "Blockchain Technology: Transforming the Supply Chain Industry",
                            "doi": "10.7895/example",
                        }
                    ),
                    MockRecord(
                        {
                            "title": "The Intersection of Machine Learning and Data Analytics in Financial Markets",
                            "doi": "10.7896/example",
                        }
                    ),
                    MockRecord(
                        {
                            "title": "Sustainability in Cloud Computing Infrastructure",
                            "doi": "10.7897/example",
                        }
                    ),
                ]

        self.MockCrossrefAPI = MockCrossrefAPI

    def test_retrieve(self) -> None:
        """Test retrieval of records."""
        beals = BEALSCrossref(self.MockSearchQuery(value="big data", operator=False))
        beals.api = self.MockCrossrefAPI
        records = beals.retrieve()

        self.assertEqual(len(records), 4)
        self.assertEqual(
            records[0].data.get("title"),
            "Big Data Analytics",
            "Retrieval did not work correctly!",
        )

    def test_build_url(self) -> None:
        """Test building the URL."""
        query = self.MockSearchQuery(value="Artificial Intelligence", operator=False)
        beals = BEALSCrossref(query)

        url = beals.build_url(query.value)
        self.assertEqual(
            url,
            "https://api.crossref.org/works?query.title=%22Artificial+Intelligence%22",
            "URL was not built correctly!",
        )

    def test_filter_records_by_term(self) -> None:
        """Test filter_records_by_term that filters records for a specific keyword."""
        beals = BEALSCrossref(self.example_query)
        records = [
            self.MockRecord(
                {"title": "The gardener and the tree", "doi": "10.5678/example"}
            ),
            self.MockRecord({"title": "Big Data Analytics", "doi": "10.6789/example"}),
            self.MockRecord({"title": "Big Data and AI", "doi": "10.7890/example"}),
            self.MockRecord(
                {
                    "title": "Writing systematic literature reviews",
                    "doi": "10.7891/example",
                }
            ),
            self.MockRecord(
                {
                    "title": "Harnessing Artificial Intelligence for Big Data Analytics in Modern Enterprises",
                    "doi": "10.7892/example",
                }
            ),
            self.MockRecord(
                {
                    "title": "Machine Learning Techniques for Large-Scale Data Analysis",
                    "doi": "10.7893/example",
                }
            ),
            self.MockRecord(
                {
                    "title": "AI-Driven Big Data Solutions for Healthcare Innovation",
                    "doi": "10.7894/example",
                }
            ),
            self.MockRecord(
                {
                    "title": "Blockchain Technology: Transforming the Supply Chain Industry",
                    "doi": "10.7895/example",
                }
            ),
            self.MockRecord(
                {
                    "title": "The Intersection of Machine Learning and Data Analytics in Financial Markets",
                    "doi": "10.7896/example",
                }
            ),
            self.MockRecord(
                {
                    "title": "Establishing sustainability in Cloud Computing Infrastructure",
                    "doi": "10.7897/example",
                }
            ),
        ]

        filtered_records = beals._filter_records_by_term(term="big data", record_list=records)
        self.assertEqual(
            len(filtered_records), 4, "Number of returned records is not as expected!"
        )
        self.assertEqual(
            filtered_records[0].data.get("title"),
            "Big Data Analytics",
            "Record does not match the searched keyword!",
        )

    def test_remove_duplicates(self) -> None:
        """Test remove_duplicates based on DOI and title."""
        beals = BEALSCrossref(self.example_query)
        beals.records = [
            self.MockRecord(
                {"title": "The gardener and the tree", "doi": "10.5678/example"}
            ),
            self.MockRecord({"title": "Big Data Analytics", "doi": "10.6789/example"}),
            self.MockRecord({"title": "Big Data and AI", "doi": "10.7890/example"}),
            self.MockRecord(
                {"title": "The gardener and the tree", "doi": "10.6781/example"}
            ),
            self.MockRecord(
                {
                    "title": "Writing systematic literature reviews",
                    "doi": "10.7891/example",
                }
            ),
            self.MockRecord(
                {"title": "Big Data Analytics in Healthcare", "doi": "10.6789/example"}
            ),
        ]

        beals._remove_duplicates()

        self.assertEqual(
            len(beals.records), 4, "Number of returned records is not as expected!"
        )
        self.assertCountEqual(
            beals.records,
            [
                self.MockRecord(
                    {"title": "The gardener and the tree", "doi": "10.6781/example"}
                ),
                self.MockRecord(
                    {
                        "title": "Big Data Analytics in Healthcare",
                        "doi": "10.6789/example",
                    }
                ),
                self.MockRecord({"title": "Big Data and AI", "doi": "10.7890/example"}),
                self.MockRecord(
                    {
                        "title": "Writing systematic literature reviews",
                        "doi": "10.7891/example",
                    }
                ),
            ],
            "Duplicates were not removed correctly!",
        )

    def test_filter_records(self) -> None:
        """Test filter_records."""
        # Search string ("big data" OR "machine") AND (("analytics" AND "financial") OR "solutions"))

        query_10_term = self.MockSearchQuery(value="financial", operator=False)
        beals_10_term = BEALSCrossref(query_10_term)

        query_9_and = self.MockSearchQuery(value="AND", operator=True)
        beals_9_and = BEALSCrossref(query_9_and)

        query_8_term = self.MockSearchQuery(value="Big Data", operator=False)
        beals_8_term = BEALSCrossref(query_8_term)

        query_7_term = self.MockSearchQuery(value="Machine", operator=False)
        beals_7_term = BEALSCrossref(query_7_term)

        query_6_or = self.MockSearchQuery(value="OR", operator=True)
        beals_6_or = BEALSCrossref(query_6_or)

        query_5_term = self.MockSearchQuery(value="solutions", operator=False)
        beals_5_term = BEALSCrossref(query_5_term)

        query_4_term = self.MockSearchQuery(value="analytics", operator=False)
        beals_4_term = BEALSCrossref(query_4_term)

        query_3_or = self.MockSearchQuery(value="OR", operator=True)
        beals_3_or = BEALSCrossref(query_3_or)

        query_1_and = self.MockSearchQuery(value="AND", operator=True)
        beals_1_and = BEALSCrossref(query_1_and)

        beals_1_and.records = [
            self.MockRecord(
                {"title": "The gardener and the tree", "doi": "10.5678/example"}
            ),
            self.MockRecord({"title": "Big Data Analytics", "doi": "10.6789/example"}),
            self.MockRecord({"title": "Big Data and AI", "doi": "10.7890/example"}),
            self.MockRecord(
                {
                    "title": "Writing systematic literature reviews",
                    "doi": "10.7891/example",
                }
            ),
            self.MockRecord(
                {
                    "title": "Harnessing Artificial Intelligence for Big Data Analytics in Modern Enterprises",
                    "doi": "10.7892/example",
                }
            ),
            self.MockRecord(
                {
                    "title": "Machine Learning Techniques for Large-Scale Data Analysis",
                    "doi": "10.7893/example",
                }
            ),
            self.MockRecord(
                {
                    "title": "AI-Driven Big Data Solutions for Healthcare Innovation",
                    "doi": "10.7894/example",
                }
            ),
            self.MockRecord(
                {
                    "title": "Blockchain Technology: Transforming the Supply Chain Industry",
                    "doi": "10.7895/example",
                }
            ),
            self.MockRecord(
                {
                    "title": "The Intersection of Machine Learning and Data Analytics in Financial Markets",
                    "doi": "10.7896/example",
                }
            ),
            self.MockRecord(
                {
                    "title": "Establishing sustainability in Cloud Computing Infrastructure",
                    "doi": "10.7897/example",
                }
            ),
        ]
        beals_1_and.children.extend([beals_6_or, beals_3_or])
        beals_6_or.children.extend([beals_8_term, beals_7_term])
        beals_3_or.children.extend([beals_9_and, beals_5_term])
        beals_9_and.children.extend([beals_4_term, beals_10_term])

        for c in beals_1_and.children:
            beals_1_and.records = c.filter_records(beals_1_and.records)

        self.assertEqual(
            len(beals_1_and.records),
            2,
            "Number of filtered records is not as expected!",
        )

        self.assertCountEqual(
            beals_1_and.records,
            [
                self.MockRecord(
                    {
                        "title": "The Intersection of Machine Learning and Data Analytics in Financial Markets",
                        "doi": "10.7896/example",
                    }
                ),
                self.MockRecord(
                    {
                        "title": "AI-Driven Big Data Solutions for Healthcare Innovation",
                        "doi": "10.7894/example",
                    }
                ),
            ],
            "Records were not filtered correctly!",
        )


if __name__ == "__main__":
    unittest.main()
