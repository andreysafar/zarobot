import requests
import json

class WebSearchTool:
    """
    A tool to perform web searches using the DuckDuckGo Instant Answer API.
    """
    def __init__(self):
        """
        Initializes the WebSearchTool.
        """
        self.api_url = "https://api.duckduckgo.com/"

    def execute(self, query: str) -> str:
        """
        Executes the web search for a given query.

        Args:
            query: The search query string.

        Returns:
            A formatted string with the search results, or an error message.
        """
        params = {
            'q': query,
            'format': 'json',
            'no_html': 1,
            'skip_disambig': 1
        }
        try:
            response = requests.get(self.api_url, params=params, timeout=5)
            response.raise_for_status()  # Raise an exception for bad status codes
            
            data = response.json()
            
            if data.get("AbstractText"):
                return f"Result for '{query}':\n{data['AbstractText']}\n\nSource: {data.get('AbstractURL', 'N/A')}"
            elif data.get("RelatedTopics"):
                results = []
                for topic in data["RelatedTopics"]:
                    if topic.get("Text"):
                        results.append(f"- {topic['Text']} ({topic.get('FirstURL', '')})")
                if results:
                    return f"Related topics for '{query}':\n" + "\n".join(results)
            
            return f"No direct answer found for '{query}'."

        except requests.exceptions.Timeout:
            return "The search request timed out."
        except requests.exceptions.HTTPError as e:
            return f"An HTTP error occurred: {e.response.status_code}"
        except requests.exceptions.RequestException as e:
            return f"An error occurred during the search: {e}"
        except json.JSONDecodeError:
            return "Failed to parse the search response." 