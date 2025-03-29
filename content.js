// Content script to interact with YouTube pages
console.log('YouTube Content Analyzer extension loaded');

// Function to extract video data from YouTube page
function extractVideoData() {
  let data = {
    title: '',
    description: '',
    tags: [],
    viewCount: '',
    likeCount: '',
    uploadDate: '',
    channelName: '',
    channelSubscribers: ''
  };
  
  // Get video title
  const titleElement = document.querySelector('h1.ytd-video-primary-info-renderer');
  if (titleElement) {
    data.title = titleElement.textContent.trim();
  }
  
  // Get description
  const descriptionElement = document.querySelector('#description-text');
  if (descriptionElement) {
    data.description = descriptionElement.textContent.trim();
  }
  
  // Get view count
  const viewCountElement = document.querySelector('.view-count');
  if (viewCountElement) {
    data.viewCount = viewCountElement.textContent.trim();
  }
  
  // Get like count (this is tricky as YouTube might not expose it directly)
  const likeButtonElement = document.querySelector('ytd-toggle-button-renderer.ytd-menu-renderer');
  if (likeButtonElement) {
    const likeText = likeButtonElement.querySelector('yt-formatted-string#text');
    if (likeText) {
      data.likeCount = likeText.textContent.trim();
    }
  }
  
  // Get channel name
  const channelNameElement = document.querySelector('#channel-name .ytd-channel-name');
  if (channelNameElement) {
    data.channelName = channelNameElement.textContent.trim();
  }
  
  // Get upload date
  const dateElement = document.querySelector('#info-strings .ytd-video-primary-info-renderer');
  if (dateElement) {
    data.uploadDate = dateElement.textContent.trim();
  }
  
  return data;
}

// Listen for messages from the popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getVideoData') {
    const videoData = extractVideoData();
    sendResponse({ success: true, data: videoData });
  }
  return true; // Keep the message channel open for async response
});

// Inject a button into YouTube pages
function injectAnalyzeButton() {
  // Only inject on video pages
  if (!window.location.href.includes('watch?v=')) {
    return;
  }
  
  // Check if button already exists
  if (document.getElementById('yt-analyzer-btn')) {
    return;
  }
  
  // Create button
  const analyzeButton = document.createElement('button');
  analyzeButton.id = 'yt-analyzer-btn';
  analyzeButton.textContent = 'Analyze Video';
  analyzeButton.style.cssText = `
    background-color: #FF0000;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 8px 12px;
    margin: 10px;
    cursor: pointer;
    font-weight: bold;
  `;
  
  // Add click event
  analyzeButton.addEventListener('click', () => {
    const videoData = extractVideoData();
    const videoId = new URLSearchParams(window.location.search).get('v');
    
    // Send data to background script
    chrome.runtime.sendMessage({
      action: 'analyzeVideo',
      videoId: videoId,
      videoData: videoData
    });
  });
  
  // Find a place to insert the button (below the video)
  const targetElement = document.querySelector('#top-row');
  if (targetElement) {
    targetElement.appendChild(analyzeButton);
  }
}

// Run initialization after page loads
window.addEventListener('load', () => {
  // Wait a bit for dynamic content to load
  setTimeout(injectAnalyzeButton, 2000);
});

// Also run when navigating between YouTube pages
let lastUrl = location.href;
new MutationObserver(() => {
  if (location.href !== lastUrl) {
    lastUrl = location.href;
    setTimeout(injectAnalyzeButton, 2000);
  }
}).observe(document, { subtree: true, childList: true }); 