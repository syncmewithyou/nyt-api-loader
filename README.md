# NYTimes API Data Loader

## Description
Data loader for fetching and processing articles from the NYT Article Search API.

## Features
- Fetches articles from NYT API in batches
- Flattens nested dictionaries 
- Supports incremental loading based on publication date
- Generates dynamic schema for article fields
- Error handling & retry logic for API requests

## Usage

### CLI Arguments:
- `--api_key` (required): Your NYT API key
- `--query` (default: "news"): Search query term
- `--batch_size` (default: 10): Number of articles per batch
- `--max_pages` (default: 5): Maximum number of pages to fetch
- `--incremental_marker`: Timestamp for incremental loading (format: YYYY-MM-DDThh:mm:ssZ)
- `--print_all`: Print all flattened dictionaries instead of just the first one

## Examples

### Basic search: 
```bash
python main.py --api_key YOUR_API_KEY --query "Silicon Valley"
```

### Incremental loading - fetch only articles newer than a specific date:  
```bash
python main.py --api_key YOUR_API_KEY --query "Silicon Valley" --incremental_marker "2024-03-01T00:00:00Z"
```

### Customize batch size and page limit:
```bash
python main.py --api_key YOUR_API_KEY --query "Silicon Valley" --batch_size 5 --max_pages 3
```

### Print all flattened article dictionaries:
```bash
python main.py --api_key YOUR_API_KEY --query "Silicon Valley" --print_all
```

### Simulating future incremental load (use output from previous run):
#### First run - capture a timestamp
```bash
python main.py --api_key YOUR_API_KEY --query "Silicon Valley" --incremental_marker "2024-03-01T00:00:00Z"
```

#### Later run - use the timestamp from a previous article
```bash
python main.py --api_key YOUR_API_KEY --query "Silicon Valley" --incremental_marker "2024-03-04T12:55:02Z"
```
## Assumptions

1. The implementation assumes the NYTimes API structure is relatively stable. The dynamic schema generation helps adapt to minor changes, but major API redesigns would require code updates.

2. The flattening function assumes dot notation is an appropriate way to represent nested fields (e.g., `headline.main`). This is usually a standard but there are other notations too.

3. I prioritized memory efficiency over processing speed by implementing a generator-based approach that processes articles in batches rather than loading all results at once.

4. The implementation assumes exact timestamp precision is more important than minimizing API calls. The code queries by date at the API level but filters by exact timestamp at the client level making sure all articles are processed.

5. The code assumes publication dates from the API consistently follow the format defined in `TIMESTAMP_FORMAT`. Inconsistent date formats would require more robust parsing.

6. Basic error handling is implemented with the assumption that transient errors should be logged but not cause the entire process to fail.

7. Default values (5 pages, 10 articles per batch) were chosen as reasonable limits for typical usage and to prevent accidental API abuse.

8.  For standard searches, we assume users want the newest articles first (sort=newest). For incremental loading, we use oldest first (sort=oldest) to ensure proper chronological processing.

9. The dynamic schema generation assumes downstream systems would benefit from knowing all possible fields, even those that appear infrequently. This could be enhancent further to actually be useful.

## Dependencies

- requests

## Installation

```bash
pip install -r requirements.txt
```