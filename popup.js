document.addEventListener('DOMContentLoaded', function() {
  // Tab switching functionality
  const tabButtons = document.querySelectorAll('.tab-button');
  const tabContents = document.querySelectorAll('.tab-content');
  
  tabButtons.forEach(button => {
    button.addEventListener('click', () => {
      const tabId = button.getAttribute('data-tab');
      
      // Update active button
      tabButtons.forEach(btn => btn.classList.remove('active'));
      button.classList.add('active');
      
      // Update active content
      tabContents.forEach(content => content.classList.remove('active'));
      document.getElementById(`${tabId}-tab`).classList.add('active');
    });
  });
  
  // API backend URL - Update with your Python backend server URL
  const API_URL = 'http://localhost:5000';
  
  // Check if API is running
  checkApiConnection();
  
  // Button event listeners
  document.getElementById('analyze-trending').addEventListener('click', analyzeTrending);
  document.getElementById('generate-content').addEventListener('click', generateContent);
  document.getElementById('track-performance').addEventListener('click', trackPerformance);
  
  // Check for previous analysis results
  chrome.storage.local.get('lastAnalysis', function(data) {
    if (data.lastAnalysis) {
      // Show in the appropriate tab based on type
      if (data.lastAnalysis.video_id) {
        displayResults('performance-results', data.lastAnalysis.result);
        // Switch to performance tab
        document.querySelector('[data-tab="performance"]').click();
      }
    }
  });
  
  // Function to check if API is running
  async function checkApiConnection() {
    try {
      const response = await fetch(`${API_URL}`, {
        method: 'GET',
        mode: 'no-cors'
      });
      
      // If we get here, the server is at least responding
      console.log('API appears to be running');
    } catch (error) {
      console.warn('API connection check failed:', error);
      // Show a warning in each tab
      displayResults('trending-results', 'Warning: Could not connect to the backend API. Make sure the Python backend is running on http://localhost:5000');
      displayResults('content-results', 'Warning: Could not connect to the backend API. Make sure the Python backend is running on http://localhost:5000');
      displayResults('performance-results', 'Warning: Could not connect to the backend API. Make sure the Python backend is running on http://localhost:5000');
    }
  }
  
  // Function to handle trending analysis
  async function analyzeTrending() {
    const niche = document.getElementById('niche-input').value.trim();
    if (!niche) {
      alert('Please enter a niche to analyze');
      return;
    }
    
    showLoader('trending-loader');
    displayResults('trending-results', 'Analyzing trending videos for ' + niche + '...');
    
    try {
      const response = await fetch(`${API_URL}/analyze_trending`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ niche })
      });
      
      if (!response.ok) {
        throw new Error(`Server error: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      
      if (data.error) {
        throw new Error(data.error);
      }
      
      displayResults('trending-results', data.result);
    } catch (error) {
      console.error('Error:', error);
      displayResults('trending-results', `Error: ${error.message || 'Could not analyze trending videos. Please try again later.'}`);
    } finally {
      hideLoader('trending-loader');
    }
  }
  
  // Function to handle content generation
  async function generateContent() {
    const prompt = document.getElementById('content-prompt').value.trim();
    if (!prompt) {
      alert('Please enter a description of the content you want to create');
      return;
    }
    
    showLoader('content-loader');
    displayResults('content-results', 'Generating content ideas for your query...');
    
    try {
      const response = await fetch(`${API_URL}/generate_content`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ prompt })
      });
      
      if (!response.ok) {
        throw new Error(`Server error: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      
      if (data.error) {
        throw new Error(data.error);
      }
      
      displayResults('content-results', data.result);
    } catch (error) {
      console.error('Error:', error);
      displayResults('content-results', `Error: ${error.message || 'Could not generate content. Please try again later.'}`);
    } finally {
      hideLoader('content-loader');
    }
  }
  
  // Function to handle performance tracking
  async function trackPerformance() {
    const videoUrl = document.getElementById('video-url').value.trim();
    if (!videoUrl) {
      alert('Please enter a YouTube video URL');
      return;
    }
    
    // Simple validation for YouTube URL
    if (!videoUrl.includes('youtube.com/') && !videoUrl.includes('youtu.be/')) {
      alert('Please enter a valid YouTube video URL');
      return;
    }
    
    showLoader('performance-loader');
    displayResults('performance-results', 'Analyzing performance for ' + videoUrl + '...');
    
    try {
      const response = await fetch(`${API_URL}/track_performance`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ video_url: videoUrl })
      });
      
      if (!response.ok) {
        throw new Error(`Server error: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      
      if (data.error) {
        throw new Error(data.error);
      }
      
      displayResults('performance-results', data.result);
    } catch (error) {
      console.error('Error:', error);
      displayResults('performance-results', `Error: ${error.message || 'Could not analyze video performance. Please try again later.'}`);
    } finally {
      hideLoader('performance-loader');
    }
  }
  
  // Helper functions
  function showLoader(id) {
    document.getElementById(id).style.display = 'block';
  }
  
  function hideLoader(id) {
    document.getElementById(id).style.display = 'none';
  }
  
  function displayResults(containerId, results) {
    const container = document.getElementById(containerId);
    
    // Format the results if they're an object
    let formattedResults = results;
    if (typeof results === 'object') {
      formattedResults = '<ul>' + 
        Object.entries(results).map(([key, value]) => 
          `<li><strong>${key}:</strong> ${value}</li>`
        ).join('') + 
        '</ul>';
    }
    
    container.innerHTML = formattedResults;
  }
}); 