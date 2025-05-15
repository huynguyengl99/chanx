// Module for handling WebSocket endpoints

import { addStatusMessage } from './messages.js';
import { loadPathParameters, updateTabVisibility, parseExistingQueryParams } from './parameters.js';
import { loadMessageExamples } from './messages.js';
import { recursiveToCamel } from './utils.js';

let websocketInfoUrl = '';
let elements;
let state;

// Initialize the endpoints module
export function initEndpoints(infoUrl, domElements, appState) {
    websocketInfoUrl = infoUrl;
    elements = domElements;
    state = appState;

    // Add event listener for endpoint selection
    elements.wsEndpointSelect.addEventListener('change', () => {
        const selectedUrl = elements.wsEndpointSelect.value;
        state.currentEndpoint = selectedUrl;

        // Find the selected endpoint
        const selectedEndpoint = state.availableEndpoints.find(e => e.url === selectedUrl);
        if (selectedEndpoint) {
            // Update the description
            elements.endpointDescription.textContent = selectedEndpoint.description || 'No description available';

            // Set the URL field (prefer friendly URL if available)
            elements.wsUrlInput.value = selectedEndpoint.friendlyUrl || selectedUrl;

            // Load path parameters
            loadPathParameters(selectedEndpoint);

            // Update tab visibility based on whether we have path params
            updateTabVisibility(selectedEndpoint);

            // Load message examples
            loadMessageExamples(selectedUrl);

            // Parse query params
            parseExistingQueryParams();
        } else {
            elements.endpointDescription.textContent = '';
            elements.wsUrlInput.value = selectedUrl;
        }
    });

    // Add event listener for refresh endpoints button
    elements.refreshEndpointsBtn.addEventListener('click', () => loadEndpoints(elements, state));
}

// Load WebSocket endpoints from the server
export async function loadEndpoints(elements, state) {
    try {
        elements.endpointsLoading.style.display = 'flex';
        elements.wsEndpointSelect.disabled = true;

        const response = await fetch(websocketInfoUrl);
        if (!response.ok) {
            throw new Error(`HTTP error ${response.status}`);
        }

        const rawEndpoints = await response.json();
        const endpoints = recursiveToCamel(rawEndpoints);
        state.availableEndpoints = endpoints;

        // Clear existing options
        elements.wsEndpointSelect.innerHTML = '<option value="">-- Select an endpoint --</option>';

        // Add new options
        for (const endpoint of endpoints) {
            const option = document.createElement('option');
            option.value = endpoint.url;
            const displayUrl = endpoint.friendlyUrl || endpoint.url;
            option.textContent = `${endpoint.name} (${displayUrl})`;
            elements.wsEndpointSelect.appendChild(option);
        }

        addStatusMessage(`Loaded ${endpoints.length} WebSocket endpoints`);
    } catch (error) {
        console.error('Error loading endpoints:', error);
        addStatusMessage(`Failed to load endpoints: ${error.message}`, 'error');
    } finally {
        elements.endpointsLoading.style.display = 'none';
        elements.wsEndpointSelect.disabled = false;
    }
}
