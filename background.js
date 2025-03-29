// Background script for YouTube Content Analyzer
console.log('YouTube Content Analyzer background script loaded');

// API backend URL - Update with your Python backend server URL
const API_URL = 'http://localhost:5000';

// Helper function for showing notifications
function showNotification(title, message) {
  // Check if notifications API is available
  if (chrome.notifications) {
    chrome.notifications.create({
      type: 'basic',
      iconUrl: 'images/icon128.png',
      title: title,
      message: message
    });
  } else {
    console.log(`Notification: ${title} - ${message}`);
  }
}

// Listen for messages from content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'analyzeVideo') {
    // Show notification that analysis is starting
    showNotification('YouTube Content Analyzer', 'Analyzing video...');
    
    // Send data to backend for analysis
    fetch(`${API_URL}/analyze_video`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        video_id: request.videoId,
        video_data: request.videoData
      })
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`Server responded with status: ${response.status}`);
      }
      return response.json();
    })
    .then(data => {
      // Open results in popup
      chrome.storage.local.set({ 'lastAnalysis': data }, () => {
        // Show notification that analysis is complete
        showNotification('YouTube Content Analyzer', 'Analysis complete! Click to see results.');
      });
    })
    .catch(error => {
      console.error('Error:', error);
      // Show error notification
      showNotification('YouTube Content Analyzer', 'Error analyzing video. Please try again.');
    });
  }
  
  return true; // Keep the message channel open for async response
});

// Handle extension installation or update
chrome.runtime.onInstalled.addListener(() => {
  console.log('YouTube Content Analyzer installed');
  
  // Set default settings if needed
  chrome.storage.local.set({
    'settings': {
      'apiKey': '',
      'autoAnalyze': false
    }
  });
}); 