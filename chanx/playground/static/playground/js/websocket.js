// The websocket_info_url will be passed from the HTML template
function initWebSocketPlayground(websocketInfoUrl) {
    // DOM Elements
    const wsEndpointSelect = document.getElementById('wsEndpoint');
    const endpointDescription = document.getElementById('endpointDescription');
    const endpointsLoading = document.getElementById('endpointsLoading');
    const refreshEndpointsBtn = document.getElementById('refreshEndpoints');
    const wsUrlInput = document.getElementById('wsUrl');
    const connectBtn = document.getElementById('connectBtn');
    const disconnectBtn = document.getElementById('disconnectBtn');
    const connectionStatus = document.getElementById('connectionStatus');
    const messageInput = document.getElementById('messageInput');
    const jsonInput = document.getElementById('jsonInput');
    const fileInput = document.getElementById('fileInput');
    const fileInfo = document.getElementById('fileInfo');
    const jsonError = document.getElementById('jsonError');
    const sendRawBtn = document.getElementById('sendRawBtn');
    const formatJsonBtn = document.getElementById('formatJsonBtn');
    const sendJsonBtn = document.getElementById('sendJsonBtn');
    const sendFileBtn = document.getElementById('sendFileBtn');
    const messageLog = document.getElementById('messageLog');
    const tabs = document.querySelectorAll('.tab');
    const tabContents = document.querySelectorAll('.tab-content');

    // DOM elements for connection tabs
    const connectionTabButtons = document.querySelectorAll('.tab-button');
    const connectionTabContents = document.querySelectorAll('.connection-tab-content');

    // DOM elements for query params
    const queryParamsList = document.getElementById('queryParamsList');
    const addQueryParamBtn = document.getElementById('addQueryParamBtn');

    // Message Examples Elements
    const messageExampleSelect = document.getElementById('messageExampleSelect');
    const messageExampleDescription = document.getElementById('messageExampleDescription');
    const messageExamplesLoading = document.getElementById('messageExamplesLoading');

    let currentEndpoint = null;

    // WebSocket instance
    let socket = null;
    let selectedFile = null;
    let availableEndpoints = [];

    // Load WebSocket endpoints from the server
    async function loadEndpoints() {
        try {
            endpointsLoading.style.display = 'flex';
            wsEndpointSelect.disabled = true;

            const response = await fetch(websocketInfoUrl);
            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}`);
            }

            const endpoints = await response.json();
            availableEndpoints = endpoints;

            // Clear existing options
            wsEndpointSelect.innerHTML = '<option value="">-- Select an endpoint --</option>';

            // Add new options
            for (const endpoint of endpoints) {
                const option = document.createElement('option');
                option.value = endpoint.url;
                option.textContent = `${endpoint.name} (${endpoint.url})`;
                wsEndpointSelect.appendChild(option);
            }

            addStatusMessage(`Loaded ${endpoints.length} WebSocket endpoints`);
        } catch (error) {
            console.error('Error loading endpoints:', error);
            addStatusMessage(`Failed to load endpoints: ${error.message}`, 'error');
        } finally {
            endpointsLoading.style.display = 'none';
            wsEndpointSelect.disabled = false;
        }
    }

    // Initialize by loading endpoints
    loadEndpoints();

    // Refresh endpoints when button is clicked
    refreshEndpointsBtn.addEventListener('click', loadEndpoints);

    // Load message examples into the select dropdown
    function loadMessageExamples(endpointUrl) {
        // Clear existing options
        messageExampleSelect.innerHTML = '<option value="">-- Select a message type --</option>';
        messageExampleDescription.textContent = '';

        // Find the selected endpoint in available endpoints
        const selectedEndpoint = availableEndpoints.find(endpoint => endpoint.url === endpointUrl);

        if (!selectedEndpoint || !selectedEndpoint.message_examples || selectedEndpoint.message_examples.length === 0) {
            messageExampleSelect.disabled = true;
            addStatusMessage("No message examples available for this endpoint", "status");
            return;
        }

        // Enable the select and add options
        messageExampleSelect.disabled = false;

        // Add new options
        for (const example of selectedEndpoint.message_examples) {
            const option = document.createElement('option');
            option.value = example.name;
            option.textContent = example.name;
            messageExampleSelect.appendChild(option);
        }

        addStatusMessage(`Loaded ${selectedEndpoint.message_examples.length} message examples`);
    }

    // Update the JSON input when a message example is selected
    messageExampleSelect.addEventListener('change', () => {
        const selectedName = messageExampleSelect.value;
        if (!selectedName) {
            jsonInput.value = '';
            messageExampleDescription.textContent = '';
            return;
        }

        const selectedEndpoint = availableEndpoints.find(endpoint => endpoint.url === currentEndpoint);
        if (!selectedEndpoint || !selectedEndpoint.message_examples) {
            return;
        }

        const example = selectedEndpoint.message_examples.find(ex => ex.name === selectedName);
        if (example) {
            jsonInput.value = JSON.stringify(example.example, null, 2);
            messageExampleDescription.textContent = example.description || '';
        }
    });

    // Tab functionality
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Remove active class from all tabs and contents
            tabs.forEach(t => t.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            // Add active class to selected tab and content
            tab.classList.add('active');
            const tabId = 'tab-' + tab.getAttribute('data-tab');
            document.getElementById(tabId).classList.add('active');
        });
    });

    // Connect to WebSocket
    connectBtn.addEventListener('click', () => {
        const url = wsUrlInput.value.trim();
        if (!url) {
            addStatusMessage('Please enter a WebSocket URL', 'error');
            return;
        }

        try {
            socket = new WebSocket(url);

            // Connection opened
            socket.addEventListener('open', (event) => {
                updateConnectionStatus(true);
                addStatusMessage('Connected to: ' + url);
            });

            // Listen for messages
            socket.addEventListener('message', (event) => {
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
            socket.addEventListener('close', (event) => {
                updateConnectionStatus(false);
                addStatusMessage('Disconnected from server');
            });

            // Connection error
            socket.addEventListener('error', (event) => {
                updateConnectionStatus(false);
                addStatusMessage('Connection error', 'error');
                console.error('WebSocket error:', event);
            });
        } catch (error) {
            addStatusMessage('Failed to create WebSocket connection: ' + error.message, 'error');
            console.error('WebSocket creation error:', error);
        }
    });

    // Disconnect from WebSocket
    disconnectBtn.addEventListener('click', () => {
        if (socket) {
            socket.close();
            socket = null;
        }
    });

    // Send a raw text message
    sendRawBtn.addEventListener('click', () => {
        const message = messageInput.value.trim();
        if (!message) {
            return;
        }

        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(message);
            addMessage(message, 'sent');
            messageInput.value = '';
        } else {
            addStatusMessage('Not connected to a WebSocket server', 'error');
        }
    });

    // Format JSON button
    formatJsonBtn.addEventListener('click', () => {
        const jsonText = jsonInput.value.trim();
        if (!jsonText) return;

        try {
            const parsed = JSON.parse(jsonText);
            jsonInput.value = JSON.stringify(parsed, null, 2);
            jsonError.textContent = '';
        } catch (e) {
            jsonError.textContent = 'Invalid JSON: ' + e.message;
        }
    });

    // Send a JSON message
    sendJsonBtn.addEventListener('click', () => {
        const jsonText = jsonInput.value.trim();
        if (!jsonText) {
            return;
        }

        try {
            const jsonObj = JSON.parse(jsonText);

            if (socket && socket.readyState === WebSocket.OPEN) {
                const jsonString = JSON.stringify(jsonObj);
                socket.send(jsonString);
                addJsonMessage(jsonObj, 'sent');
            } else {
                addStatusMessage('Not connected to a WebSocket server', 'error');
            }
        } catch (e) {
            jsonError.textContent = 'Invalid JSON: ' + e.message;
        }
    });

    // Handle file selection
    fileInput.addEventListener('change', (event) => {
        selectedFile = event.target.files[0];
        if (selectedFile) {
            const size = formatFileSize(selectedFile.size);
            fileInfo.innerHTML = `Selected: <span class="file-name">${selectedFile.name}</span> (<span class="file-size">${size}</span>)`;
        } else {
            fileInfo.textContent = '';
        }
    });

    // Send a file
    sendFileBtn.addEventListener('click', () => {
        if (!selectedFile) {
            addStatusMessage('Please select a file first', 'error');
            return;
        }

        if (socket && socket.readyState === WebSocket.OPEN) {
            // Create a reader to read the file as ArrayBuffer
            const reader = new FileReader();

            reader.onload = function (e) {
                // The result is an ArrayBuffer
                const arrayBuffer = e.target.result;

                // Send the binary data to the WebSocket server
                socket.send(arrayBuffer);

                // Add to message log
                addBinaryMessage(selectedFile, arrayBuffer, 'sent');

                // Clear the file input
                fileInput.value = '';
                fileInfo.textContent = '';
                selectedFile = null;
            };

            reader.readAsArrayBuffer(selectedFile);
        } else {
            addStatusMessage('Not connected to a WebSocket server', 'error');
        }
    });

    // Update connection status UI
    function updateConnectionStatus(isConnected) {
        connectBtn.disabled = isConnected;
        disconnectBtn.disabled = !isConnected;
        messageInput.disabled = !isConnected;
        jsonInput.disabled = !isConnected;
        fileInput.disabled = !isConnected;
        sendRawBtn.disabled = !isConnected;
        formatJsonBtn.disabled = !isConnected;
        sendJsonBtn.disabled = !isConnected;
        sendFileBtn.disabled = !isConnected;
        messageExampleSelect.disabled = !isConnected;

        if (isConnected) {
            connectionStatus.textContent = 'Connected';
            connectionStatus.className = 'status connected';
        } else {
            connectionStatus.textContent = 'Disconnected';
            connectionStatus.className = 'status disconnected';
        }
    }

    // Add a raw text message to the log
    function addMessage(message, type) {
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
        messageLog.insertBefore(messageElement, messageLog.firstChild);
    }

    // Add a JSON message to the log with syntax highlighting
    function addJsonMessage(jsonObj, type) {
        const timestamp = new Date().toLocaleTimeString();
        const directionIcon = type === 'sent' ?
            '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 2L11 13"></path><path d="M22 2L15 22L11 13L2 9L22 2Z"></path></svg>' :
            '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 15L13 6"></path><path d="M22 15H17V10"></path><path d="M2 9L22 2L15 22L2 9Z"></path></svg>';

        const directionText = type === 'sent' ? 'Sent' : 'Received';

        // Stringify the JSON in two formats:
        // 1. Single line with no spaces for collapsed view
        const compactJson = JSON.stringify(jsonObj);

        // 2. Pretty printed with indentation for expanded view
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
                <div class="message-content collapsible">
                    <pre>${displayJson}</pre>
                </div>
                <div class="message-expand">Expand</div>
                <div class="message-content" style="display: none;">
                    <pre>${prettyJsonHighlighted}</pre>
                </div>
            `;

        // Add expand/collapse functionality
        const expandButton = messageElement.querySelector('.message-expand');
        const collapsedContent = messageElement.querySelector('.message-content.collapsible');
        const expandedContent = messageElement.querySelector('.message-content:not(.collapsible)');

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
        messageLog.insertBefore(messageElement, messageLog.firstChild);
    }

    // Add a binary message to the log
    function addBinaryMessage(file, arrayBuffer, type) {
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
        messageLog.insertBefore(messageElement, messageLog.firstChild);
    }

    // Add a status message to the log
    function addStatusMessage(message, type = '') {
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
        messageLog.insertBefore(messageElement, messageLog.firstChild);
    }

    // Format file size
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';

        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));

        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // JSON syntax highlighting
    function syntaxHighlightJson(json) {
        json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
            let cls = 'json-number';
            if (/^"/.test(match)) {
                if (/:$/.test(match)) {
                    cls = 'json-key';
                } else {
                    cls = 'json-string';
                }
            } else if (/true|false/.test(match)) {
                cls = 'json-boolean';
            } else if (/null/.test(match)) {
                cls = 'json-null';
            }
            return '<span class="' + cls + '">' + match + '</span>';
        });
    }

    connectionTabButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Remove active class from all tabs and contents
            connectionTabButtons.forEach(btn => btn.classList.remove('active'));
            connectionTabContents.forEach(content => content.classList.remove('active'));

            // Add active class to selected tab and content
            button.classList.add('active');
            const tabId = button.getAttribute('data-tab');
            document.getElementById(tabId).classList.add('active');
        });
    });

    // Add query parameter row
    addQueryParamBtn.addEventListener('click', () => {
        addParamRow(queryParamsList);
    });

    function addParamRow(container) {
        const row = document.createElement('div');
        row.className = 'param-row';

        row.innerHTML = `
                <input type="text" class="param-key-input" placeholder="Key">
                <input type="text" class="param-value-input" placeholder="Value">
                <input type="text" class="param-desc-input" placeholder="Description">
                <div class="param-actions">
                    <button class="remove-param">×</button>
                </div>
            `;

        // Add event listener to remove button
        const removeBtn = row.querySelector('.remove-param');
        removeBtn.addEventListener('click', () => {
            container.removeChild(row);
            updateWebSocketUrl();
        });

        // Add event listeners to inputs for URL updating
        const inputs = row.querySelectorAll('input');
        inputs.forEach(input => {
            input.addEventListener('input', updateWebSocketUrl);
        });

        container.appendChild(row);
    }

    // Function to collect query parameters
    function getQueryParams() {
        const params = [];
        const rows = queryParamsList.querySelectorAll('.param-row');

        rows.forEach(row => {
            const keyInput = row.querySelector('.param-key-input');
            const valueInput = row.querySelector('.param-value-input');

            const key = keyInput.value.trim();
            const value = valueInput.value.trim();

            if (key && value) {
                params.push({key, value});
            }
        });

        return params;
    }

    // Update WebSocket URL with query parameters
    function updateWebSocketUrl() {
        const baseUrl = wsUrlInput.value.split('?')[0];
        const params = getQueryParams();

        if (params.length > 0) {
            const queryString = params
                .map(param => `${encodeURIComponent(param.key)}=${encodeURIComponent(param.value)}`)
                .join('&');

            wsUrlInput.value = `${baseUrl}?${queryString}`;
        } else {
            wsUrlInput.value = baseUrl;
        }
    }

    // Initialize by adding one row to each container
    addParamRow(queryParamsList);

    // Update URL when endpoint is selected (modified to work with query params)
    wsEndpointSelect.addEventListener('change', () => {
        const selectedUrl = wsEndpointSelect.value;
        wsUrlInput.value = selectedUrl;
        currentEndpoint = selectedUrl; // Store the current endpoint URL
        updateWebSocketUrl();

        // Update the description
        const selectedEndpoint = availableEndpoints.find(e => e.url === selectedUrl);
        if (selectedEndpoint) {
            endpointDescription.textContent = selectedEndpoint.description || 'No description available';

            // Load message examples for this endpoint
            loadMessageExamples(selectedUrl);
        } else {
            endpointDescription.textContent = '';
        }
    });

    // Add an event listener to all wsUrlInput to update when manually changed
    wsUrlInput.addEventListener('change', () => {
        // Parse existing query params from the URL and populate the UI
        try {
            const url = new URL(wsUrlInput.value);
            const params = Array.from(url.searchParams.entries());

            // Clear existing query params UI
            while (queryParamsList.firstChild) {
                queryParamsList.removeChild(queryParamsList.firstChild);
            }

            // Add UI for each param
            if (params.length > 0) {
                params.forEach(([key, value]) => {
                    const row = document.createElement('div');
                    row.className = 'param-row';

                    row.innerHTML = `
                            <input type="text" class="param-key-input" value="${key}" placeholder="Key">
                            <input type="text" class="param-value-input" value="${value}" placeholder="Value">
                            <input type="text" class="param-desc-input" placeholder="Description">
                            <div class="param-actions">
                                <button class="remove-param">×</button>
                            </div>
                        `;

                    // Add event listener to remove button
                    const removeBtn = row.querySelector('.remove-param');
                    removeBtn.addEventListener('click', () => {
                        queryParamsList.removeChild(row);
                        updateWebSocketUrl();
                    });

                    // Add event listeners to inputs for URL updating
                    const inputs = row.querySelectorAll('input');
                    inputs.forEach(input => {
                        input.addEventListener('input', updateWebSocketUrl);
                    });

                    queryParamsList.appendChild(row);
                });
            } else {
                // Add one empty row if no params found
                addParamRow(queryParamsList);
            }
        } catch (error) {
            // If URL parsing fails, keep the UI as is
            console.warn('Failed to parse WebSocket URL:', error);
        }
    });

    // Initial call to set up the UI
    document.addEventListener('DOMContentLoaded', () => {
        // Initialize with one empty row for each container
        while (queryParamsList.firstChild) {
            queryParamsList.removeChild(queryParamsList.firstChild);
        }

        addParamRow(queryParamsList);
    });

    // Initialize with a status message
    addStatusMessage('WebSocket Playground Ready');
}

// Export the initialization function
window.initWebSocketPlayground = initWebSocketPlayground;
