import os
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from dotenv import load_dotenv
import re
import time
from typing import Dict, List, Any, Optional
import logging
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Clear existing handlers
logger.handlers = []

# Simple console handler
console_handler = logging.StreamHandler()
logger.addHandler(console_handler)

# Flow tracking variables
flow_steps = {}
GLOBAL_TOOL_SESSION = "tool_exec"  # Default session ID for direct tool execution

def log_flow_step(session_id, step_type, message=""):
    """Log a step in the flow with minimal formatting"""
    if session_id not in flow_steps:
        flow_steps[session_id] = 1
    
    step_num = flow_steps[session_id]
    
    # Color codes
    BLUE = '\033[94m'    # Query
    GREEN = '\033[92m'   # LLM
    YELLOW = '\033[93m'  # Tool
    CYAN = '\033[96m'    # Result
    RED = '\033[91m'     # Error
    RESET = '\033[0m'    # Reset
    
    color = BLUE
    if step_type == "LLM":
        color = GREEN
    elif step_type == "TOOL":
        color = YELLOW
    elif step_type == "RESULT":
        color = CYAN
    elif step_type == "ERROR":
        color = RED
    
    # Format the step in the pattern: Query1→LLM→Tool→Result
    formatted_step = f"{color}{step_type}{step_num}{RESET}"
    
    # Increment step counter if this is the start of a new sequence
    if step_type == "QUERY":
        flow_steps[session_id] += 1
    
    # Log the formatted message
    if message:
        logger.info(f"[{session_id}] {formatted_step} → {message[:100]}{'...' if len(message) > 100 else ''}")
    else:
        logger.info(f"[{session_id}] {formatted_step}")

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Get API keys from environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your-api-key-here")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "your-youtube-api-key-here")

# Initialize Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Initialize YouTube API client
def get_youtube_client():
    return build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

# Store conversation history for each session
conversation_history = {}

# Root endpoint for health check
@app.route('/', methods=['GET'])
def health_check():
    """
    Simple health check endpoint to confirm the API is running
    """
    youtube_api_configured = bool(YOUTUBE_API_KEY and YOUTUBE_API_KEY != "your-youtube-api-key-here")
    youtube_api_working = False
    
    # Test YouTube API connection if configured
    if youtube_api_configured:
        try:
            youtube = get_youtube_client()
            # Try a simple search query
            response = youtube.videos().list(
                part="snippet",
                chart="mostPopular",
                maxResults=1
            ).execute()
            if response and "items" in response:
                youtube_api_working = True
        except Exception as e:
            logger.error(f"YouTube API test failed: {str(e)}")
    
    return jsonify({
        "status": "ok",
        "message": "YouTube Content Analyzer API is running",
        "gemini_api_configured": bool(GEMINI_API_KEY and GEMINI_API_KEY != "your-api-key-here"),
        "youtube_api_configured": youtube_api_configured,
        "youtube_api_working": youtube_api_working
    })

# Define Tool classes for Agentic AI
class Tool:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    def execute(self, **kwargs):
        raise NotImplementedError("Tool execution not implemented")

class YouTubeScraperTool(Tool):
    def __init__(self):
        super().__init__(
            name="youtube_scraper",
            description="Scrapes trending videos from YouTube based on a niche keyword"
        )
    
    def execute(self, niche: str) -> Dict[str, Any]:
        """Get trending videos from YouTube based on niche keyword"""
        logger.info(f"Searching YouTube videos for niche: {niche}")
        log_flow_step(GLOBAL_TOOL_SESSION, "TOOL", f"YouTubeScraperTool executing with niche: {niche}")
        
        try:
            youtube = get_youtube_client()
            
            # Search for videos related to the niche
            log_flow_step(GLOBAL_TOOL_SESSION, "TOOL", f"Searching YouTube for videos related to: {niche}")
            search_response = youtube.search().list(
                q=niche,
                part="snippet",
                type="video",
                maxResults=10,
                order="viewCount",  # Sort by view count to get trending videos
                relevanceLanguage="en"
            ).execute()
            
            video_ids = [item['id']['videoId'] for item in search_response['items']]
            log_flow_step(GLOBAL_TOOL_SESSION, "RESULT", f"Found {len(video_ids)} video IDs")
            
            # Get video statistics (views, likes, etc.)
            videos_response = youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=",".join(video_ids)
            ).execute()
            
            trending_videos = []
            for video in videos_response['items']:
                # Extract keywords from tags if available
                keywords = video['snippet'].get('tags', [])
                if not keywords:
                    # If no tags, extract keywords from title and description
                    all_text = f"{video['snippet']['title']} {video['snippet']['description']}"
                    keywords = [word.lower() for word in re.findall(r'\b\w{4,}\b', all_text)]
                    keywords = list(set(keywords))[:5]  # Take up to 5 unique keywords
                
                trending_videos.append({
                    "title": video['snippet']['title'],
                    "views": video['statistics'].get('viewCount', '0'),
                    "likes": video['statistics'].get('likeCount', '0'),
                    "channel": video['snippet']['channelTitle'],
                    "video_id": video['id'],
                    "thumbnail": video['snippet']['thumbnails']['high']['url'],
                    "keywords": keywords,
                    "description": video['snippet']['description'],
                    "published_at": video['snippet']['publishedAt'],
                    "duration": video['contentDetails']['duration']
                })
            
            return {
                "trending_videos": trending_videos
            }
            
        except HttpError as e:
            logger.error(f"YouTube API error: {e}")
            # Fallback to mock data if API fails
            return self._mock_response(niche)
    
    def _mock_response(self, niche: str) -> Dict[str, Any]:
        """Provide mock data as fallback"""
        logger.warning(f"Using mock data for niche: {niche}")
        return {
            "trending_videos": [
                {
                    "title": f"Top 10 {niche.capitalize()} Tips for Beginners",
                    "views": "1200000",
                    "likes": "45000",
                    "channel": f"{niche.capitalize()} Expert",
                    "video_id": "dQw4w9WgXcQ",  # Placeholder ID
                    "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
                    "keywords": [niche, "beginners", "tips", "tutorial"],
                    "description": f"Learn the best {niche} tips and tricks in this comprehensive guide.",
                    "published_at": "2023-01-01T00:00:00Z",
                    "duration": "PT10M30S"
                },
                # Additional mock videos as before...
            ]
        }

class ContentAnalyzerTool(Tool):
    def __init__(self):
        super().__init__(
            name="content_analyzer",
            description="Analyzes video titles, descriptions, and keywords for SEO optimization"
        )
    
    def execute(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze content for SEO optimization"""
        title = content.get('title', '')
        logger.info(f"Analyzing content: {title}")
        log_flow_step(GLOBAL_TOOL_SESSION, "TOOL", f"ContentAnalyzerTool analyzing: {title[:50]}...")
        
        description = content.get('description', '')
        provided_keywords = content.get('keywords', [])
        
        # Extract keywords from title and description
        log_flow_step(GLOBAL_TOOL_SESSION, "TOOL", f"Extracting keywords from title and description")
        all_text = f"{title} {description}"
        extracted_keywords = re.findall(r'\b\w{4,}\b', all_text.lower())
        extracted_keywords = [keyword for keyword in extracted_keywords 
                              if keyword not in ['this', 'that', 'with', 'from', 'have', 'what', 'your']]
        
        # Combine provided and extracted keywords
        keywords = list(set(provided_keywords + extracted_keywords))
        log_flow_step(GLOBAL_TOOL_SESSION, "RESULT", f"Found {len(keywords)} unique keywords")
        
        # Calculate keyword frequency
        keyword_freq = {}
        for keyword in keywords:
            # Check if keyword appears in title (higher weight)
            title_count = title.lower().count(keyword.lower()) * 2
            # Check if keyword appears in description
            desc_count = description.lower().count(keyword.lower())
            keyword_freq[keyword] = title_count + desc_count
        
        # Sort keywords by frequency
        sorted_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)
        top_keywords = sorted_keywords[:10] if sorted_keywords else []
        
        # Calculate title effectiveness
        title_effectiveness = self._calculate_title_effectiveness(title)
        
        # Calculate description effectiveness
        description_effectiveness = self._calculate_description_effectiveness(description)
        
        # Overall SEO score (weighted average)
        seo_score = int(title_effectiveness * 0.5 + description_effectiveness * 0.3 + min(len(top_keywords) * 7, 20))
        
        return {
            "seo_score": seo_score,
            "title_effectiveness": title_effectiveness,
            "description_effectiveness": description_effectiveness,
            "top_keywords": [k for k, v in top_keywords],
            "keyword_density": {k: v for k, v in top_keywords},
            "improvement_suggestions": self._generate_improvement_suggestions(
                title, description, title_effectiveness, description_effectiveness, top_keywords
            )
        }
    
    def _calculate_title_effectiveness(self, title: str) -> int:
        """Calculate title effectiveness score (0-100)"""
        score = 50  # Base score
        
        # Length factors (ideal: 40-60 characters)
        title_length = len(title)
        if 40 <= title_length <= 60:
            score += 20
        elif 30 <= title_length <= 70:
            score += 10
        
        # Engagement factors
        if any(word in title.lower() for word in ['how', 'why', 'what']):
            score += 10  # Question/explanation titles perform well
        
        if any(word in title.lower() for word in ['top', 'best', 'ultimate', 'complete', 'guide']):
            score += 5  # Superlatives/guide indicators
        
        if re.search(r'\d+', title):
            score += 5  # Numbers in title
        
        # Normalize score
        return min(max(score, 0), 100)
    
    def _calculate_description_effectiveness(self, description: str) -> int:
        """Calculate description effectiveness score (0-100)"""
        score = 50  # Base score
        
        # Length factors
        desc_length = len(description)
        if desc_length > 250:
            score += 20  # Good detailed description
        elif desc_length > 100:
            score += 10  # Decent description
        
        # Content factors
        if 'http' in description or 'www.' in description:
            score += 10  # Contains links
        
        if re.search(r'subscribe|follow|like|comment', description, re.IGNORECASE):
            score += 5  # Call to action
        
        if re.search(r'timestamps|(\d+:\d+)', description, re.IGNORECASE):
            score += 10  # Contains timestamps
        
        # Normalize score
        return min(max(score, 0), 100)
    
    def _generate_improvement_suggestions(self, title: str, description: str, 
                                         title_score: int, desc_score: int,
                                         top_keywords: List) -> List[str]:
        """Generate improvement suggestions based on content analysis"""
        suggestions = []
        
        # Title suggestions
        if title_score < 70:
            if len(title) < 30:
                suggestions.append("Make your title longer (40-60 characters is ideal)")
            elif len(title) > 70:
                suggestions.append("Consider shortening your title (40-60 characters is ideal)")
            
            if not any(word in title.lower() for word in ['how', 'why', 'what', '?']):
                suggestions.append("Consider using question formats in your title")
            
            if not re.search(r'\d+', title):
                suggestions.append("Consider adding numbers to your title (e.g., '7 Ways to...')")
        
        # Description suggestions
        if desc_score < 70:
            if len(description) < 100:
                suggestions.append("Add more details to your description (aim for 250+ characters)")
            
            if not ('http' in description or 'www.' in description):
                suggestions.append("Include relevant links in your description")
            
            if not re.search(r'subscribe|follow|like|comment', description, re.IGNORECASE):
                suggestions.append("Add a clear call-to-action in your description")
            
            if not re.search(r'timestamps|(\d+:\d+)', description, re.IGNORECASE):
                suggestions.append("Add timestamps for longer videos to improve user experience")
        
        # Keyword suggestions
        if len(top_keywords) < 5:
            suggestions.append("Use more relevant keywords in your title and description")
        
        # Add general suggestions
        suggestions.extend([
            "Use trending keywords in your niche for better discoverability",
            "Include a clear video category/topic in the first few words of your title",
            "Use more specific and unique tags that accurately describe your content"
        ])
        
        return suggestions

class ContentGeneratorTool(Tool):
    def __init__(self):
        super().__init__(
            name="content_generator",
            description="Generates video script ideas and thumbnails based on trending topics"
        )
    
    def execute(self, prompt: str, trending_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate content ideas based on prompt and trending data"""
        logger.info(f"Generating content based on prompt: {prompt}")
        log_flow_step(GLOBAL_TOOL_SESSION, "TOOL", f"ContentGeneratorTool generating ideas for: {prompt}")
        
        try:
            # Use Gemini to generate unique content ideas for this specific topic
            model = genai.GenerativeModel('gemini-2.0-flash')
            log_flow_step(GLOBAL_TOOL_SESSION, "TOOL", f"Calling Gemini model to generate content ideas")
            
            generation_prompt = f"""
            Generate unique YouTube video content ideas for the topic: "{prompt}".
            
            Your response should be structured as a valid JSON object with the following format:
            {{
                "video_ideas": [
                    {{
                        "title": "Engaging title for the video",
                        "hook": "Attention-grabbing hook to start the video",
                        "outline": ["Section 1 (0:00-2:00)", "Section 2 (2:00-5:00)", "Section 3 (5:00-8:00)", "..."]
                    }},
                    // Include 2-3 unique video ideas
                ],
                "thumbnail_ideas": [
                    "Description of thumbnail idea 1",
                    "Description of thumbnail idea 2",
                    "Description of thumbnail idea 3"
                ],
                "script_template": "Detailed script template specific to this topic, including intro, main points, and conclusion"
            }}
            
            Ensure your ideas are:
            1. Specific to the "{prompt}" topic
            2. On-trend and likely to engage viewers
            3. Structured for maximum retention
            4. Different from each other to provide variety
            
            The script template should be detailed and include placeholders for key information.
            """
            
            # Generate response
            response = model.generate_content(generation_prompt)
            response_text = response.text
            log_flow_step(GLOBAL_TOOL_SESSION, "RESULT", f"Gemini generated content response of {len(response_text)} characters")
            
            # Extract JSON content
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                content_json = json_match.group(1)
            else:
                # If not in code block, try to extract JSON directly
                json_pattern = r'({[\s\S]*})'
                json_match = re.search(json_pattern, response_text)
                if json_match:
                    content_json = json_match.group(1)
                else:
                    content_json = response_text
            
            # Clean the JSON string
            content_json = content_json.replace('\n', ' ').replace('```', '')
            
            try:
                # Parse the JSON response
                content_data = json.loads(content_json)
                
                # Ensure all required fields are present
                if "video_ideas" not in content_data or "thumbnail_ideas" not in content_data or "script_template" not in content_data:
                    logger.warning("Missing required fields in content generation response")
                    # Supplement with partial data if needed
                    if "video_ideas" not in content_data:
                        content_data["video_ideas"] = [{
                            "title": f"Complete Guide to {prompt}",
                            "hook": f"Discover the secrets of {prompt} that experts don't want you to know",
                            "outline": [
                                "Introduction (0:00-1:30)",
                                f"{prompt} Fundamentals (1:30-4:00)",
                                "Advanced Techniques (4:00-10:00)",
                                "Implementation Steps (10:00-15:00)",
                                "Conclusion (15:00-16:00)"
                            ]
                        }]
                    
                    if "thumbnail_ideas" not in content_data:
                        content_data["thumbnail_ideas"] = [
                            f"Bold text showcasing '{prompt}' with contrasting background",
                            f"Before/after results from using {prompt} techniques",
                            f"Question headline: 'Is {prompt} right for you?' with arrow pointing to benefit"
                        ]
                    
                    if "script_template" not in content_data:
                        content_data["script_template"] = f"""
                        INTRO:
                        - Hook viewers with an interesting fact about {prompt}
                        - Introduce yourself and your experience with {prompt}
                        - Overview of what viewers will learn
                        
                        MAIN CONTENT:
                        - Section 1: Explain the basics of {prompt}
                        - Section 2: Common challenges with {prompt}
                        - Section 3: Step-by-step technique or solution
                        - Section 4: Real-world examples or case studies
                        
                        CONCLUSION:
                        - Recap key points
                        - Call to action
                        - Tease upcoming related content
                        """
                
                return content_data
                
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing content generation JSON: {e}")
                # Fall back to simplified format with topic-specific content
                return self._create_fallback_content(prompt)
                
        except Exception as e:
            logger.error(f"Error in content generation: {e}")
            # Fall back to simplified format with topic-specific content
            return self._create_fallback_content(prompt)
    
    def _create_fallback_content(self, topic: str) -> Dict[str, Any]:
        """Create fallback content specific to the topic if AI generation fails"""
        return {
            "video_ideas": [
                {
                    "title": f"7 Essential {topic.capitalize()} Techniques for 2023",
                    "hook": f"Did you know 80% of experts use these {topic} strategies?",
                    "outline": [
                        "Introduction (0:00-1:30)",
                        f"Common {topic} mistakes (1:30-4:00)",
                        f"The 7 key {topic} techniques (4:00-12:00)",
                        "Implementation steps (12:00-15:00)",
                        "Results you can expect (15:00-17:00)",
                        "Call to action (17:00-18:00)"
                    ]
                },
                {
                    "title": f"The Ultimate Beginner's Guide to {topic.capitalize()}",
                    "hook": f"This simple {topic} approach changed everything for me...",
                    "outline": [
                        "My story and struggle with " + topic + " (0:00-2:30)",
                        "The breakthrough moment (2:30-4:00)",
                        f"Step-by-step {topic} methodology (4:00-10:00)",
                        "Avoiding common pitfalls (10:00-13:00)",
                        "Advanced tips for faster results (13:00-16:00)",
                        "Next steps and resources (16:00-18:00)"
                    ]
                }
            ],
            "thumbnail_ideas": [
                f"Bold text overlay with '{topic}' and shocked face reaction",
                f"Before/after split screen showing {topic} results",
                f"Question headline: 'Is your {topic} approach wrong?' with arrow pointing to solution"
            ],
            "script_template": f"""INTRO:
Hook viewers with a surprising stat about {topic}
Teaser of what they'll learn about {topic}

MAIN CONTENT:
Point 1: Current state of {topic}
Point 2: Common problems with {topic} approaches
Point 3-5: Detailed steps for mastering {topic}

CONCLUSION:
Summary of {topic} benefits
Call to action
Teaser for next video on advanced {topic} techniques"""
        }

class PerformanceTrackerTool(Tool):
    def __init__(self):
        super().__init__(
            name="performance_tracker",
            description="Tracks video performance metrics and suggests improvements"
        )
    
    def execute(self, video_url: str) -> Dict[str, Any]:
        """Track performance of a video based on URL"""
        logger.info(f"Tracking performance for video: {video_url}")
        log_flow_step(GLOBAL_TOOL_SESSION, "TOOL", f"PerformanceTrackerTool analyzing video: {video_url}")
        
        # Extract video ID from URL
        video_id = None
        if "youtube.com" in video_url:
            video_id = video_url.split("v=")[1].split("&")[0] if "v=" in video_url else None
        elif "youtu.be" in video_url:
            video_id = video_url.split("/")[-1]
        
        if not video_id:
            log_flow_step(GLOBAL_TOOL_SESSION, "ERROR", f"Invalid YouTube URL: {video_url}")
            return {"error": "Invalid YouTube URL"}
        
        log_flow_step(GLOBAL_TOOL_SESSION, "RESULT", f"Extracted video ID: {video_id}")
        
        try:
            youtube = get_youtube_client()
            
            # Get video statistics
            video_response = youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=video_id
            ).execute()
            
            if not video_response['items']:
                return {"error": "Video not found"}
            
            video = video_response['items'][0]
            
            # Get comments (most recent)
            try:
                comments_response = youtube.commentThreads().list(
                    part="snippet",
                    videoId=video_id,
                    order="relevance",
                    maxResults=20
                ).execute()
                
                comments = []
                for item in comments_response.get('items', []):
                    comment = item['snippet']['topLevelComment']['snippet']
                    comments.append({
                        "author": comment['authorDisplayName'],
                        "text": comment['textDisplay'],
                        "likes": comment['likeCount'],
                        "published_at": comment['publishedAt']
                    })
            except HttpError:
                # Comments might be disabled
                comments = []
            
            # Process data
            stats = video['statistics']
            
            # Calculate engagement rate (likes + comments) / views
            views = int(stats.get('viewCount', 0))
            likes = int(stats.get('likeCount', 0))
            comment_count = int(stats.get('commentCount', 0))
            
            engagement_rate = ((likes + comment_count) / views) * 100 if views > 0 else 0
            
            # We can't get real audience retention from the API
            # This would require YouTube Analytics API with channel owner auth
            
            # Generate improvement suggestions based on engagement metrics
            suggestions = []
            
            if engagement_rate < 5:
                suggestions.append("Improve audience engagement by asking questions in the video")
                suggestions.append("Encourage viewers to like and comment")
            
            if likes / views < 0.05 and views > 100:
                suggestions.append("Work on more compelling content to increase like ratio")
            
            if comment_count < 10 and views > 1000:
                suggestions.append("Add provocative questions or ask for opinions to increase comments")
            
            # Add generic suggestions
            suggestions.extend([
                "Add cards and end screens for better retention",
                "Respond to more comments to boost engagement",
                "Create follow-up content addressing viewer questions"
            ])
            
            # Create simulated audience retention data
            # (This cannot be retrieved from the public API)
            audience_retention = [
                {"segment": "0-30 seconds", "retention": "95%"},
                {"segment": "30-60 seconds", "retention": "87%"},
                {"segment": "1-2 minutes", "retention": "76%"},
                {"segment": "2-5 minutes", "retention": "65%"},
                {"segment": "5+ minutes", "retention": "43%"}
            ]
            
            return {
                "title": video['snippet']['title'],
                "published_at": video['snippet']['publishedAt'],
                "views": stats.get('viewCount', '0'),
                "likes": stats.get('likeCount', '0'),
                "dislikes": "Not available",  # API no longer provides dislike counts
                "comments": stats.get('commentCount', '0'),
                "duration": video['contentDetails']['duration'],
                "engagement_rate": f"{engagement_rate:.2f}%",
                "recent_comments": comments[:5] if comments else [],
                "audience_retention": audience_retention,  # Simulated
                "improvement_suggestions": suggestions
            }
            
        except HttpError as e:
            logger.error(f"YouTube API error: {e}")
            # Fallback to mock data
            return self._mock_response(video_id)
    
    def _mock_response(self, video_id: str) -> Dict[str, Any]:
        """Provide mock data as fallback"""
        logger.warning(f"Using mock data for video ID: {video_id}")
        return {
            "views": "12,345",
            "watch_time": "45,678 minutes",
            "average_view_duration": "4:32",
            "likes": "1,234",
            "comments": "456",
            "ctr": "4.8%",
            "audience_retention": [
                {"segment": "0-30 seconds", "retention": "95%"},
                {"segment": "30-60 seconds", "retention": "87%"},
                {"segment": "1-2 minutes", "retention": "76%"},
                {"segment": "2-5 minutes", "retention": "65%"},
                {"segment": "5+ minutes", "retention": "43%"}
            ],
            "improvement_suggestions": [
                "Add a stronger hook in the first 30 seconds",
                "Create more engaging content between 2-5 minute mark",
                "Add cards and end screens for better retention",
                "Respond to more comments to boost engagement",
                "Create follow-up content based on most-watched segments"
            ]
        }

# Initialize tools
available_tools = {
    "youtube_scraper": YouTubeScraperTool(),
    "content_analyzer": ContentAnalyzerTool(),
    "content_generator": ContentGeneratorTool(),
    "performance_tracker": PerformanceTrackerTool()
}

# Function to handle agentic LLM calls
def call_gemini(prompt, conversation_id=None, tool_results=None):
    """
    Call Gemini API with prompt and handle tool calls
    
    Args:
        prompt (str): The user prompt
        conversation_id (str): ID to track conversation history
        tool_results (dict): Results from previous tool calls
        
    Returns:
        dict: Response from Gemini with potential tool calls
    """
    # Log query step
    log_flow_step(conversation_id, "QUERY", prompt)
    
    # Get or create conversation history
    if conversation_id not in conversation_history:
        conversation_history[conversation_id] = []
    
    # Add tool results to history if provided
    if tool_results:
        log_flow_step(conversation_id, "RESULT", str(tool_results))
        conversation_history[conversation_id].append({
            "role": "function",
            "parts": [{"text": json.dumps(tool_results)}]
        })
    
    # Add user prompt to history
    conversation_history[conversation_id].append({
        "role": "user",
        "parts": [{"text": prompt}]
    })
    
    try:
        # Construct full conversation context
        full_context = ""
        for message in conversation_history[conversation_id]:
            role = message["role"]
            content = message["parts"][0]["text"]
            full_context += f"{role.upper()}: {content}\n\n"
        
        # Add tool descriptions to the prompt
        tools_description = "You have access to the following tools:\n"
        for tool_name, tool in available_tools.items():
            tools_description += f"- {tool_name}: {tool.description}\n"
        
        full_prompt = f"{tools_description}\n\n{full_context}\n\nIf you need to use a tool, respond with:\nTOOL: <tool_name>\nPARAMS: {{'param1': 'value1', 'param2': 'value2'}}\n\nOtherwise respond directly to the user."
        
        # Call Gemini API
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(full_prompt)
        response_text = response.text
        
        # Log LLM response step
        log_flow_step(conversation_id, "LLM", response_text)
        
        # Check if the response includes a tool call
        if "TOOL:" in response_text:
            # Extract tool name and parameters
            tool_pattern = r"TOOL: (\w+)\nPARAMS: ({.*})"
            tool_match = re.search(tool_pattern, response_text, re.DOTALL)
            
            if tool_match:
                tool_name = tool_match.group(1)
                tool_params_str = tool_match.group(2)
                
                # Log tool call step
                log_flow_step(conversation_id, "TOOL", f"{tool_name}: {tool_params_str}")
                
                try:
                    # Process tool parameters as before...
                    # Replace single quotes with double quotes for JSON parsing
                    tool_params_str = tool_params_str.replace("'", '"')
                    
                    # Fix issue with double quotes in URLs - improved pattern to handle more edge cases
                    # First pattern: Fix cases with ""https" format
                    tool_params_str = re.sub(r'": ""(https?)"://', r'": "\1://', tool_params_str)
                    
                    # Second pattern: Fix cases where URL is surrounded by multiple quotes
                    tool_params_str = re.sub(r'": "+"(https?://[^"]+)"+"', r'": "\1"', tool_params_str)
                    
                    # Third pattern: Fix any remaining URL formatting issues
                    tool_params_str = re.sub(r'": +"([^"]+)"', r'": "\1"', tool_params_str)
                    
                    # Ensure all key names have double quotes
                    tool_params_str = re.sub(r'(\w+):', r'"\1":', tool_params_str)
                    
                    # Log the cleaned parameters for debugging
                    logger.info(f"Cleaned parameters: {tool_params_str}")
                    
                    try:
                        tool_params = json.loads(tool_params_str)
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON parse error: {e}")
                        # Try a more aggressive cleanup approach for URLs
                        if "video_url" in tool_params_str:
                            # Extract the URL using regex
                            url_match = re.search(r'https?://[^\s"]+', tool_params_str)
                            if url_match:
                                url = url_match.group(0)
                                # Create a clean parameter dictionary
                                tool_params = {"video_url": url}
                                logger.info(f"Fallback: extracted URL {url} from parameters")
                            else:
                                raise
                        else:
                            raise
                    
                    # Store the assistant's response
                    conversation_history[conversation_id].append({
                        "role": "assistant",
                        "parts": [{"text": response_text}]
                    })
                    
                    return {
                        "response": response_text,
                        "tool_call": {
                            "name": tool_name,
                            "parameters": tool_params
                        }
                    }
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse tool parameters: {tool_params_str}")
        
        # If no tool call, just return the response
        conversation_history[conversation_id].append({
            "role": "assistant",
            "parts": [{"text": response_text}]
        })
        
        return {
            "response": response_text,
            "tool_call": None
        }
        
    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}")
        return {
            "response": f"Error: {str(e)}",
            "tool_call": None
        }

# Function to execute tool calls
def execute_tool_call(tool_call):
    """
    Execute a tool call and return results
    
    Args:
        tool_call (dict): Tool call details with name and parameters
        
    Returns:
        dict: Results from tool execution
    """
    tool_name = tool_call["name"]
    tool_params = tool_call["parameters"]
    
    if tool_name not in available_tools:
        log_flow_step(GLOBAL_TOOL_SESSION, "ERROR", f"Tool '{tool_name}' not found")
        return {"error": f"Tool '{tool_name}' not found"}
    
    try:
        tool = available_tools[tool_name]
        result = tool.execute(**tool_params)
        return {tool_name: result}
    except Exception as e:
        log_flow_step(GLOBAL_TOOL_SESSION, "ERROR", f"Error executing tool {tool_name}: {e}")
        logger.error(f"Error executing tool {tool_name}: {e}")
        return {"error": f"Tool execution error: {str(e)}"}

# API routes
@app.route('/analyze_trending', methods=['POST'])
def analyze_trending():
    """
    Analyze trending videos in a specific niche
    
    Request:
    {
        "niche": "string",  // Required: the niche/keyword to analyze
        "session_id": "string"  // Optional: session ID for conversation history
    }
    """
    data = request.json
    
    if not data or "niche" not in data:
        return jsonify({"error": "Missing required parameter: niche"}), 400
    
    niche = data["niche"]
    session_id = data.get("session_id", "default")
    
    try:
        # Initialize the flow for this session
        flow_steps[session_id] = 1
        
        # Log initial query
        log_flow_step(session_id, "QUERY", f"Analyze trending videos for: {niche}")
        
        # Use the YouTube scraper tool
        yt_scraper = available_tools["youtube_scraper"]
        log_flow_step(session_id, "TOOL", f"youtube_scraper(niche={niche})")
        trending_data = yt_scraper.execute(niche=niche)
        log_flow_step(session_id, "RESULT", f"Found {len(trending_data.get('trending_videos', []))} videos")
        
        if not trending_data or "trending_videos" not in trending_data:
            return jsonify({
                "error": "Failed to fetch trending videos",
                "message": "Could not retrieve trending videos for the specified niche"
            }), 500
        
        # Use the content analyzer tool to analyze the trending videos
        content_analyzer = available_tools["content_analyzer"]
        analysis_results = []
        
        for idx, video in enumerate(trending_data["trending_videos"]):
            # Format numbers for display
            if 'views' in video and video['views'].isdigit():
                view_count = int(video['views'])
                if view_count >= 1000000:
                    video['views_formatted'] = f"{view_count/1000000:.1f}M"
                elif view_count >= 1000:
                    video['views_formatted'] = f"{view_count/1000:.1f}K"
                else:
                    video['views_formatted'] = str(view_count)
            
            if 'likes' in video and video['likes'].isdigit():
                like_count = int(video['likes'])
                if like_count >= 1000000:
                    video['likes_formatted'] = f"{like_count/1000000:.1f}M"
                elif like_count >= 1000:
                    video['likes_formatted'] = f"{like_count/1000:.1f}K"
                else:
                    video['likes_formatted'] = str(like_count)
            
            # Analyze each video
            log_flow_step(session_id, "TOOL", f"content_analyzer({video.get('title', '')[:30]}...)")
            analysis = content_analyzer.execute(video)
            log_flow_step(session_id, "RESULT", f"SEO score: {analysis.get('seo_score', 'N/A')}")
            
            # Combine video data with analysis
            combined_result = {
                "video": video,
                "analysis": analysis
            }
            
            analysis_results.append(combined_result)
        
        # Generate summary with Gemini
        system_prompt = f"""
        You're analyzing YouTube trends in the '{niche}' niche.
        Based on the trending videos and their metrics, provide:
        1. Common patterns in successful titles
        2. Key topics that seem to be popular
        3. A brief summary of what content performs well
        Keep it concise and actionable for content creators.
        """
        
        user_prompt = json.dumps(analysis_results, indent=2)
        
        # Call Gemini for insights
        log_flow_step(session_id, "QUERY", "Generate summary from analysis")
        ai_summary = call_gemini(
            prompt=user_prompt,
            conversation_id=session_id,
            tool_results={"system_prompt": system_prompt}
        )
        
        log_flow_step(session_id, "RESULT", "Analysis complete")
        
        return jsonify({
            "success": True,
            "niche": niche,
            "trending_videos": trending_data["trending_videos"],
            "analysis_results": analysis_results,
            "ai_summary": ai_summary
        })
    
    except Exception as e:
        log_flow_step(session_id, "ERROR", str(e))
        logger.error(f"Error in /analyze_trending: {str(e)}")
        return jsonify({
            "error": "Analysis failed",
            "message": str(e)
        }), 500

@app.route('/generate_content', methods=['POST'])
def generate_content():
    """
    Generate content ideas for video creation
    
    Request:
    {
        "prompt": "string",  // Required: the content topic/idea
        "session_id": "string"  // Optional: session ID for conversation history
    }
    """
    data = request.json
    
    if not data or "prompt" not in data:
        return jsonify({"error": "Missing required parameter: prompt"}), 400
    
    prompt = data["prompt"]
    session_id = data.get("session_id", "default")
    
    try:
        # Initialize flow for this session
        flow_steps[session_id] = 1
        
        # Log initial query
        log_flow_step(session_id, "QUERY", f"Generate content for: {prompt}")
        
        # Use the content generator tool
        log_flow_step(session_id, "TOOL", f"content_generator(prompt={prompt})")
        content_generator = available_tools["content_generator"]
        content_ideas = content_generator.execute(prompt=prompt)
        log_flow_step(session_id, "RESULT", f"Generated {len(content_ideas.get('video_ideas', []))} ideas")
        
        if not content_ideas:
            return jsonify({
                "error": "Failed to generate content ideas",
                "message": "Could not generate content ideas for the specified prompt"
            }), 500
        
        # Generate insights with Gemini
        system_prompt = f"""
        You're an expert YouTube content strategist creating a detailed content plan for a video about: '{prompt}'.
        
        Review the video ideas, thumbnail concepts, and script template I'm providing you. Then, create a comprehensive,
        highly specific response with these sections:
        
        1. CONTENT STRATEGY
        - Analyze which video idea has the highest potential and explain exactly why
        - Suggest 2-3 specific ways to make the title and hook even more compelling
        - Identify the most important points to emphasize based on current trends
        
        2. SCRIPT ENHANCEMENT
        - Provide specific talking points for the introduction that will hook viewers
        - Suggest 2-3 storytelling techniques that would work well for this topic
        - Recommend visual elements or demonstrations to include at specific timestamps
        
        3. THUMBNAIL OPTIMIZATION
        - Select the best thumbnail idea and explain why it will generate the highest CTR
        - Suggest specific colors, fonts, and composition for maximum impact
        - Recommend a specific emotion to convey in the thumbnail and how to achieve it
        
        4. DISTRIBUTION STRATEGY
        - Recommend specific hashtags for this topic
        - Suggest the best posting time and promotional approach
        - Identify 2-3 related content pieces to create as follow-ups
        
        Your advice should be extremely specific to '{prompt}' and actionable. Include exact phrases, examples, 
        and techniques that would work well for this particular topic.
        """
        
        user_prompt = json.dumps(content_ideas, indent=2)
        
        # Call Gemini for insights
        log_flow_step(session_id, "QUERY", "Generate content strategy")
        ai_insights = call_gemini(
            prompt=user_prompt,
            conversation_id=session_id,
            tool_results={"system_prompt": system_prompt}
        )
        
        log_flow_step(session_id, "RESULT", "Content generation complete")
        
        return jsonify({
            "success": True,
            "prompt": prompt,
            "content_ideas": content_ideas,
            "ai_insights": ai_insights
        })
    
    except Exception as e:
        log_flow_step(session_id, "ERROR", str(e))
        logger.error(f"Error in /generate_content: {str(e)}")
        return jsonify({
            "error": "Content generation failed",
            "message": str(e)
        }), 500

@app.route('/track_performance', methods=['POST'])
def track_performance():
    """
    Track performance of a specific video
    
    Request:
    {
        "video_url": "string",  // Required: URL of the YouTube video to analyze
        "session_id": "string"  // Optional: session ID for conversation history
    }
    """
    data = request.json
    
    if not data or "video_url" not in data:
        return jsonify({"error": "Missing required parameter: video_url"}), 400
    
    video_url = data["video_url"]
    session_id = data.get("session_id", "default")
    
    # Check if the URL is a valid YouTube URL
    if "youtube.com" not in video_url and "youtu.be" not in video_url:
        return jsonify({
            "error": "Invalid YouTube URL",
            "message": "Please provide a valid YouTube video URL"
        }), 400
    
    try:
        # Initialize flow for this session
        flow_steps[session_id] = 1
        
        # Log initial query
        log_flow_step(session_id, "QUERY", f"Track performance for: {video_url}")
        
        # Use the performance tracker tool
        log_flow_step(session_id, "TOOL", f"performance_tracker(video_url={video_url})")
        performance_tracker = available_tools["performance_tracker"]
        performance_data = performance_tracker.execute(video_url=video_url)
        
        if "error" in performance_data:
            log_flow_step(session_id, "ERROR", performance_data["error"])
            return jsonify({
                "error": "Performance tracking failed",
                "message": performance_data["error"]
            }), 400
        
        log_flow_step(session_id, "RESULT", "Performance data retrieved")
        
        # Generate insights with Gemini
        system_prompt = """
        You're analyzing YouTube video performance metrics.
        Based on the data provided, give specific actionable advice to improve:
        1. Viewer retention
        2. Engagement (likes, comments)
        3. Overall performance
        Keep your recommendations practical and specific to this video.
        """
        
        user_prompt = json.dumps(performance_data, indent=2)
        
        # Call Gemini for insights
        log_flow_step(session_id, "QUERY", "Generate performance insights")
        ai_insights = call_gemini(
            prompt=user_prompt,
            conversation_id=session_id,
            tool_results={"system_prompt": system_prompt}
        )
        
        log_flow_step(session_id, "RESULT", "Performance analysis complete")
        
        return jsonify({
            "success": True,
            "video_url": video_url,
            "performance_data": performance_data,
            "ai_insights": ai_insights
        })
    
    except Exception as e:
        log_flow_step(session_id, "ERROR", str(e))
        logger.error(f"Error in /track_performance: {str(e)}")
        return jsonify({
            "error": "Performance tracking failed",
            "message": str(e)
        }), 500

@app.route('/analyze_video', methods=['POST'])
def analyze_video():
    try:
        data = request.json
        video_id = data.get('video_id', '')
        video_data = data.get('video_data', {})
        
        # Generate a conversation ID
        conversation_id = f"video_{int(time.time())}"
        
        # Initialize flow for this session
        flow_steps[conversation_id] = 1
        
        # Log initial query
        log_flow_step(conversation_id, "QUERY", f"Analyze video ID: {video_id}")
        
        # Initial prompt to the model
        prompt = f"I want to analyze this YouTube video with ID {video_id} and the following data: {json.dumps(video_data)}. What insights can you provide about this video's performance, SEO, and content quality?"
        
        # First call to Gemini
        response = call_gemini(prompt, conversation_id)
        
        # Check if there's a tool call
        if response.get("tool_call"):
            # Execute the tool
            tool_name = response["tool_call"]["name"]
            log_flow_step(conversation_id, "TOOL", f"{tool_name}")
            tool_results = execute_tool_call(response["tool_call"])
            log_flow_step(conversation_id, "RESULT", f"Tool results from {tool_name}")
            
            # Second call to Gemini with tool results
            second_prompt = "Based on the video analysis, what specific improvements would you recommend for this video? How can the title, description, and content be optimized?"
            log_flow_step(conversation_id, "QUERY", "Request improvements based on analysis")
            second_response = call_gemini(
                second_prompt,
                conversation_id, 
                tool_results
            )
            
            # Check if there's another tool call
            if second_response.get("tool_call"):
                # Execute the second tool
                second_tool_name = second_response["tool_call"]["name"]
                log_flow_step(conversation_id, "TOOL", f"{second_tool_name}")
                second_tool_results = execute_tool_call(second_response["tool_call"])
                log_flow_step(conversation_id, "RESULT", f"Tool results from {second_tool_name}")
                
                # Final call to Gemini with all results
                final_prompt = "Based on all the analysis, what are your final recommendations for improving this video and creating better content in the future?"
                log_flow_step(conversation_id, "QUERY", "Request final recommendations")
                final_response = call_gemini(
                    final_prompt,
                    conversation_id,
                    second_tool_results
                )
                
                log_flow_step(conversation_id, "RESULT", "Full agentic flow complete (Query→LLM→Tool→Result→Query→LLM→Tool→Result→Query→LLM→Result)")
                
                return jsonify({
                    "result": final_response["response"],
                    "video_id": video_id,
                    "conversation_id": conversation_id
                })
            else:
                log_flow_step(conversation_id, "RESULT", "Partial agentic flow complete (Query→LLM→Tool→Result→Query→LLM→Result)")
                return jsonify({
                    "result": second_response["response"],
                    "video_id": video_id,
                    "conversation_id": conversation_id
                })
        else:
            log_flow_step(conversation_id, "RESULT", "Simple flow complete (Query→LLM→Result)")
            return jsonify({
                "result": response["response"],
                "video_id": video_id,
                "conversation_id": conversation_id
            })
            
    except Exception as e:
        log_flow_step(conversation_id if 'conversation_id' in locals() else "unknown", "ERROR", str(e))
        logger.error(f"Error in analyze_video: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000) 