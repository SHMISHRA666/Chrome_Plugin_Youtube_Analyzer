# YouTube Content Analyzer - Agentic AI Chrome Extension

An AI-powered Chrome extension that analyzes YouTube content, suggests improvements, and helps creators optimize their videos.

## Features

- **Trend Analysis**: Scrapes trending videos in your niche and analyzes key metrics
- **Content Generation**: AI-powered video scripts and thumbnail suggestions
- **SEO Optimization**: Analyzes titles, descriptions, and keywords for better visibility
- **Performance Tracking**: Tracks video metrics and suggests improvements

## Setup Instructions

### 1. Backend Setup

1. Make sure you have Python 3.8+ installed
2. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file from the `.env.example` template and add your Gemini API key:
   ```
   GEMINI_API_KEY=your-api-key-here
   ```
4. Run the Flask backend:
   ```
   python app.py
   ```

### 2. Chrome Extension Setup

1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode" (toggle in the top-right corner)
3. Click "Load unpacked" and select the extension folder (containing manifest.json)
4. The extension should now be installed and visible in your Chrome toolbar

## Usage

1. Click on the extension icon to open the main interface
2. Navigate to the different tabs:
   - **Trending Analysis**: Enter your niche to analyze trending videos
   - **Content Generation**: Input topics to get AI-generated video ideas and scripts
   - **Performance**: Enter a YouTube video URL to analyze its performance

3. You can also visit any YouTube video page, and you'll see an "Analyze Video" button below the video

## Agentic AI Flow

This extension demonstrates agentic AI capabilities by:

1. Using Gemini API with custom tools that extend its capabilities
2. Implementing an iterative process where:
   - User input → LLM response → Tool call → Tool result → LLM final response
3. Maintaining conversation context throughout the interaction

## Technologies Used

- **Frontend**: HTML, CSS, JavaScript (Chrome Extension)
- **Backend**: Python, Flask
- **AI**: Google's Gemini API

## Notes

- This is a demonstration project showing agentic AI principles
- The backend uses mock data for demo purposes; in a production implementation, you would integrate with actual YouTube API services 