document.addEventListener('DOMContentLoaded', function() {
  // Add a simple markdown parser fallback in case marked.js is not available
  if (typeof marked === 'undefined') {
    console.warn('Marked library not loaded. Using fallback parser.');
    
    // Simple markdown parser fallback
    window.marked = {
      parse: function(markdown) {
        if (!markdown) return '';
        
        // Basic conversion of markdown to HTML
        return markdown
          // Convert headers
          .replace(/^# (.*?)$/gm, '<h1>$1</h1>')
          .replace(/^## (.*?)$/gm, '<h2>$1</h2>')
          .replace(/^### (.*?)$/gm, '<h3>$1</h3>')
          .replace(/^#### (.*?)$/gm, '<h4>$1</h4>')
          
          // Convert bold and italic
          .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
          .replace(/__(.*?)__/g, '<strong>$1</strong>')
          .replace(/\*(.*?)\*/g, '<em>$1</em>')
          .replace(/_(.*?)_/g, '<em>$1</em>')
          
          // Convert bullet lists
          .replace(/^\* (.*?)$/gm, '<li>$1</li>')
          .replace(/^- (.*?)$/gm, '<li>$1</li>')
          
          // Fix lists by adding <ul> tags
          .replace(/(<li>.*?<\/li>)(?!\s*<li>)/gs, '<ul>$1</ul>')
          
          // Convert paragraphs (any line not starting with HTML tag)
          .replace(/^(?!<\w+>)(.*?)$/gm, function(match) {
            if (match.trim() === '') return match;
            return '<p>' + match + '</p>';
          })
          
          // Fix line breaks
          .replace(/\n\n/g, '<br>')
          
          // Final cleanup for any duplicate tags
          .replace(/<\/p><p>/g, '</p>\n<p>');
      }
    };
  }
  
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
        method: 'GET'
      });
      
      const data = await response.json();
      console.log('API status:', data);
      
      if (data.youtube_api_working) {
        console.log('YouTube API is working correctly');
      } else if (data.youtube_api_configured) {
        console.warn('YouTube API is configured but not working');
      } else {
        console.warn('YouTube API is not configured');
      }
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
        body: JSON.stringify({ 
          niche,
          session_id: `session_${Date.now()}`
        })
      });
      
      if (!response.ok) {
        throw new Error(`Server error: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      
      if (data.error) {
        throw new Error(data.error);
      }
      
      // Format the trending videos and analysis
      let formattedResults = `<h3>Trending Analysis for "${niche}"</h3>`;
      
      // Add AI summary if available
      if (data.ai_summary && data.ai_summary.response) {
        // Check if response is markdown
        if (typeof data.ai_summary.response === 'string' && 
            (data.ai_summary.response.includes('**') || 
             data.ai_summary.response.includes('#') || 
             data.ai_summary.response.includes('*') || 
             data.ai_summary.response.includes('-'))) {
          
          // Start with basic title
          displayResults('trending-results', `<h3>Trending Analysis for "${niche}"</h3>`);
          
          // Create container for markdown content
          const container = document.getElementById('trending-results');
          const insightsHeading = document.createElement('h4');
          insightsHeading.textContent = 'AI Insights';
          container.appendChild(insightsHeading);
          
          // Create markdown div
          const markdownDiv = document.createElement('div');
          markdownDiv.className = 'markdown-content';
          
          try {
            // Parse markdown
            markdownDiv.innerHTML = marked.parse(data.ai_summary.response);
          } catch (error) {
            console.error('Error parsing markdown:', error);
            markdownDiv.innerHTML = `<pre>${data.ai_summary.response}</pre>`;
          }
          
          // Append markdown content
          container.appendChild(markdownDiv);
          
          // Add video results if available
          if (data.trending_videos && data.trending_videos.length > 0) {
            const videosHeading = document.createElement('h4');
            videosHeading.textContent = 'Top Trending Videos';
            container.appendChild(videosHeading);
            
            const videoGrid = document.createElement('div');
            videoGrid.className = 'video-grid';
            
            data.trending_videos.forEach(video => {
              const videoAnalysis = data.analysis_results.find(result => result.video.video_id === video.video_id);
              const seoScore = videoAnalysis ? videoAnalysis.analysis.seo_score : 'N/A';
              
              const videoCard = document.createElement('div');
              videoCard.className = 'video-card';
              videoCard.innerHTML = `
                <div class="video-thumbnail">
                  <img src="${video.thumbnail || 'https://i.ytimg.com/vi/default/hqdefault.jpg'}" alt="${video.title}">
                </div>
                <div class="video-info">
                  <h5>${video.title}</h5>
                  <p>Channel: ${video.channel}</p>
                  <p>Views: ${video.views_formatted || video.views}</p>
                  <p>Likes: ${video.likes_formatted || video.likes}</p>
                  <p>SEO Score: ${seoScore}/100</p>
                </div>
              `;
              
              videoGrid.appendChild(videoCard);
            });
            
            container.appendChild(videoGrid);
          }
          
          // Add custom styles
          addCustomStyles();
          
          return;
        } else {
          formattedResults += `<div class="ai-summary"><h4>AI Insights</h4><p>${data.ai_summary.response}</p></div>`;
        }
      }
      
      // Add video results
      if (data.trending_videos && data.trending_videos.length > 0) {
        formattedResults += '<h4>Top Trending Videos</h4><div class="video-grid">';
        
        data.trending_videos.forEach(video => {
          const videoAnalysis = data.analysis_results.find(result => result.video.video_id === video.video_id);
          const seoScore = videoAnalysis ? videoAnalysis.analysis.seo_score : 'N/A';
          
          formattedResults += `
            <div class="video-card">
              <div class="video-thumbnail">
                <img src="${video.thumbnail || 'https://i.ytimg.com/vi/default/hqdefault.jpg'}" alt="${video.title}">
              </div>
              <div class="video-info">
                <h5>${video.title}</h5>
                <p>Channel: ${video.channel}</p>
                <p>Views: ${video.views_formatted || video.views}</p>
                <p>Likes: ${video.likes_formatted || video.likes}</p>
                <p>SEO Score: ${seoScore}/100</p>
              </div>
            </div>
          `;
        });
        
        formattedResults += '</div>';
      }
      
      displayResults('trending-results', formattedResults);
      
      // Add custom styles for the video grid
      addCustomStyles();
      
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
        body: JSON.stringify({ 
          prompt,
          session_id: `session_${Date.now()}`
        })
      });
      
      if (!response.ok) {
        throw new Error(`Server error: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      
      if (data.error) {
        throw new Error(data.error);
      }
      
      // Format the content ideas
      let formattedResults = `<h3>Content Ideas for "${prompt}"</h3>`;
      
      // Add AI insights if available
      if (data.ai_insights && data.ai_insights.response) {
        // Check if response is markdown
        if (typeof data.ai_insights.response === 'string' && 
            (data.ai_insights.response.includes('**') || 
             data.ai_insights.response.includes('#') || 
             data.ai_insights.response.includes('*') || 
             data.ai_insights.response.includes('-'))) {
          
          // Start with basic title
          displayResults('content-results', `<h3>Content Ideas for "${prompt}"</h3>`);
          
          // Create container for markdown content
          const container = document.getElementById('content-results');
          const insightsHeading = document.createElement('h4');
          insightsHeading.textContent = 'AI Recommendations';
          container.appendChild(insightsHeading);
          
          // Create markdown div
          const markdownDiv = document.createElement('div');
          markdownDiv.className = 'markdown-content';
          
          try {
            // Parse markdown
            markdownDiv.innerHTML = marked.parse(data.ai_insights.response);
          } catch (error) {
            console.error('Error parsing markdown:', error);
            markdownDiv.innerHTML = `<pre>${data.ai_insights.response}</pre>`;
          }
          
          // Append markdown content
          container.appendChild(markdownDiv);
          
          // Display video ideas
          if (data.content_ideas && data.content_ideas.video_ideas) {
            const ideasHeading = document.createElement('h4');
            ideasHeading.textContent = 'Video Ideas';
            container.appendChild(ideasHeading);
            
            data.content_ideas.video_ideas.forEach((idea, index) => {
              const ideaCard = document.createElement('div');
              ideaCard.className = 'idea-card';
              ideaCard.innerHTML = `
                <h5>${idea.title}</h5>
                <p><strong>Hook:</strong> ${idea.hook}</p>
                <p><strong>Outline:</strong></p>
                <ul>
                  ${idea.outline.map(item => `<li>${item}</li>`).join('')}
                </ul>
              `;
              
              container.appendChild(ideaCard);
            });
          }
          
          // Display thumbnail ideas
          if (data.content_ideas && data.content_ideas.thumbnail_ideas) {
            const thumbnailHeading = document.createElement('h4');
            thumbnailHeading.textContent = 'Thumbnail Ideas';
            container.appendChild(thumbnailHeading);
            
            const thumbnailList = document.createElement('ul');
            data.content_ideas.thumbnail_ideas.forEach(idea => {
              const item = document.createElement('li');
              item.textContent = idea;
              thumbnailList.appendChild(item);
            });
            
            container.appendChild(thumbnailList);
          }
          
          // Display script template
          if (data.content_ideas && data.content_ideas.script_template) {
            const scriptHeading = document.createElement('h4');
            scriptHeading.textContent = 'Script Template';
            container.appendChild(scriptHeading);
            
            const scriptTemplate = document.createElement('div');
            scriptTemplate.className = 'script-template';
            
            const pre = document.createElement('pre');
            pre.textContent = data.content_ideas.script_template;
            scriptTemplate.appendChild(pre);
            
            container.appendChild(scriptTemplate);
          }
          
          // Add custom styles
          addCustomStyles();
          
          return;
        } else {
          formattedResults += `<div class="ai-insights"><h4>AI Recommendations</h4><p>${data.ai_insights.response}</p></div>`;
        }
      }
      
      // Display video ideas
      if (data.content_ideas && data.content_ideas.video_ideas) {
        formattedResults += `<h4>Video Ideas</h4>`;
        
        data.content_ideas.video_ideas.forEach((idea, index) => {
          formattedResults += `
            <div class="idea-card">
              <h5>${idea.title}</h5>
              <p><strong>Hook:</strong> ${idea.hook}</p>
              <p><strong>Outline:</strong></p>
              <ul>
                ${idea.outline.map(item => `<li>${item}</li>`).join('')}
              </ul>
            </div>
          `;
        });
      }
      
      // Display thumbnail ideas
      if (data.content_ideas && data.content_ideas.thumbnail_ideas) {
        formattedResults += `<h4>Thumbnail Ideas</h4><ul>`;
        data.content_ideas.thumbnail_ideas.forEach(idea => {
          formattedResults += `<li>${idea}</li>`;
        });
        formattedResults += `</ul>`;
      }
      
      // Display script template
      if (data.content_ideas && data.content_ideas.script_template) {
        formattedResults += `
          <h4>Script Template</h4>
          <div class="script-template">
            <pre>${data.content_ideas.script_template}</pre>
          </div>
        `;
      }
      
      displayResults('content-results', formattedResults);
      
      // Add custom styles for content ideas
      addCustomStyles();
      
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
        body: JSON.stringify({ 
          video_url: videoUrl,
          session_id: `session_${Date.now()}`
        })
      });
      
      if (!response.ok) {
        throw new Error(`Server error: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      
      if (data.error) {
        throw new Error(data.error);
      }
      
      // Format the performance data
      let formattedResults = `<h3>Performance Analysis</h3>`;
      
      if (data.performance_data) {
        const pd = data.performance_data;
        formattedResults += `
          <div class="performance-summary">
            <h4>${pd.title || "Video Analysis"}</h4>
            <div class="metrics-grid">
              <div class="metric">
                <span class="metric-label">Views</span>
                <span class="metric-value">${pd.views}</span>
              </div>
              <div class="metric">
                <span class="metric-label">Likes</span>
                <span class="metric-value">${pd.likes}</span>
              </div>
              <div class="metric">
                <span class="metric-label">Comments</span>
                <span class="metric-value">${pd.comments}</span>
              </div>
              <div class="metric">
                <span class="metric-label">Engagement Rate</span>
                <span class="metric-value">${pd.engagement_rate || "N/A"}</span>
              </div>
            </div>
          </div>
        `;
        
        // Audience retention
        if (pd.audience_retention && pd.audience_retention.length > 0) {
          formattedResults += `<h4>Audience Retention</h4><ul class="retention-list">`;
          pd.audience_retention.forEach(segment => {
            formattedResults += `<li>${segment.segment}: ${segment.retention}</li>`;
          });
          formattedResults += `</ul>`;
        }
        
        // Improvement suggestions
        if (pd.improvement_suggestions && pd.improvement_suggestions.length > 0) {
          formattedResults += `<h4>Improvement Suggestions</h4><ul class="suggestions-list">`;
          pd.improvement_suggestions.forEach(suggestion => {
            formattedResults += `<li>${suggestion}</li>`;
          });
          formattedResults += `</ul>`;
        }
      }
      
      // Add AI insights if available
      if (data.ai_insights && data.ai_insights.response) {
        // Check if response is markdown
        if (typeof data.ai_insights.response === 'string' && 
            (data.ai_insights.response.includes('**') || 
             data.ai_insights.response.includes('#') || 
             data.ai_insights.response.includes('*') || 
             data.ai_insights.response.includes('-'))) {
          
          // Instead of replacing everything, add the formatted metrics first
          displayResults('performance-results', formattedResults);
          
          // Then create a container for the markdown insights
          const container = document.getElementById('performance-results');
          const insightsHeading = document.createElement('h4');
          insightsHeading.textContent = 'AI Recommendations';
          container.appendChild(insightsHeading);
          
          // Create a div for markdown content
          const markdownDiv = document.createElement('div');
          markdownDiv.className = 'markdown-content';
          
          try {
            // Parse markdown with marked
            markdownDiv.innerHTML = marked.parse(data.ai_insights.response);
          } catch (error) {
            console.error('Error parsing markdown:', error);
            // Fallback to simple display
            markdownDiv.innerHTML = `<pre>${data.ai_insights.response}</pre>`;
          }
          
          // Append the parsed content
          container.appendChild(markdownDiv);
          
          // Add custom styles
          addCustomStyles();
          
          // Important: Return here to avoid double-displaying
          return;
        } else {
          formattedResults += `
            <div class="ai-insights">
              <h4>AI Recommendations</h4>
              <p>${data.ai_insights.response}</p>
            </div>
          `;
        }
      }
      
      displayResults('performance-results', formattedResults);
      
      // Add custom styles for the performance metrics
      addCustomStyles();
      
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
    
    try {
      // Check if the results appear to be markdown and not HTML
      const isMarkdown = typeof results === 'string' && 
                         !results.startsWith('<') &&
                         (results.includes('**') || 
                          results.includes('#') || 
                          results.match(/^\s*\*\s+/m) || // Bullet points starting with *
                          results.match(/^\s*-\s+/m) ||  // Bullet points starting with -
                          results.match(/^\s*\d+\.\s+/m) || // Numbered lists
                          results.includes('__') ||
                          results.includes('_'));
                         
      if (isMarkdown) {
        console.log('Content appears to be markdown, attempting to parse');
        
        // Try to parse markdown to HTML using marked library or fallback
        try {
          const htmlContent = marked.parse(results);
          console.log('Markdown parsed successfully');
          
          // Create a div with markdown styling
          const markdownDiv = document.createElement('div');
          markdownDiv.className = 'markdown-content';
          markdownDiv.innerHTML = htmlContent;
          
          // Clear container and append the parsed content
          container.innerHTML = '';
          container.appendChild(markdownDiv);
        } catch (markdownError) {
          console.error('Error parsing markdown:', markdownError);
          // Fallback to simple display with pre-formatting
          container.innerHTML = `<pre>${results}</pre>`;
        }
      } else {
        console.log('Content does not appear to be markdown, displaying as-is');
        // If not markdown or already HTML, just set the innerHTML
        container.innerHTML = results;
      }
    } catch (error) {
      console.error('Error displaying results:', error);
      container.innerHTML = `<p>Error displaying content: ${error.message}</p>`;
      if (typeof results === 'string') {
        container.innerHTML += `<pre>${results}</pre>`;
      }
    }
  }
  
  function addCustomStyles() {
    // Only add styles once
    if (!document.getElementById('custom-grid-styles')) {
      const styleEl = document.createElement('style');
      styleEl.id = 'custom-grid-styles';
      styleEl.textContent = `
        .video-grid {
          display: grid;
          grid-template-columns: 1fr;
          gap: 15px;
          margin-top: 10px;
        }
        
        .video-card {
          border: 1px solid #ddd;
          border-radius: 5px;
          overflow: hidden;
          background: #f9f9f9;
        }
        
        .video-thumbnail img {
          width: 100%;
          height: auto;
        }
        
        .video-info {
          padding: 10px;
        }
        
        .video-info h5 {
          margin: 0 0 5px 0;
          font-size: 14px;
        }
        
        .video-info p {
          margin: 3px 0;
          font-size: 12px;
        }
        
        .metrics-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px;
          margin: 10px 0;
        }
        
        .metric {
          background: #f0f0f0;
          padding: 8px;
          border-radius: 4px;
          text-align: center;
        }
        
        .metric-label {
          display: block;
          font-size: 12px;
          color: #666;
        }
        
        .metric-value {
          display: block;
          font-size: 14px;
          font-weight: bold;
          margin-top: 4px;
        }
        
        .ai-summary, .ai-insights {
          background: #f5f5f5;
          padding: 10px;
          border-left: 3px solid #cc0000;
          margin: 10px 0;
        }
        
        .retention-list, .suggestions-list {
          padding-left: 20px;
          margin: 10px 0;
        }
        
        .idea-card {
          border: 1px solid #ddd;
          border-radius: 5px;
          padding: 10px;
          margin: 10px 0;
          background: #f9f9f9;
        }
        
        .idea-card h5 {
          margin: 0 0 8px 0;
          color: #333;
        }
        
        .idea-card ul {
          margin: 5px 0;
          padding-left: 20px;
        }
        
        .script-template {
          background: #f0f0f0;
          padding: 10px;
          border-radius: 4px;
          margin: 10px 0;
          overflow-x: auto;
        }
        
        .script-template pre {
          margin: 0;
          white-space: pre-wrap;
          font-family: monospace;
          font-size: 12px;
        }
      `;
      document.head.appendChild(styleEl);
    }
  }
}); 