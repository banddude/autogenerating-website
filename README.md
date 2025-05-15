# AI-Powered Dynamic Website

This project is a Flask-based website that dynamically generates HTML content using AI (specifically, an OpenAI model) and caches it for future requests. It also features an AI-powered search functionality that creates new pages based on user queries.

## Features

*   **Dynamic Content Generation:** Pages are created on-the-fly by an AI if not already cached.
*   **Caching:** Generated content is cached to improve performance for subsequent requests to the same URL.
*   **AI Search:** Users can search for topics, and the AI will generate a new page and URL path for the search query.
*   **Configurable:** Site settings, like company name and base URL, are managed via `config.json`.
*   **Basic UI:** Includes a simple, responsive interface with dark/light mode.

## Technologies Used

*   **Backend:** Python, Flask
*   **AI:** OpenAI API
*   **Frontend:** HTML, CSS, JavaScript
*   **Caching:** Simple file-based caching

## Project Structure

```
autogenerating-website/
├── cache/                  # Stores cached HTML content
├── static/                 # Static assets (CSS, JS)
│   └── style.css
├── venv/                   # Python virtual environment
├── .gitignore
├── app.py                  # Main Flask application, routing, AI integration
├── config.json             # Configuration for site title, API keys (not included), etc.
├── index.html              # Main HTML template
├── page.py                 # Logic for AI content generation
└── README.md               # This file
```

## Setup and Installation

1.  **Clone the repository (if applicable).**
2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```
3.  **Install dependencies:**
    ```bash
    pip install Flask openai python-dotenv # (Assuming dotenv for API keys, though not explicitly shown in current files)
    # Add any other necessary packages to requirements.txt and install
    ```
    *(Initially, dependencies were managed implicitly. For a more robust setup, a `requirements.txt` should be created and used.)*

4.  **Configure `config.json`:**
    Create or update `config.json` with your desired settings:
    ```json
    {
        "company_name": "Your Company Name",
        "openai_api_key": "YOUR_OPENAI_API_KEY",
        "base_url": "http://localhost:3006/",
        "default_page_title": "My AI Site"
    }
    ```
    **Note:** Ensure your OpenAI API key is kept secure and not committed to version control. Consider using environment variables for sensitive data.

5.  **Run the Flask application:**
    ```bash
    flask run --host=0.0.0.0 --port=3006
    ```
    Or, if running `app.py` directly:
    ```bash
    python app.py
    ```
    The site should then be accessible at the `base_url` specified in your config (e.g., `http://localhost:3006/`).

## How It Works

1.  When a user navigates to a URL:
    *   `app.py` checks if the path is for a static asset (e.g., `favicon.ico`, CSS). If so, it attempts to serve it or returns a 404.
    *   It then checks if a cached version of the page exists in the `cache/` directory (e.g., `cache/requested-path_content.html`). If found, it's served.
    *   If not cached, `page.py`'s `generate_page_content_from_prompt` function is called. This function constructs a prompt for the OpenAI API based on the requested path, asking it to generate HTML content.
    *   The AI's response (HTML content) is cached and then returned to the user.
2.  **AI Search (`/ai_search` endpoint):**
    *   The user enters a query in the search bar.
    *   A POST request is sent to `/ai_search`.
    *   `page.py`'s `generate_page_data_from_search_query` function prompts the AI to generate a suitable URL path *and* HTML content for the query. The AI is instructed to return this in a specific JSON format: `{"url_path": "string", "content": "string_html_content"}`.
    *   The generated content is cached using the new URL path.
    *   The new path, content, and updated menu items are sent back to the client, which then updates the page dynamically.

## Configuration

*   `config.json`:
    *   `company_name`: Name of the company, displayed on the site.
    *   `openai_api_key`: Your OpenAI API key (essential for AI features).
    *   `base_url`: The base URL where the site is hosted.
    *   `default_page_title`: Default title for pages.
*   `app.py`:
    *   `SKIPPED_PATHS`: A list of URL paths (like `/favicon.ico`) that should not trigger AI content generation.

## Future Enhancements / To-Do

*   Implement `requirements.txt` for easier dependency management.
*   More robust error handling for API calls and file operations.
*   User authentication or admin panel for managing cache or site settings.
*   More sophisticated caching strategy (e.g., TTL, invalidation).
*   Allow AI to generate/select images or other media.
*   Improve prompt engineering for more consistent and higher-quality AI outputs.
*   Add unit and integration tests.

---
*This README was co-authored by Aiva, Mike Shaffer's AI assistant.* 