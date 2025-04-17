// Module for handling path and query parameters

import {addStatusMessage} from './messages.js';

// Cache DOM elements and state
let elements;
let state;

// Initialize the parameters module
export function initParameters(domElements, appState) {
    elements = domElements;
    state = appState;

    // Add event listener to query parameter button
    elements.addQueryParamBtn.addEventListener('click', () => {
        addQueryParamRow(elements.queryParamsList);
    });

    // Add event listener to URL input for parsing query parameters
    elements.wsUrlInput.addEventListener('change', parseExistingQueryParams);

    // Initialize with one empty row for query parameters
    document.addEventListener('DOMContentLoaded', () => {
        // Clear existing rows
        while (elements.queryParamsList.firstChild) {
            elements.queryParamsList.removeChild(elements.queryParamsList.firstChild);
        }

        addQueryParamRow(elements.queryParamsList);
    });
}

// When loading path parameters
export function loadPathParameters(endpoint) {
    // Clear existing path parameters
    elements.pathParamsList.innerHTML = '';

    // If no endpoint is selected or no path params, show empty state
    if (!endpoint || !endpoint.path_params || endpoint.path_params.length === 0) {
        // Add a placeholder message in the path params list
        const emptyState = document.createElement('div');
        emptyState.className = 'empty-params-state';
        emptyState.textContent = 'No path parameters for this endpoint.';
        elements.pathParamsList.appendChild(emptyState);
        return;
    }

    // Add UI for each path parameter
    endpoint.path_params.forEach(param => {
        addPathParamRow(elements.pathParamsList, param);
    });

    // Store the original pattern for replacements
    state.originalPathPattern = endpoint.url;

    // Initialize with friendly URL if available
    if (endpoint.friendly_url) {
        elements.wsUrlInput.value = endpoint.friendly_url;
    }
}

// Add path parameter row
function addPathParamRow(container, param) {
    const row = document.createElement('div');
    row.className = 'param-row';

    row.innerHTML = `
        <input type="text" class="param-key-input" value="${param.name}" placeholder="Parameter" readonly>
        <input type="text" class="param-value-input" placeholder="Value" data-param-name="${param.name}">
        <input type="text" class="param-desc-input" value="${param.description || ''}" placeholder="Description" readonly>
        <div class="param-actions">
            <span class="param-pattern" title="Pattern: ${param.pattern || ''}">${param.pattern || ''}</span>
        </div>
    `;

    // Add event listener to value input for URL updating
    const valueInput = row.querySelector('.param-value-input');
    valueInput.addEventListener('input', updateWebSocketUrlWithPathParams);

    container.appendChild(row);
}

// Add query parameter row
function addQueryParamRow(container) {
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
    const rows = elements.queryParamsList.querySelectorAll('.param-row');

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

// Update WebSocket URL with path parameters
export function updateWebSocketUrlWithPathParams() {
    if (!state.originalPathPattern) return;

    let updatedPath = state.originalPathPattern;
    const pathParamValues = {};

    // Collect path parameter values
    const paramInputs = elements.pathParamsList.querySelectorAll('.param-value-input');
    paramInputs.forEach(input => {
        const paramName = input.getAttribute('data-param-name');
        const paramValue = input.value.trim();
        pathParamValues[paramName] = paramValue;
    });

    // Replace parameters in the URL
    for (const [paramName, paramValue] of Object.entries(pathParamValues)) {
        // Replace either :paramName or (?P<paramName>pattern)
        const regexPattern = new RegExp(`(\\(\\?P<${paramName}>[^)]+\\)|:${paramName})`, 'g');
        updatedPath = updatedPath.replace(regexPattern, paramValue || `:${paramName}`);
    }

    // Update the URL input
    elements.wsUrlInput.value = updatedPath;

    // Then apply query parameters
    updateWebSocketUrl();
}

// Update WebSocket URL with query parameters
export function updateWebSocketUrl() {
    const baseUrl = elements.wsUrlInput.value.split('?')[0];
    const params = getQueryParams();

    if (params.length > 0) {
        const queryString = params
            .map(param => `${encodeURIComponent(param.key)}=${encodeURIComponent(param.value)}`)
            .join('&');

        elements.wsUrlInput.value = `${baseUrl}?${queryString}`;
    } else {
        elements.wsUrlInput.value = baseUrl;
    }
}

// When no endpoint has path parameters, show Query Params tab as active
export function updateTabVisibility(endpoint) {
    // Check if the endpoint has path parameters
    const hasPathParams = endpoint && endpoint.path_params && endpoint.path_params.length > 0;

    // Get the tab buttons
    const pathParamsTab = document.querySelector('.tab-button[data-tab="connection-path-params"]');
    const queryParamsTab = document.querySelector('.tab-button[data-tab="connection-params"]');

    // Get the tab content elements
    const pathParamsContent = document.getElementById('connection-path-params');
    const queryParamsContent = document.getElementById('connection-params');

    if (!hasPathParams) {
        // If no path params, make Query Params tab active
        pathParamsTab.classList.remove('active');
        queryParamsTab.classList.add('active');

        pathParamsContent.classList.remove('active');
        queryParamsContent.classList.add('active');
    }
}

// Parse existing query parameters from the URL
export function parseExistingQueryParams() {
    try {
        const url = new URL(elements.wsUrlInput.value);
        const params = Array.from(url.searchParams.entries());

        // Clear existing query params UI
        while (elements.queryParamsList.firstChild) {
            elements.queryParamsList.removeChild(elements.queryParamsList.firstChild);
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
                    elements.queryParamsList.removeChild(row);
                    updateWebSocketUrl();
                });

                // Add event listeners to inputs for URL updating
                const inputs = row.querySelectorAll('input');
                inputs.forEach(input => {
                    input.addEventListener('input', updateWebSocketUrl);
                });

                elements.queryParamsList.appendChild(row);
            });
        } else {
            // Add one empty row if no params found
            addQueryParamRow(elements.queryParamsList);
        }
    } catch (error) {
        // If URL parsing fails, keep the UI as is
        console.warn('Failed to parse WebSocket URL:', error);
    }
}
