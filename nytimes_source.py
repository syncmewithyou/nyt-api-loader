import logging
import requests
from datetime import datetime, timezone, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

class NYTimesSource:
    """A data loader plugin for the NY Times API."""
    BASE_URL = "https://api.nytimes.com/svc/search/v2/articlesearch.json"
    TIMESTAMP_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
    API_DATE_FORMAT = '%Y%m%d'
    API_MAX_PAGE = 99

    def __init__(self):
        self.session = None
        self.current_page = 0
        self.all_fields = set()  # Used to track fields for 
        self.query_params = {}
        self.incremental_start_time = None
        self.new_latest_timestamp = None
        self.args = None
        self.max_pages = 5  # Limit API calls to avoid rate limiting issues 

    @staticmethod
    def flatten_dict(dictionary):
        """Flattens a nested dictionary."""
        result = {}
        if not isinstance(dictionary, dict):
            return result

        stack = [('', dictionary)]
        while stack:
            prefix, current = stack.pop()
            if not isinstance(current, dict):
                continue

            for key, value in current.items():
                new_key = f"{prefix}{key}" if prefix else str(key)
                if isinstance(value, dict):
                    stack.append((f"{new_key}.", value))
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        item_key = f"{new_key}.{i}"
                        if isinstance(item, dict):
                            stack.append((f"{item_key}.", item))
                        elif isinstance(item, list):
                            stack.append((f"{item_key}.", {str(j): v for j, v in enumerate(item)}))
                        else:
                            result[item_key] = item
                else:
                    result[new_key] = value
        return result

    def connect(self, inc_column=None, max_inc_value=None):
        """Connect to the source"""
        log.debug("Incremental Column: %r", inc_column)
        log.debug("Incremental Last Value: %r", max_inc_value)
        
        self.session = requests.Session()
        self.session.headers.update({'Accept': 'application/json'})
        self.current_page = 0
        self.all_fields = set()
        
        # Get max pages from args if provided
        self.max_pages = getattr(self.args, 'max_pages', self.max_pages)

        # Setup query parameters
        self.query_params = {
            'q': getattr(self.args, 'query', ''),
            'api-key': getattr(self.args, 'api_key', ''),
            'sort': 'newest',
        }
        
        # Setup incremental loading if marker provided
        if max_inc_value:
            try:
                self.incremental_start_time = datetime.strptime(
                    max_inc_value, self.TIMESTAMP_FORMAT).replace(tzinfo=timezone.utc)
                self.new_latest_timestamp = self.incremental_start_time
                
                one_day_before = (self.incremental_start_time - timedelta(days=1))
                begin_date = one_day_before.strftime(self.API_DATE_FORMAT)
                self.query_params['begin_date'] = begin_date
                
                # Keep newest sort order
                log.info(f"Incremental loading enabled with begin_date={begin_date} and timestamp marker: {max_inc_value}")
            except ValueError:
                log.error("Invalid timestamp format. Disabling incremental loading.")
                self.incremental_start_time = None
                self.new_latest_timestamp = None

    def disconnect(self):
        """Disconnect from the source."""
        if self.session:
            self.session.close()
            self.session = None

    def _get_articles(self):
        """Fetches articles for the current page."""
        # Check pagination limits (per API specs)
        if self.current_page > self.API_MAX_PAGE or self.current_page >= self.max_pages:
            return []
        # Sleep to avoid rate limiting issues (per API specs)
        if self.current_page > 0: 
            import time
            time.sleep(12) 

        self.query_params['page'] = self.current_page
        
        try:
            response = self.session.get(self.BASE_URL, params=self.query_params, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get('response', {}).get('docs', [])
        except Exception as e:
            log.error(f"Error fetching articles: {e}")
            return []

    def getDataBatch(self, batch_size):
        """
        Generator - Get data from source on batches.
        :returns One list for each batch. Each of those is a list of
        dictionaries with the defined rows.
        """
        if not self.session:
            return
        
        documents = []
        
        while True:
            # Check if we've reached max pages
            if self.current_page >= self.max_pages:
                log.info(f"Reached maximum page limit ({self.max_pages})")
                break
                
            # Fetch articles
            try:
                docs = self._get_articles()
            except Exception as e:
                log.error(f"Error fetching articles: {e}")
                break
                
            # End of results
            if not docs:
                break
            
            # Check incremental cutoff 
            if self.incremental_start_time and docs[0].get('pub_date'):
                try:
                    first_time = datetime.strptime(
                        docs[0]['pub_date'], self.TIMESTAMP_FORMAT).replace(tzinfo=timezone.utc)
                    if first_time < self.incremental_start_time:
                        log.info("Reached articles older than incremental marker, stopping")
                        break
                except ValueError as e:
                    log.warning(f"Date parsing error: {e}")
                    pass
            
            # Process documents
            for doc in docs:
                pub_date = doc.get('pub_date')
                article_time = None
                
                # Filter for incremental loading
                if self.incremental_start_time and pub_date:
                    try:
                        article_time = datetime.strptime(
                            pub_date, self.TIMESTAMP_FORMAT).replace(tzinfo=timezone.utc)
                        if article_time <= self.incremental_start_time:
                            continue
                    except ValueError:
                        article_time = None
                
                # Flatten document
                flat_doc = self.flatten_dict(doc)
                if not flat_doc:
                    continue
                
                # Update schema and add to batch
                self.all_fields.update(flat_doc.keys())
                documents.append(flat_doc)
                
                # Update latest timestamp for incremental loading
                if article_time and (not self.new_latest_timestamp or 
                                     article_time > self.new_latest_timestamp):
                    self.new_latest_timestamp = article_time
                
                # Yield batch if full
                if len(documents) >= batch_size:
                    yield documents
                    documents = []
            
            # Move to next page
            self.current_page += 1
        
        # Yield any remaining documents
        if documents:
            yield documents

    def getSchema(self):
        """
        Return the schema of the dataset
        :returns a List containing the names of the columns retrieved from the
        source
        """
        return sorted(list(self.all_fields))