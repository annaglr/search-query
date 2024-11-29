import datetime

from colrev.packages.crossref.src import crossref_api
import logging

from search_query import OrQuery, AndQuery


class BEALSCrossref:
    _api_url = "https://api.crossref.org/"
    
    def __init__(self, query) -> None:
        self.value = query.value
        self.operator = query.operator
        self.search_field = query.search_field
        self.children = [BEALSCrossref(child) for child in query.children]
        self.records = []

        self.api = crossref_api.CrossrefAPI(params={})

        self.logger = logging.getLogger(__name__)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
        )
        
        self.path_length = -1     

    def retrieve(self) -> list:
        # retrieve results from the API

        url = self.build_url(self.value)
        self.api.params = {"url" : url}
        
        num_res = self.api.get_len_total()

        # checks availability of Crossref API
        self.api.check_availability()

        self.logger.info(f"Retrieve {num_res:,} records")

        estimated_time = num_res * 0.007 + 5
        estimated_time_formatted = str(datetime.timedelta(seconds=int(estimated_time)))
        self.logger.info(f"Estimated time: {estimated_time_formatted}")
           
        prep_records = list(self.api.get_records())
        records = self._search_records(term=self.value, record_list=prep_records)
        self.logger.info(f"Finished and retrieved {str(len(records))} records.")

        return records


    def build_url(self, query: str) -> str:
        query = query.replace(" ", "+")
        url = (
            self._api_url
            + "works?"
            + "query.bibliographic=%22"
            + query
            + "%22"
        )

        return url


    def _combine_results_from_children(self) -> None:
        # combine the records from the children (OR operator)
        # DOI used as identifier for records
       
        child_records = {}
        for child in self.children:
            for record in child.records:
                child_records[record.data.get("doi")] = record
        
        self.records = [record for record in child_records.values()]


    def run_beals(self) -> list:
        # base case: call self.retrieve if the query is a simple term and assign the results to self.records
        if not self.operator:
            self.records = self.retrieve()
            self._remove_duplicates()

        else:
            # recursive cases: call APIXY(x).run_beals() for x in children and combine the results
            if self.value == "AND":
                
                next_child = self.calculate_path()
                self.records = next_child.run_beals()
            
                for c in self.children:
                    if c != next_child:
                        self.records = c._filter_records(self.records)

                self._remove_duplicates()
                
            elif self.value == "NOT":
                # NotQuery is not implemented yet
                pass
            else:
                # OR operator
                for child in self.children:
                    child.run_beals()
                self._combine_results_from_children()
                self._remove_duplicates()

        return self.records
    

    def calculate_path(self):
        if not self.operator:
            self.api.params = {"url" : self.build_url(self.value)}
            self.path_length = self.api.get_len_total()
            return self
        else:
            if len(self.children) == 0:
                print("AndQuery and OrQuery must have at least one child.")
                return None

            if self.value == "AND":
                self.path_length = min([child.calculate_path().path_length for child in self.children])
            
            elif self.value == "OR":
                self.path_length = sum([child.calculate_path().path_length for child in self.children])

            else:
                # NotQuery not yet supported
                print("NotQuery is not supported yet.")
                return None
            
            min_len = self.children[0].path_length
            min_len_child = self.children[0]

            for child in self.children:
                if min_len > child.path_length:
                    min_len = child.path_length
                    min_len_child = child
            
            return min_len_child
            

    def _search_records(self, term: str, record_list) -> list:
        rec_list = []

        for record in record_list:
            if record.data.get("title"):
                if term.lower() in record.data.get("title").lower():
                    rec_list.append(record)

        return rec_list
    

    def _filter_records(self, parent_records) -> list:
        if self.operator:
            if self.value == "AND":
                self.records = self._AND_filter(parent_records)

            elif self.value == "OR":
                self.records = self._OR_filter(parent_records)
                
            else:
                # NotQuery not implemented yet
                print("NotQuery is not implemented yet")
                pass

        else:
            self.records = self._search_records(self.value, parent_records)
        
        return self.records


    def _AND_filter(self, records: list) -> list:
        for c in self.children:
            if not c.operator:
                records = self._search_records(c.value, records)
        
        for ch in self.children:
            if ch.operator:
                records = ch._filter_records(records)
        return records
    

    def _OR_filter(self, records) -> list:
        child_records = []
        for c in self.children:
            if not c.operator:
                child_records.extend(self._search_records(c.value, records))
            else:
                child_records.extend(c._filter_records(records))
        
        return child_records

    def _remove_duplicates(self) -> None:
        no_duplicates = {}
        for record in self.records:
            no_duplicates[record.data.get("doi")] = record
        
        self.records = [record for record in no_duplicates.values()]

        no_dup = {}
        for record in self.records:
            no_dup[record.data.get("title").lower()] = record
        
        self.records = [record for record in no_dup.values()]

    
if __name__ == "__main__":

    search_query = AndQuery(["lululemon", "analysis"], search_field="ti")
    results = BEALSCrossref(search_query).run_beals()

    print(len(results))

    for rec in results[:20]:
        print(f"\nDOI: {rec.data.get("doi")}\nTitle: {rec.data.get('title')}\n")
    
