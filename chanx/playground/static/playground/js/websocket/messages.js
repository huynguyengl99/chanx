// Module for handling WebSocket messages

import { formatFileSize, syntaxHighlightJson } from './utils.js';

// Module-scope references
let elements;
let state;

// Initialize the messaging module
export function initMessaging(domElements, appState) {
    elements = domElements;
    state = appState;

    // Send a raw text message
    elements.sendRawBtn.addEventListener('click', () => {
        const message = elements.messageInput.value.trim();
        if (!message) {
            return;
        }

        if (state.socket && state.socket.readyState === WebSocket.OPEN) {
            state.socket.send(message);
            addMessage(message, 'sent');
            elements.messageInput.value = '';
        } else {
            addStatusMessage('Not connected to a WebSocket server', 'error');
        }
    });

    // Format JSON button
    elements.formatJsonBtn.addEventListener('click', () => {
        const jsonText = elements.jsonInput.value.trim();
        if (!jsonText) return;

        try {
            const parsed = JSON.parse(jsonText);
            elements.jsonInput.value = JSON.stringify(parsed, null, 2);
            elements.jsonError.textContent = '';
        } catch (e) {
            elements.jsonError.textContent = 'Invalid JSON: ' + e.message;
        }
    });

    // Send a JSON message
    elements.sendJsonBtn.addEventListener('click', () => {
        const jsonText = elements.jsonInput.value.trim();
        if (!jsonText) {
            return;
        }

        try {
            const jsonObj = JSON.parse(jsonText);

            if (state.socket && state.socket.readyState === WebSocket.OPEN) {
                const jsonString = JSON.stringify(jsonObj);
                state.socket.send(jsonString);
                addJsonMessage(jsonObj, 'sent');
            } else {
                addStatusMessage('Not connected to a WebSocket server', 'error');
            }
        } catch (e) {
            elements.jsonError.textContent = 'Invalid JSON: ' + e.message;
        }
    });

    // Handle file selection
    elements.fileInput.addEventListener('change', (event) => {
        state.selectedFile = event.target.files[0];
        if (state.selectedFile) {
            const size = formatFileSize(state.selectedFile.size);
            elements.fileInfo.innerHTML = `Selected: <span class="file-name">${state.selectedFile.name}</span> (<span class="file-size">${size}</span>)`;
        } else {
            elements.fileInfo.textContent = '';
        }
    });

    // Send a file
    elements.sendFileBtn.addEventListener('click', () => {
        if (!state.selectedFile) {
            addStatusMessage('Please select a file first', 'error');
            return;
        }

        if (state.socket && state.socket.readyState === WebSocket.OPEN) {
            const reader = new FileReader();

            reader.onload = function (e) {
                // The result is an ArrayBuffer
                const arrayBuffer = e.target.result;

                // Send the binary data to the WebSocket server
                state.socket.send(arrayBuffer);

                // Add to message log
                addBinaryMessage(state.selectedFile, arrayBuffer, 'sent');

                // Clear the file input
                elements.fileInput.value = '';
                elements.fileInfo.textContent = '';
                state.selectedFile = null;
            };

            reader.readAsArrayBuffer(state.selectedFile);
        } else {
            addStatusMessage('Not connected to a WebSocket server', 'error');
        }
    });

    // Setup message examples dropdown
    elements.messageExampleSelect.addEventListener('change', () => {
        const selectedName = elements.messageExampleSelect.value;
        if (!selectedName) {
            elements.jsonInput.value = '';
            elements.messageExampleDescription.textContent = '';
            return;
        }

        const selectedEndpoint = state.availableEndpoints.find(endpoint => endpoint.url === state.currentEndpoint);
        if (!selectedEndpoint || !selectedEndpoint.messageExamples) {
            return;
        }

        const example = selectedEndpoint.messageExamples.find(ex => ex.name === selectedName);
        if (example) {
            elements.jsonInput.value = JSON.stringify(example.example, null, 2);
            elements.messageExampleDescription.textContent = example.description || '';
        }
    });
}

// Load message examples for the selected endpoint
export function loadMessageExamples(endpointUrl) {
    // Clear existing options
    elements.messageExampleSelect.innerHTML = '<option value="">-- Select a message type --</option>';
    elements.messageExampleDescription.textContent = '';

    // Find the selected endpoint in available endpoints
    const selectedEndpoint = state.availableEndpoints.find(endpoint => endpoint.url === endpointUrl);

    if (!selectedEndpoint || !selectedEndpoint.messageExamples || selectedEndpoint.messageExamples.length === 0) {
        elements.messageExampleSelect.disabled = true;
        addStatusMessage("No message examples available for this endpoint", "status");
        return;
    }

    // Enable the select and add options
    elements.messageExampleSelect.disabled = false;

    // Add new options
    for (const example of selectedEndpoint.messageExamples) {
        const option = document.createElement('option');
        option.value = example.name;
        option.textContent = example.name;
        elements.messageExampleSelect.appendChild(option);
    }

    addStatusMessage(`Loaded ${selectedEndpoint.messageExamples.length} message examples`);
}

// Add a raw text message to the log
export function addMessage(message, type) {
    const timestamp = new Date().toLocaleTimeString();
    const directionIcon = type === 'sent' ?
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 2L11 13"></path><path d="M22 2L15 22L11 13L2 9L22 2Z"></path></svg>' :
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 15L13 6"></path><path d="M22 15H17V10"></path><path d="M2 9L22 2L15 22L2 9Z"></path></svg>';

    const directionText = type === 'sent' ? 'Sent' : 'Received';

    const messageElement = document.createElement('div');
    messageElement.className = `message ${type}`;
    messageElement.innerHTML = `
        <div class="message-header">
            <div class="message-direction">${directionIcon} ${directionText}</div>
            <div class="message-timestamp">${timestamp}</div>
        </div>
        <div class="message-content">
            ${message}
        </div>
    `;

    // Add at the top of the log (newest first)
    elements.messageLog.insertBefore(messageElement, elements.messageLog.firstChild);
}

// Add a JSON message to the log with syntax highlighting
export function addJsonMessage(jsonObj, type) {
    const timestamp = new Date().toLocaleTimeString();
    const directionIcon = type === 'sent' ?
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 2L11 13"></path><path d="M22 2L15 22L11 13L2 9L22 2Z"></path></svg>' :
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 15L13 6"></path><path d="M22 15H17V10"></path><path d="M2 9L22 2L15 22L2 9Z"></path></svg>';

    const directionText = type === 'sent' ? 'Sent' : 'Received';

    // Stringify the JSON in two formats
    const compactJson = JSON.stringify(jsonObj);
    const prettyJson = JSON.stringify(jsonObj, null, 2);

    // Create a shortened version with ellipsis for very long messages
    const MAX_PREVIEW_LENGTH = 100;
    let displayJson = compactJson;
    if (compactJson.length > MAX_PREVIEW_LENGTH) {
        displayJson = compactJson.substring(0, MAX_PREVIEW_LENGTH) + '...';
    }

    const messageElement = document.createElement('div');
    messageElement.className = `message ${type}`;

    const prettyJsonHighlighted = syntaxHighlightJson(prettyJson);

    messageElement.innerHTML = `
        <div class="message-header">
            <div class="message-direction">${directionIcon} ${directionText} JSON</div>
            <div class="message-timestamp">${timestamp}</div>
        </div>
        <div class="message-content">
            <pre>${displayJson}</pre>
        </div>
        <div class="message-expand">Expand</div>
        <div class="message-content" style="display: none;">
            <pre>${prettyJsonHighlighted}</pre>
        </div>
    `;

    // Add expand/collapse functionality
    const expandButton = messageElement.querySelector('.message-expand');
    const collapsedContent = messageElement.querySelector('.message-content:not([style])');
    const expandedContent = messageElement.querySelector('.message-content[style]');

    expandButton.addEventListener('click', () => {
        if (expandedContent.style.display === 'none') {
            expandedContent.style.display = 'block';
            collapsedContent.style.display = 'none';
            expandButton.textContent = 'Collapse';
        } else {
            expandedContent.style.display = 'none';
            collapsedContent.style.display = 'block';
            expandButton.textContent = 'Expand';
        }
    });

    // Add at the top of the log (newest first)
    elements.messageLog.insertBefore(messageElement, elements.messageLog.firstChild);
}

// Add a binary message to the log
export function addBinaryMessage(file, arrayBuffer, type) {
    const timestamp = new Date().toLocaleTimeString();
    const directionIcon = type === 'sent' ?
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 2L11 13"></path><path d="M22 2L15 22L11 13L2 9L22 2Z"></path></svg>' :
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 15L13 6"></path><path d="M22 15H17V10"></path><path d="M2 9L22 2L15 22L2 9Z"></path></svg>';

    const directionText = type === 'sent' ? 'Sent' : 'Received';

    let content = '';
    if (file instanceof File) {
        content = `File: ${file.name} (${formatFileSize(file.size)})`;
    } else if (file instanceof Blob) {
        content = `Binary data (${formatFileSize(file.size)})`;
    }

    const messageElement = document.createElement('div');
    messageElement.className = `message ${type}`;
    messageElement.innerHTML = `
        <div class="message-header">
            <div class="message-direction">${directionIcon} ${directionText} Binary</div>
            <div class="message-timestamp">${timestamp}</div>
        </div>
        <div class="message-content">
            ${content}
        </div>
    `;

    // Add at the top of the log (newest first)
    elements.messageLog.insertBefore(messageElement, elements.messageLog.firstChild);
}

// Add a status message to the log
export function addStatusMessage(message, type = '') {
    const timestamp = new Date().toLocaleTimeString();

    const messageElement = document.createElement('div');
    messageElement.className = `message status ${type}`;
    messageElement.innerHTML = `
        <div class="message-header">
            <div class="message-direction">System</div>
            <div class="message-timestamp">${timestamp}</div>
        </div>
        <div class="message-content">
            ${message}
        </div>
    `;

    // Add at the top of the log (newest first)
    elements.messageLog.insertBefore(messageElement, elements.messageLog.firstChild);
}
