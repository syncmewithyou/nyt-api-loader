import argparse
import logging
import json
from nytimes_source import NYTimesSource

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='NYTimes Article Search API Data Loader')
    parser.add_argument('--api_key', required=True, help='API key')
    parser.add_argument('--query', default='news', help='Search query')
    parser.add_argument('--batch_size', type=int, default=10, help='Articles per batch')
    parser.add_argument('--max_pages', type=int, default=5, help='Maximum pages to fetch (default: 5)')
    parser.add_argument('--incremental_marker', help='Timestamp for incremental loading (format: YYYY-MM-DDThh:mm:ssZ)')
    parser.add_argument('--print_all', action='store_true', help='Print all flattened dictionaries instead of just the first one')

    args = parser.parse_args()
    logging.getLogger().setLevel(logging.INFO)
    
    print(f"\n=== NYTimes Article Search: '{args.query}' ===")
    
    # Create and initialize data source
    source = NYTimesSource()
    source.args = args
    source.connect(inc_column='pub_date', max_inc_value=args.incremental_marker)
    
    # Initilaze variables to keep track of articles for display purposes
    all_articles = []
    first_article = None
    batch_count = 0
    article_count = 0
    
    # Process batches of articles
    for idx, batch in enumerate(source.getDataBatch(args.batch_size)):
        batch_count += 1
        article_count += len(batch)
        
        print(f"\nBatch {idx}: {len(batch)} articles")
        
        # Show all articles in the batch
        for item in batch:
            print(f" - {item.get('_id', 'N/A')} - {item.get('headline.main', 'No headline')}")
            
        # Save articles for demonstration
        if args.print_all:
            all_articles.extend(batch)
        elif idx == 0 and batch:
            first_article = batch[0]
    
    print("\n=== Summary ===")
    print(f"Total batches: {batch_count}")
    print(f"Total articles: {article_count}")
    
    # Add latest timestamp for easy incremental loading testing for multiple runs
    if source.new_latest_timestamp:
        latest_timestamp = source.new_latest_timestamp.strftime(source.TIMESTAMP_FORMAT)
        print(f"\n=== For Incremental Loading Testing ===")
        print(f"Latest article timestamp: {latest_timestamp}")
        print(f"Use this with CLI argument to get only newer articles in next run:")
        print(f"--incremental_marker \"{latest_timestamp}\"")
    elif args.incremental_marker and article_count == 0:
        print(f"\n=== No articles found newer than {args.incremental_marker} ===")
        print("Try using an earlier date or a different query.")
    
    # Print all articles or just the first one
    if args.print_all and all_articles:
        print(f"\n=== All Flattened Articles ({len(all_articles)}) ===")
        for i, article in enumerate(all_articles):
            print(f"\n--- Article {i+1} ---")
            print(json.dumps(article, indent=2))
    elif first_article:
        print("\n=== Flattened Dictionary ===")
        # Show the full flattened dictionary structure
        print(json.dumps(first_article, indent=2))
    
    print("\n=== Dynamic Schema ===")
    schema = source.getSchema()
    print(f"Total fields: {len(schema)}")
    print("All schema fields:")
    print(json.dumps(schema, indent=2))
    
    source.disconnect()
    
    print("\n=== Done ===")