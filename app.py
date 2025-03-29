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

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Get API key from environment variable
API_KEY = os.getenv("GEMINI_API_KEY", "your-api-key-here")

# Initialize Gemini API
genai.configure(api_key=API_KEY)

# Store conversation history for each session
conversation_history = {}

# Root endpoint for health check
@app.route('/', methods=['GET'])
def health_check():
    """
    Simple health check endpoint to confirm the API is running
    """
    return jsonify({
        "status": "ok",
        "message": "YouTube Content Analyzer API is running",
        "api_key_configured": bool(API_KEY and API_KEY != "your-api-key-here")
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
        """Simulate scraping trending videos from YouTube"""
        logger.info(f"Scraping trending videos for niche: {niche}")
        
        # In a real implementation, we would use YouTube API or web scraping
        # For this demo, we'll return mock data
        return {
            "trending_videos": [
                {
                    "title": f"Top 10 {niche.capitalize()} Tips for Beginners",
                    "views": "1.2M",
                    "likes": "45K",
                    "channel": f"{niche.capitalize()} Expert",
                    "keywords": [niche, "beginners", "tips", "tutorial"],
                    "description": f"Learn the best {niche} tips and tricks in this comprehensive guide."
                },
                {
                    "title": f"Why {niche.capitalize()} Is Changing Everything in 2023",
                    "views": "892K",
                    "likes": "32K",
                    "channel": "TrendWatcher",
                    "keywords": [niche, "trends", "2023", "industry"],
                    "description": f"The {niche} industry is evolving rapidly. Here's what you need to know."
                },
                {
                    "title": f"I Tried {niche.capitalize()} For 30 Days - Here's What Happened",
                    "views": "2.4M",
                    "likes": "78K",
                    "channel": "LifeExperiments",
                    "keywords": [niche, "challenge", "experiment", "journey"],
                    "description": f"My personal journey with {niche} and the surprising results after 30 days."
                }
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
        logger.info(f"Analyzing content: {content['title'] if 'title' in content else 'data'}")
        
        # In a real implementation, we would use NLP or SEO analysis tools
        # For this demo, we'll return mock analysis
        
        # Extract keywords from title and description
        all_text = f"{content.get('title', '')} {content.get('description', '')}"
        keywords = re.findall(r'\b\w{4,}\b', all_text.lower())
        keyword_freq = {}
        for keyword in keywords:
            if keyword in keyword_freq:
                keyword_freq[keyword] += 1
            else:
                keyword_freq[keyword] = 1
        
        # Sort keywords by frequency
        sorted_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)
        top_keywords = sorted_keywords[:5] if sorted_keywords else []
        
        return {
            "seo_score": 75,
            "title_effectiveness": 80,
            "description_effectiveness": 65,
            "suggested_keywords": [k for k, _ in top_keywords],
            "improvement_suggestions": [
                "Add more specific keywords related to your niche",
                "Make the title more engaging with emotional triggers",
                "Include a clear call-to-action in the description",
                "Add timestamps for longer videos",
                "Use more hashtags relevant to trending topics"
            ]
        }

class ContentGeneratorTool(Tool):
    def __init__(self):
        super().__init__(
            name="content_generator",
            description="Generates video script ideas and thumbnails based on trending topics"
        )
    
    def execute(self, prompt: str, trending_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate content ideas based on prompt and trending data"""
        logger.info(f"Generating content based on prompt: {prompt}")
        
        # In a real implementation, we would use a more sophisticated AI system
        # For this demo, we'll generate mock content
        
        return {
            "video_ideas": [
                {
                    "title": "7 Incredible Ways to Master Your Craft in 2023",
                    "hook": "Did you know 80% of experts use this one technique?",
                    "outline": [
                        "Introduction (0:00-1:30)",
                        "Common mistakes to avoid (1:30-4:00)",
                        "The 7 techniques, explained (4:00-12:00)",
                        "Implementation steps (12:00-15:00)",
                        "Results you can expect (15:00-17:00)",
                        "Call to action (17:00-18:00)"
                    ]
                },
                {
                    "title": "The Ultimate Beginner's Guide That Experts Don't Want You To See",
                    "hook": "This simple approach changed everything for me...",
                    "outline": [
                        "My story and struggle (0:00-2:30)",
                        "The breakthrough moment (2:30-4:00)",
                        "Step-by-step methodology (4:00-10:00)",
                        "Avoiding common pitfalls (10:00-13:00)",
                        "Advanced tips for faster results (13:00-16:00)",
                        "Next steps and resources (16:00-18:00)"
                    ]
                }
            ],
            "thumbnail_ideas": [
                "Bold text overlay with shocked face reaction and contrasting colors",
                "Before/after split screen with progress metrics clearly visible",
                "Question headline with arrow pointing to visual result"
            ],
            "script_template": "INTRO:\nHook viewers with a surprising stat or question\nTeaser of what they'll learn\n\nMAIN CONTENT:\nPoint 1: Problem statement\nPoint 2: Solution overview\nPoint 3-5: Detailed steps\n\nCONCLUSION:\nSummary of benefits\nCall to action\nTeaser for next video"
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
        
        # Extract video ID from URL
        video_id = None
        if "youtube.com" in video_url:
            video_id = video_url.split("v=")[1].split("&")[0] if "v=" in video_url else None
        elif "youtu.be" in video_url:
            video_id = video_url.split("/")[-1]
        
        if not video_id:
            return {"error": "Invalid YouTube URL"}
        
        # In a real implementation, we would use YouTube Analytics API
        # For this demo, we'll return mock performance data
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
    logger.info(f"Calling Gemini with prompt: {prompt[:100]}...")
    
    # Get or create conversation history
    if conversation_id not in conversation_history:
        conversation_history[conversation_id] = []
    
    # Add tool results to history if provided
    if tool_results:
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
        
        # Call Gemini API using the correct method for version 0.3.1
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(full_prompt)
        
        # Parse response for tool calls
        response_text = response.text
        
        # Check if the response includes a tool call
        if "TOOL:" in response_text:
            # Extract tool name and parameters
            tool_pattern = r"TOOL: (\w+)\nPARAMS: ({.*})"
            tool_match = re.search(tool_pattern, response_text, re.DOTALL)
            
            if tool_match:
                tool_name = tool_match.group(1)
                tool_params_str = tool_match.group(2)
                
                try:
                    # Log original parameters for debugging
                    logger.info(f"Original parameters: {tool_params_str}")
                    
                    # Handle the case of video_url specifically - direct extraction
                    if tool_name == "performance_tracker" and "video_url" in tool_params_str:
                        url_match = re.search(r'https?://[^\s"]+', tool_params_str)
                        if url_match:
                            url = url_match.group(0)
                            tool_params = {"video_url": url}
                            logger.info(f"Direct extraction: extracted URL {url} from parameters")
                            
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
                    
                    # For other tools, try standard JSON parsing with improvements
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
        return {"error": f"Tool '{tool_name}' not found"}
    
    try:
        tool = available_tools[tool_name]
        result = tool.execute(**tool_params)
        return {tool_name: result}
    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {e}")
        return {"error": f"Tool execution error: {str(e)}"}

# API routes
@app.route('/analyze_trending', methods=['POST'])
def analyze_trending():
    try:
        data = request.json
        niche = data.get('niche', '')
        
        # Generate a conversation ID
        conversation_id = f"trending_{int(time.time())}"
        
        # Initial prompt to the model
        prompt = f"I want to analyze trending YouTube videos in the {niche} niche. What insights can you provide about current trends, and what kind of content is performing well in this area? Use the youtube_scraper tool with the parameter 'niche' (not 'keyword')."
        
        # First call to Gemini
        response = call_gemini(prompt, conversation_id)
        
        # Check if there's a tool call
        if response.get("tool_call"):
            # Execute the tool
            tool_results = execute_tool_call(response["tool_call"])
            
            # Second call to Gemini with tool results
            second_response = call_gemini(
                f"Based on the trending analysis for {niche}, what specific insights can you provide about the most successful videos? What patterns do you see in titles, descriptions, and keywords?",
                conversation_id, 
                tool_results
            )
            
            # Check if there's another tool call
            if second_response.get("tool_call"):
                # Execute the second tool
                second_tool_results = execute_tool_call(second_response["tool_call"])
                
                # Final call to Gemini with all results
                final_response = call_gemini(
                    f"Based on all the data gathered about {niche} trending videos, what are your final recommendations for creating successful content in this niche?",
                    conversation_id,
                    second_tool_results
                )
                
                return jsonify({
                    "result": final_response["response"],
                    "conversation_id": conversation_id
                })
            else:
                return jsonify({
                    "result": second_response["response"],
                    "conversation_id": conversation_id
                })
        else:
            return jsonify({
                "result": response["response"],
                "conversation_id": conversation_id
            })
            
    except Exception as e:
        logger.error(f"Error in analyze_trending: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/generate_content', methods=['POST'])
def generate_content():
    try:
        data = request.json
        prompt = data.get('prompt', '')
        
        # Generate a conversation ID
        conversation_id = f"content_{int(time.time())}"
        
        # Initial prompt to the model
        ai_prompt = f"I need help generating video content ideas for: {prompt}. Can you suggest video ideas, script outlines, and thumbnail concepts? When using the content_generator tool, use the parameter name 'prompt' for the input."
        
        # First call to Gemini
        response = call_gemini(ai_prompt, conversation_id)
        
        # Check if there's a tool call
        if response.get("tool_call"):
            # Execute the tool
            tool_results = execute_tool_call(response["tool_call"])
            
            # Second call to Gemini with tool results
            second_response = call_gemini(
                f"Based on the content ideas generated, can you provide more detailed script suggestions and SEO optimization tips for: {prompt}?",
                conversation_id, 
                tool_results
            )
            
            # Check if there's another tool call
            if second_response.get("tool_call"):
                # Execute the second tool
                second_tool_results = execute_tool_call(second_response["tool_call"])
                
                # Final call to Gemini with all results
                final_response = call_gemini(
                    f"Based on all the data and suggestions, what's the final optimized content plan for my video about: {prompt}?",
                    conversation_id,
                    second_tool_results
                )
                
                return jsonify({
                    "result": final_response["response"],
                    "conversation_id": conversation_id
                })
            else:
                return jsonify({
                    "result": second_response["response"],
                    "conversation_id": conversation_id
                })
        else:
            return jsonify({
                "result": response["response"],
                "conversation_id": conversation_id
            })
            
    except Exception as e:
        logger.error(f"Error in generate_content: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/track_performance', methods=['POST'])
def track_performance():
    try:
        data = request.json
        video_url = data.get('video_url', '')
        
        # Generate a conversation ID
        conversation_id = f"performance_{int(time.time())}"
        
        # Initial prompt to the model
        prompt = f"""I want to analyze the performance of this YouTube video: {video_url}. 
What insights can you provide about its performance, and how can I improve it?

IMPORTANT FORMATTING INSTRUCTIONS:
When using the performance_tracker tool, follow this EXACT format:
TOOL: performance_tracker
PARAMS: {{"video_url": "{video_url}"}}

Do not add any extra quotes or formatting to the URL.
"""
        
        # First call to Gemini
        response = call_gemini(prompt, conversation_id)
        
        # Check if there's a tool call
        if response.get("tool_call"):
            # Execute the tool
            tool_results = execute_tool_call(response["tool_call"])
            
            # Second call to Gemini with tool results
            second_response = call_gemini(
                "Based on the performance data, what specific improvements would you recommend for this video? What patterns do you see in audience retention and engagement?",
                conversation_id, 
                tool_results
            )
            
            # Check if there's another tool call
            if second_response.get("tool_call"):
                # Execute the second tool
                second_tool_results = execute_tool_call(second_response["tool_call"])
                
                # Final call to Gemini with all results
                final_response = call_gemini(
                    "Based on all the performance data analyzed, what are your final recommendations for improving this video and creating better content in the future?",
                    conversation_id,
                    second_tool_results
                )
                
                return jsonify({
                    "result": final_response["response"],
                    "conversation_id": conversation_id
                })
            else:
                return jsonify({
                    "result": second_response["response"],
                    "conversation_id": conversation_id
                })
        else:
            return jsonify({
                "result": response["response"],
                "conversation_id": conversation_id
            })
            
    except Exception as e:
        logger.error(f"Error in track_performance: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/analyze_video', methods=['POST'])
def analyze_video():
    try:
        data = request.json
        video_id = data.get('video_id', '')
        video_data = data.get('video_data', {})
        
        # Generate a conversation ID
        conversation_id = f"video_{int(time.time())}"
        
        # Initial prompt to the model
        prompt = f"I want to analyze this YouTube video with ID {video_id} and the following data: {json.dumps(video_data)}. What insights can you provide about this video's performance, SEO, and content quality?"
        
        # First call to Gemini
        response = call_gemini(prompt, conversation_id)
        
        # Check if there's a tool call
        if response.get("tool_call"):
            # Execute the tool
            tool_results = execute_tool_call(response["tool_call"])
            
            # Second call to Gemini with tool results
            second_response = call_gemini(
                "Based on the video analysis, what specific improvements would you recommend for this video? How can the title, description, and content be optimized?",
                conversation_id, 
                tool_results
            )
            
            # Check if there's another tool call
            if second_response.get("tool_call"):
                # Execute the second tool
                second_tool_results = execute_tool_call(second_response["tool_call"])
                
                # Final call to Gemini with all results
                final_response = call_gemini(
                    "Based on all the analysis, what are your final recommendations for improving this video and creating better content in the future?",
                    conversation_id,
                    second_tool_results
                )
                
                return jsonify({
                    "result": final_response["response"],
                    "video_id": video_id,
                    "conversation_id": conversation_id
                })
            else:
                return jsonify({
                    "result": second_response["response"],
                    "video_id": video_id,
                    "conversation_id": conversation_id
                })
        else:
            return jsonify({
                "result": response["response"],
                "video_id": video_id,
                "conversation_id": conversation_id
            })
            
    except Exception as e:
        logger.error(f"Error in analyze_video: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000) 