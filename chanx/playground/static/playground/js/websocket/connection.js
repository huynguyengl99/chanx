// Module for handling WebSocket connections

import {addStatusMessage, addJsonMessage, addMessage, addBinaryMessage} from './messages.js';

// Initialize the connection module
export function initConnection(elements, state) {
    // Add event listeners for connection buttons
    elements.connectBtn.addEventListener('click', () => connectWebSocket(elements, state));
    elements.disconnectBtn.addEventListener('click', () => disconnectWebSocket(elements, state));
}

// Extract the real URL from the display element
function extractRealUrlFromDisplay(displayElement) {
    if (!displayElement || !displayElement.textContent) {
        return null;
    }

    // Real URL is displayed as "Real URL: [actual-url]"
    const match = displayElement.textContent.match(/Real URL: (.+)/);
    return match ? match[1] : null;
}

// Connect to a WebSocket server
function connectWebSocket(elements, state) {
    // First try to get the real URL from the display
    const realUrlFromDisplay = extractRealUrlFromDisplay(elements.realUrlDisplay);

    // If we have a real URL and it's visible (i.e., we have path parameters), use it
    const shouldUseRealUrl = realUrlFromDisplay &&
                             elements.realUrlDisplay &&
                             elements.realUrlDisplay.style.display !== 'none';

    // Determine which URL to use
    const editorUrl = elements.wsUrlInput.value.trim();
    const url = shouldUseRealUrl ? realUrlFromDisplay : editorUrl;

    if (!url) {
        addStatusMessage('Please enter a WebSocket URL', 'error');
        return;
    }

    try {
        state.socket = new WebSocket(url);

        // Connection opened
        state.socket.addEventListener('open', () => {
            updateConnectionStatus(true, elements);
            addStatusMessage('Connected to: ' + url);
        });

        // Listen for messages
        state.socket.addEventListener('message', (event) => {
            if (event.data instanceof Blob) {
                // Handle binary data
                const reader = new FileReader();
                reader.onload = () => {
                    addBinaryMessage(event.data, reader.result, 'received');
                };
                reader.readAsArrayBuffer(event.data);
            } else {
                // Handle text data
                try {
                    // Try to parse as JSON
                    const jsonObj = JSON.parse(event.data);
                    addJsonMessage(jsonObj, 'received');
                } catch (e) {
                    // If not JSON, treat as raw text
                    addMessage(event.data, 'received');
                }
            }
        });

        // Connection closed
        state.socket.addEventListener('close', () => {
            updateConnectionStatus(false, elements);
            addStatusMessage('Disconnected from server');
        });

        // Connection error
        state.socket.addEventListener('error', (event) => {
            updateConnectionStatus(false, elements);
            addStatusMessage('Connection error', 'error');
            console.error('WebSocket error:', event);
        });
    } catch (error) {
        addStatusMessage('Failed to create WebSocket connection: ' + error.message, 'error');
        console.error('WebSocket creation error:', error);
    }
}

// Disconnect from the WebSocket server
function disconnectWebSocket(elements, state) {
    if (state.socket) {
        state.socket.close();
        state.socket = null;
    }
}

// Update connection status UI
export function updateConnectionStatus(isConnected, elements) {
    elements.connectBtn.disabled = isConnected;
    elements.disconnectBtn.disabled = !isConnected;
    elements.messageInput.disabled = !isConnected;
    elements.jsonInput.disabled = !isConnected;
    elements.fileInput.disabled = !isConnected;
    elements.sendRawBtn.disabled = !isConnected;
    elements.formatJsonBtn.disabled = !isConnected;
    elements.sendJsonBtn.disabled = !isConnected;
    elements.sendFileBtn.disabled = !isConnected;
    elements.messageExampleSelect.disabled = !isConnected;

    if (isConnected) {
        elements.connectionStatus.textContent = 'Connected';
        elements.connectionStatus.className = 'status connected';
    } else {
        elements.connectionStatus.textContent = 'Disconnected';
        elements.connectionStatus.className = 'status disconnected';
    }
}
