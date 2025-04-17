// Main entry point for WebSocket Playground
// This file serves as the initialization point for the application

// Import all module files
import { initMain } from './websocket/main.js';

// Export the initialization function to be called from the HTML template
window.initWebSocketPlayground = function(websocketInfoUrl) {
    // Initialize the WebSocket playground with configuration
    initMain(websocketInfoUrl);
};
