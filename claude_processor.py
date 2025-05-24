import os
import time
import json
import re
import anthropic
from utils import load_environment, logger, truncate_text

class ClaudeProcessor:
    """
    Class for processing and analyzing content using the Claude API.
    """
    
    def __init__(self):
        """Initialize the Claude client."""
        load_environment()
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-3-opus-20240229"
    
    def generate_summary(self, text, max_length=150):
        """
        Generate a concise summary of the given text.
        
        Args:
            text (str): The text to summarize
            max_length (int): Maximum length of the summary
            
        Returns:
            str: Concise summary of the text
        """
        if not text:
            return ""
            
        prompt = f"""
        Please provide a concise summary of the following text. The summary should be under {max_length} characters, 
        capture the main points, and be written in a clear, engaging style.
        
        Text to summarize:
        {text}
        """
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_length // 2,  # Estimate tokens from characters
                temperature=0.2,
                system="You are a helpful AI assistant that summarizes text concisely.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.content[0].text.strip()[:max_length]
        except anthropic.APIConnectionError as e:
            logger.error(f"Claude API Connection Error during summary generation: {e}", exc_info=True)
            return truncate_text(text, max_length)
        except anthropic.RateLimitError as e:
            logger.warning(f"Claude API Rate Limit Exceeded during summary generation: {e}")
            time.sleep(10)  # Simple backoff
            return truncate_text(text, max_length)
        except anthropic.APIStatusError as e:
            logger.error(f"Claude API Status Error during summary generation ({e.status_code}): {e.response}", exc_info=True)
            return truncate_text(text, max_length)
        except Exception as e:
            logger.error(f"Error generating summary for text starting with '{text[:50]}...': {e}", exc_info=True)
            return truncate_text(text, max_length)
    
    def categorize_content(self, item):
        """
        Categorize AI content into relevant topics and assign importance score.
        
        Args:
            item (dict): Content item with title, description, etc.
            
        Returns:
            dict: Item updated with categories and importance score
        """
        title = item.get('title', '')
        content_to_analyze = item.get('full_content_for_analysis') or item.get('description') or item.get('abstract', '')

        # Refined prompt with better instructions
        prompt = f"""
        Analyze this AI-related content:
        Title: {title}
        Content: {content_to_analyze[:4000]}

        Provide your analysis in a VALID JSON format with the following fields:
        1. "categories": A list of 1-3 relevant topic categories from this specific list: [Research, Applications, Business, Ethics, Policy, Tools, Tutorials, Hardware, Theory, Community].
        2. "importance_score": An integer from 1 (low) to 10 (high) assessing relevance for someone tracking general AI developments. Consider novelty, impact, and breadth of interest.
        3. "keywords": A list of 3-5 relevant keywords or keyphrases (can include named entities like 'GPT-4', 'TensorFlow').
        4. "suggested_short_summary": A very concise one-sentence summary (max 100 characters).

        JSON response should look like:
        {{
            "categories": ["Research", "Applications"],
            "importance_score": 8,
            "keywords": ["transformer architecture", "large language models", "AI ethics"],
            "suggested_short_summary": "A new paper explores transformer efficiency."
        }}
        """
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=512,
                temperature=0.1,  # Lower for more deterministic output
                system="You are an expert AI content analyst. Respond with VALID JSON only, adhering strictly to the requested schema. Do not include any explanatory text before or after the JSON object.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            text_response = response.content[0].text.strip()

            # More robust JSON extraction
            try:
                # Attempt to find JSON block even if there's leading/trailing text
                json_match = re.search(r'\{.*\}', text_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    analysis_data = json.loads(json_str)

                    item['categories'] = analysis_data.get('categories', ['Uncategorized'])
                    item['importance_score'] = analysis_data.get('importance_score', 5)
                    item['keywords'] = analysis_data.get('keywords', [])
                    # Use Claude's summary if provided and good, otherwise generate/truncate
                    claude_summary = analysis_data.get('suggested_short_summary')
                    if claude_summary:
                        item['summary'] = claude_summary
                    elif 'summary' not in item or not item['summary']:
                        item['summary'] = self.generate_summary(content_to_analyze, max_length=150)

                else:
                    logger.warning(f"Could not extract JSON from Claude response for item: {title}. Response: {text_response}")
                    self._set_default_analysis(item)
                return item
            except json.JSONDecodeError as json_e:
                logger.error(f"JSONDecodeError from Claude response for item: {title}. Error: {json_e}. Response: {text_response}", exc_info=True)
                self._set_default_analysis(item)
                return item

        except anthropic.APIConnectionError as e:
            logger.error(f"Claude API Connection Error during categorization: {e}", exc_info=True)
            self._set_default_analysis(item)
            return item
        except anthropic.RateLimitError as e:
            logger.warning(f"Claude API Rate Limit Exceeded during categorization: {e}")
            time.sleep(10)  # Simple backoff
            self._set_default_analysis(item)
            return item
        except anthropic.APIStatusError as e:
            logger.error(f"Claude API Status Error during categorization ({e.status_code}): {e.response}", exc_info=True)
            self._set_default_analysis(item)
            return item
        except Exception as e:
            logger.error(f"Error categorizing content '{title}': {e}", exc_info=True)
            self._set_default_analysis(item)
            return item

    def _set_default_analysis(self, item):
        """Set default analysis values when Claude processing fails."""
        item['categories'] = item.get('categories', ['Uncategorized'])
        item['importance_score'] = item.get('importance_score', 3)  # Default lower if analysis failed
        item['keywords'] = item.get('keywords', [])
        if 'summary' not in item or not item['summary']:
            content_to_summarize = item.get('full_content_for_analysis') or item.get('description') or item.get('abstract', '')
            item['summary'] = self.generate_summary(content_to_summarize, max_length=150)
    
    def batch_process(self, items):
        """
        Process a batch of content items - summarize and categorize.
        
        Args:
            items (list): List of content items (dicts)
            
        Returns:
            list: Processed items
        """
        processed_items = []
        
        if not self.api_key:
            logger.warning("Anthropic API key not set. Skipping Claude processing.")
            for item in items:
                processed_item = item.copy()
                content_to_summarize = processed_item.get('description', processed_item.get('abstract', ''))
                processed_item['summary'] = truncate_text(content_to_summarize, 150)
                processed_item['categories'] = ['Uncategorized']
                processed_item['importance_score'] = 5
                processed_item['keywords'] = []
                processed_items.append(processed_item)
            return processed_items

        for item in items:
            processed_item = item.copy()

            # Prepare full content for analysis if possible (e.g., from blog/news scraper)
            content_for_analysis = processed_item.get('full_text_content') or \
                                   processed_item.get('description') or \
                                   processed_item.get('abstract', '')
            processed_item['full_content_for_analysis'] = content_for_analysis

            # Categorize and get initial summary from Claude
            processed_item = self.categorize_content(processed_item)

            # Ensure summary exists, even if categorization failed or didn't provide one
            if 'summary' not in processed_item or not processed_item['summary']:
                processed_item['summary'] = self.generate_summary(content_for_analysis, max_length=150)

            processed_items.append(processed_item)
            
        return processed_items