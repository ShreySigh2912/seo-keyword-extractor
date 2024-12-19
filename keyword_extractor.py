import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urlparse
from collections import Counter
import yake
import argparse
import time
from tqdm import tqdm

class KeywordExtractor:
    def __init__(self, url, max_pages=10):
        self.base_url = url
        self.domain = urlparse(url).netloc
        self.max_pages = max_pages
        self.visited_urls = set()
        self.keywords = []
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def get_internal_links(self, url):
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            links = set()
            
            for link in soup.find_all('a'):
                href = link.get('href')
                if href:
                    if href.startswith('/'):
                        links.add(self.base_url + href)
                    elif href.startswith(self.base_url):
                        links.add(href)
            
            return links
        except Exception as e:
            print(f'Error fetching links from {url}: {str(e)}')
            return set()

    def extract_keywords_from_page(self, url):
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(['script', 'style']):
                script.decompose()
            
            # Extract text content
            text = soup.get_text(separator=' ')
            
            # Use YAKE for keyword extraction
            kw_extractor = yake.KeywordExtractor(
                lan='en',
                n=2,  # ngram size
                dedupLim=0.3,
                top=10,
                features=None
            )
            
            keywords = kw_extractor.extract_keywords(text)
            return [kw[0] for kw in keywords]  # Return only the keywords, not their scores
            
        except Exception as e:
            print(f'Error extracting keywords from {url}: {str(e)}')
            return []

    def crawl(self):
        urls_to_visit = {self.base_url}
        
        with tqdm(total=self.max_pages, desc='Crawling pages') as pbar:
            while urls_to_visit and len(self.visited_urls) < self.max_pages:
                url = urls_to_visit.pop()
                
                if url not in self.visited_urls:
                    self.visited_urls.add(url)
                    
                    # Extract keywords from the current page
                    page_keywords = self.extract_keywords_from_page(url)
                    self.keywords.extend(page_keywords)
                    
                    # Find new URLs to visit
                    new_urls = self.get_internal_links(url)
                    urls_to_visit.update(new_urls - self.visited_urls)
                    
                    pbar.update(1)
                    time.sleep(1)  # Be nice to the server

    def save_results(self, output_file='keywords.csv'):
        # Count keyword frequencies
        keyword_freq = Counter(self.keywords)
        
        # Create DataFrame and save to CSV
        df = pd.DataFrame(keyword_freq.items(), columns=['Keyword', 'Frequency'])
        df = df.sort_values('Frequency', ascending=False)
        df.to_csv(output_file, index=False)
        print(f'Results saved to {output_file}')

def main():
    parser = argparse.ArgumentParser(description='Extract keywords from a website')
    parser.add_argument('url', help='URL of the website to analyze')
    parser.add_argument('--max-pages', type=int, default=10, help='Maximum number of pages to crawl')
    parser.add_argument('--output', default='keywords.csv', help='Output file name')
    
    args = parser.parse_args()
    
    extractor = KeywordExtractor(args.url, args.max_pages)
    print(f'Starting crawl of {args.url}')
    extractor.crawl()
    extractor.save_results(args.output)

if __name__ == '__main__':
    main()