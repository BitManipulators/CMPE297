#!/usr/bin/env python3
"""
Wikipedia Species Content Scraper for RAG System

This script extracts Wikipedia content for plant and animal species to build a knowledge base
for a Retrieval-Augmented Generation (RAG) system.
"""

import json
import time
import requests
import sys
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import wikipedia
import wikipediaapi
from urllib.parse import quote
import re
import threading


@dataclass
class SpeciesInfo:
    """Data class for species information (plants and animals)."""
    scientific_name: str
    common_name: str
    family: str
    genus: str
    order: str
    class_name: str
    phylum: str
    kingdom: str = ""
    wikipedia_url: str = ""
    summary: str = ""
    content: str = ""
    images: List[str] = None
    categories: List[str] = None
    error: str = ""

    def __post_init__(self):
        if self.images is None:
            self.images = []
        if self.categories is None:
            self.categories = []


class WikipediaSpeciesScraper:
    """Scraper for Wikipedia species content (plants and animals)."""

    def __init__(self,
                 language: str = 'en',
                 user_agent: str = 'Species/1.0',
                 max_content_chars: int = 15000,
                 max_section_chars: int = 2000,
                 validation_check_chars: int = 500):
        """
        Initialize the scraper.

        Args:
            language: Wikipedia language code
            user_agent: User agent string for requests
            max_content_chars: Maximum characters to extract from main content
            max_section_chars: Maximum characters per section
            validation_check_chars: Characters to check for taxonomic terms
        """
        self.language = language
        self.user_agent = user_agent
        self.max_content_chars = max_content_chars
        self.max_section_chars = max_section_chars
        self.validation_check_chars = validation_check_chars
        self.wiki_api = wikipediaapi.Wikipedia(
            language=language,
            user_agent=user_agent
        )
        # Set user agent for wikipedia library
        wikipedia.set_user_agent(user_agent)
        wikipedia.set_lang(language)

        # Rate limiting
        self.request_delay = 0.1  # 100ms between requests
        self.last_request_time = 0

        # Statistics
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'not_found': 0,
            'disambiguation': 0
        }

        # Thread safety for file writing
        self.file_lock = threading.Lock()
        self.species_written = 0

    def _rate_limit(self):
        """Implement rate limiting."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.request_delay:
            time.sleep(self.request_delay - time_since_last)
        self.last_request_time = time.time()

    def search_species_page(self, scientific_name: str, common_name: str = "", kingdom: str = "") -> Optional[str]:
        """
        Search for the best Wikipedia page for a species (plant or animal).

        Args:
            scientific_name: Scientific name of the species
            common_name: Common name of the species
            kingdom: Kingdom of the species (e.g., 'Plantae', 'Animalia')

        Returns:
            Best matching page title or None
        """
        # Build search terms based on kingdom
        search_terms = [scientific_name, f"{scientific_name} species"]

        if kingdom:
            if kingdom.lower() == 'plantae':
                search_terms.append(f"{scientific_name} plant")
            elif kingdom.lower() == 'animalia':
                search_terms.append(f"{scientific_name} animal")

        if common_name and common_name != "":
            search_terms.extend([common_name, f"{common_name} {scientific_name}"])
            if kingdom:
                if kingdom.lower() == 'plantae':
                    search_terms.append(f"{common_name} plant")
                elif kingdom.lower() == 'animalia':
                    search_terms.append(f"{common_name} animal")

        # Taxonomic validation terms (works for both plants and animals)
        taxonomic_terms = [
            'species', 'plant', 'animal', 'flower', 'tree', 'shrub', 'herb',
            'bird', 'mammal', 'reptile', 'amphibian', 'insect', 'fish',
            'family', 'genus', 'botanical', 'zoological', 'flora', 'fauna',
            'leaf', 'stem', 'wing', 'feather', 'habitat', 'distribution'
        ]

        for term in search_terms:
            try:
                self._rate_limit()

                # Try direct page access first
                page = self.wiki_api.page(term)
                if page.exists():
                    # Check if it's about the species (look for taxonomic terms)
                    summary = page.summary[:self.validation_check_chars].lower()
                    if any(tax_term in summary for tax_term in taxonomic_terms):
                        return page.title

                # If direct access fails, try search
                search_results = wikipedia.search(term, results=5)
                for result in search_results:
                    try:
                        self._rate_limit()
                        page = self.wiki_api.page(result)
                        if page.exists():
                            summary = page.summary[:self.validation_check_chars].lower()
                            if any(tax_term in summary for tax_term in taxonomic_terms):
                                return page.title
                    except Exception:
                        continue

            except Exception as e:
                print(f"Search error for '{term}': {e}")
                continue

        return None

    def extract_species_content(self, page_title: str) -> Dict[str, any]:
        """
        Extract comprehensive content from a Wikipedia page.

        Args:
            page_title: Wikipedia page title

        Returns:
            Dictionary with extracted content
        """
        try:
            self._rate_limit()
            page = self.wiki_api.page(page_title)

            if not page.exists():
                return {'error': 'Page does not exist'}

            # Extract main content
            content = {
                'title': page.title,
                'url': page.fullurl,
                'summary': page.summary,
                'content': page.text[:self.max_content_chars],  # Configurable content limit
                'categories': list(page.categories.keys())[:20],  # Top 20 categories
                'images': [],
                'sections': {}
            }

            # Extract key sections
            key_sections = [
                'Description', 'Habitat', 'Distribution', 'Ecology',
                'Uses', 'Cultivation', 'Taxonomy', 'Etymology'
            ]

            for section_title in key_sections:
                if section_title in page.sections:
                    section = page.sections[section_title]
                    content['sections'][section_title] = section.text[:self.max_section_chars]  # Configurable section limit

            # Skip image extraction to focus on text content only
            content['images'] = []

            return content

        except Exception as e:
            return {'error': str(e)}

    def scrape_species(self, category: Dict[str, any]) -> SpeciesInfo:
        """
        Scrape Wikipedia content for a single species (plant or animal).

        Args:
            category: Species category from iNaturalist dataset

        Returns:
            SpeciesInfo object with scraped content
        """
        scientific_name = category.get('name', '')
        common_name = category.get('common_name', '')
        kingdom = category.get('kingdom', '')

        species_info = SpeciesInfo(
            scientific_name=scientific_name,
            common_name=common_name,
            family=category.get('family', ''),
            genus=category.get('genus', ''),
            order=category.get('order', ''),
            class_name=category.get('class', ''),
            phylum=category.get('phylum', ''),
            kingdom=kingdom
        )

        self.stats['total_processed'] += 1

        try:
            # Find the best Wikipedia page
            page_title = self.search_species_page(scientific_name, common_name, kingdom)

            if not page_title:
                species_info.error = "No suitable Wikipedia page found"
                self.stats['not_found'] += 1
                return species_info

            # Extract content
            content = self.extract_species_content(page_title)

            if 'error' in content:
                species_info.error = content['error']
                self.stats['failed'] += 1
                return species_info

            # Populate species info
            species_info.wikipedia_url = content['url']
            species_info.summary = content['summary']
            species_info.content = content['content']
            species_info.images = content['images']
            species_info.categories = content['categories']

            # Add section content to main content
            if content['sections']:
                sections_text = "\n\n".join([
                    f"## {section}\n{text}"
                    for section, text in content['sections'].items()
                ])
                species_info.content += f"\n\n{sections_text}"

            self.stats['successful'] += 1

        except Exception as e:
            species_info.error = str(e)
            self.stats['failed'] += 1

        return species_info

    def scrape_species_batch(self, categories: List[Dict[str, any]],
                           max_workers: int = 5, batch_size: int = 100) -> List[SpeciesInfo]:
        """
        Scrape Wikipedia content for multiple species with threading.

        Args:
            categories: List of species categories from iNaturalist
            max_workers: Number of concurrent threads
            batch_size: Number of species to process in each batch

        Returns:
            List of SpeciesInfo objects
        """
        all_results = []
        total_species = len(categories)

        print(f"Starting to scrape {total_species} species...")

        # Process in batches to manage memory
        for i in range(0, total_species, batch_size):
            batch = categories[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total_species + batch_size - 1) // batch_size

            print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} species)...")

            batch_results = []
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_category = {
                    executor.submit(self.scrape_species, category): category
                    for category in batch
                }

                # Collect results
                for future in as_completed(future_to_category):
                    try:
                        result = future.result()
                        batch_results.append(result)

                        # Progress update
                        if len(batch_results) % 10 == 0:
                            print(f"  Completed {len(batch_results)}/{len(batch)} in current batch")

                    except Exception as e:
                        category = future_to_category[future]
                        print(f"Error processing {category.get('name', 'Unknown')}: {e}")

            all_results.extend(batch_results)

            # Print batch statistics
            print(f"Batch {batch_num} complete. Total progress: {len(all_results)}/{total_species}")
            self.print_stats()

            # Small delay between batches
            time.sleep(1)

        return all_results

    def scrape_species_streaming(self, categories: List[Dict[str, any]], output_file: str,
                               max_workers: int = 3, batch_size: int = 50):
        """
        Scrape Wikipedia content with streaming writes to file (thread-safe).

        Args:
            categories: List of species categories from iNaturalist
            output_file: Output JSON file path
            max_workers: Number of concurrent threads
            batch_size: Number of species to process in each batch
        """
        total_species = len(categories)

        print(f"Starting streaming scrape of {total_species} species...")
        print(f"Results will be written to: {output_file}")

        # Process in batches to manage memory
        for i in range(0, total_species, batch_size):
            batch = categories[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total_species + batch_size - 1) // batch_size

            print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} species)...")

            batch_completed = 0
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_category = {
                    executor.submit(self.scrape_species, category): category
                    for category in batch
                }

                # Process results as they complete
                for future in as_completed(future_to_category):
                    try:
                        result = future.result()

                        # Write result immediately to file (thread-safe)
                        self.append_result_to_file(result, output_file)

                        batch_completed += 1

                        # Progress update
                        if batch_completed % 10 == 0:
                            print(f"  Completed {batch_completed}/{len(batch)} in current batch")

                    except Exception as e:
                        category = future_to_category[future]
                        print(f"Error processing {category.get('name', 'Unknown')}: {e}")

            # Print batch statistics
            print(f"Batch {batch_num} complete. Total progress: {self.species_written}/{total_species}")
            self.print_stats()

            # Small delay between batches
            time.sleep(1)

        # Finalize the JSON file
        self.finalize_json_file(output_file)
        print(f"\nStreaming scrape complete! Results saved to: {output_file}")

    def save_results(self, results: List[SpeciesInfo], output_file: str):
        """Save scraping results to JSON file."""
        # Convert to serializable format
        data = []
        for species in results:
            species_dict = {
                'scientific_name': species.scientific_name,
                'common_name': species.common_name,
                'family': species.family,
                'genus': species.genus,
                'order': species.order,
                'class': species.class_name,
                'phylum': species.phylum,
                'kingdom': species.kingdom,
                'wikipedia_url': species.wikipedia_url,
                'summary': species.summary,
                'content': species.content,
                'images': species.images,
                'categories': species.categories,
                'error': species.error
            }
            data.append(species_dict)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"Results saved to {output_file}")

    def append_result_to_file(self, species: SpeciesInfo, output_file: str):
        """Thread-safe append of a single species result to JSON file incrementally."""
        species_dict = {
            'scientific_name': species.scientific_name,
            'common_name': species.common_name,
            'family': species.family,
            'genus': species.genus,
            'order': species.order,
            'class': species.class_name,
            'phylum': species.phylum,
            'kingdom': species.kingdom,
            'wikipedia_url': species.wikipedia_url,
            'summary': species.summary,
            'content': species.content,
            'images': species.images,
            'categories': species.categories,
            'error': species.error
        }

        # Thread-safe file writing
        with self.file_lock:
            is_first = self.species_written == 0

            mode = 'w' if is_first else 'a'
            with open(output_file, mode, encoding='utf-8') as f:
                if is_first:
                    f.write('[\n')
                else:
                    f.write(',\n')

                # Write the species data with proper indentation
                json_str = json.dumps(species_dict, indent=2, ensure_ascii=False)
                # Indent each line by 2 spaces to match array formatting
                indented_json = '\n'.join('  ' + line for line in json_str.split('\n'))
                f.write(indented_json)
                f.flush()  # Ensure data is written immediately

            self.species_written += 1

    def finalize_json_file(self, output_file: str):
        """Close the JSON array in the output file."""
        with open(output_file, 'a', encoding='utf-8') as f:
            f.write('\n]\n')

    def print_stats(self):
        """Print scraping statistics."""
        print(f"\nScraping Statistics:")
        print(f"  Total processed: {self.stats['total_processed']}")
        print(f"  Successful: {self.stats['successful']}")
        print(f"  Failed: {self.stats['failed']}")
        print(f"  Not found: {self.stats['not_found']}")
        if self.stats['total_processed'] > 0:
            success_rate = (self.stats['successful'] / self.stats['total_processed']) * 100
            print(f"  Success rate: {success_rate:.1f}%")


def load_species_categories(json_file: str) -> List[Dict[str, any]]:
    """Load species categories from iNaturalist JSON file."""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('categories', [])
    except Exception as e:
        print(f"Error loading categories: {e}")
        return []


def main():
    """Main function to run Wikipedia scraping."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python wikipedia_scraper.py <species_json_file> [output_file] [max_species] [max_content_chars] [--streaming]")
        print("")
        print("Examples:")
        print("  python wikipedia_scraper.py train_mini_plantae_only.json")
        print("  python wikipedia_scraper.py train_mini_animalia_only.json animal_content.json 100")
        print("  python wikipedia_scraper.py train_mini_animalia_only.json animal_content.json 100 15000")
        print("  python wikipedia_scraper.py train_mini_animalia_only.json animal_content.json 0 15000 --streaming")
        print("")
        print("Parameters:")
        print("  max_species: Limit number of species to process (default: all, 0 = all)")
        print("  max_content_chars: Maximum characters per species (default: 15000)")
        print("  --streaming: Use streaming mode (writes results immediately, thread-safe)")
        print("")
        print("Streaming Mode Benefits:")
        print("  - Low memory usage (doesn't store all results in memory)")
        print("  - Crash-resistant (partial results saved)")
        print("  - Real-time progress (file grows as processing happens)")
        print("  - Thread-safe file writing")
        sys.exit(1)

    # Parse arguments
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'species_wikipedia_content.json'
    max_species = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] != '0' else None
    max_content_chars = int(sys.argv[4]) if len(sys.argv) > 4 else 15000
    use_streaming = '--streaming' in sys.argv

    # Load species categories
    print(f"Loading species categories from {input_file}...")
    categories = load_species_categories(input_file)

    if not categories:
        print("No categories found in the input file.")
        sys.exit(1)

    if max_species:
        categories = categories[:max_species]
        print(f"Limited to first {max_species} species for testing.")

    # Detect kingdom from first category
    kingdom = categories[0].get('kingdom', 'Unknown') if categories else 'Unknown'
    print(f"Found {len(categories)} species categories to process (Kingdom: {kingdom}).")

    # Initialize scraper with custom content limits
    scraper = WikipediaSpeciesScraper(max_content_chars=max_content_chars)

    # Choose scraping method
    if use_streaming:
        print("Using STREAMING mode (thread-safe, low memory, crash-resistant)")
        scraper.scrape_species_streaming(categories, output_file, max_workers=3, batch_size=50)
    else:
        print("Using BATCH mode (stores all results in memory)")
        results = scraper.scrape_species_batch(categories, max_workers=3, batch_size=50)
        scraper.save_results(results, output_file)

    # Final statistics
    print("\n" + "="*60)
    print("SCRAPING COMPLETE")
    print("="*60)
    scraper.print_stats()

    if not use_streaming:
        # Success analysis for batch mode
        successful_results = [r for r in results if not r.error]
        failed_results = [r for r in results if r.error]

        print(f"\nContent Analysis:")
        if successful_results:
            avg_content_length = sum(len(r.content) for r in successful_results) / len(successful_results)
            print(f"  Average content length: {avg_content_length:.0f} characters")

            with_images = sum(1 for r in successful_results if r.images)
            print(f"  Species with images: {with_images}/{len(successful_results)} ({with_images/len(successful_results)*100:.1f}%)")

        if failed_results:
            print(f"\nFailed species sample:")
            for result in failed_results[:5]:
                print(f"  - {result.scientific_name}: {result.error}")
    else:
        print(f"\nStreaming mode completed:")
        print(f"  Total species written to file: {scraper.species_written}")
        print(f"  Output file: {output_file}")
        print(f"  File can be used immediately for further processing")


if __name__ == "__main__":
    main()
