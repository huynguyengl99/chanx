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

    // Add event listener to path parameter button
    elements.addPathParamBtn.addEventListener('click', () => {
        addPathParamRow(elements.pathParamsList, {name: '', pattern: '', description: ''});
        updateUrlPlaceholdersWithTrailingSlash();
    });

    // Add event listener to URL input for parsing both path and query parameters
    elements.wsUrlInput.addEventListener('change', () => {
        parseUrlAndUpdateParams();
        updateRealUrlDisplay();
    });

    // Initialize with one empty row for query parameters
    document.addEventListener('DOMContentLoaded', () => {
        while (elements.queryParamsList.firstChild) {
            elements.queryParamsList.removeChild(elements.queryParamsList.firstChild);
        }
        addQueryParamRow(elements.queryParamsList);
    });
}

// Validate path parameter value against its pattern
function validatePathParam(value, pattern) {
    if (!pattern || !value) {
        return {isValid: true, message: ''};
    }

    try {
        const regex = new RegExp(`^${pattern}$`);
        const isValid = regex.test(value);

        if (!isValid) {
            let message = `Value doesn't match expected pattern: ${pattern}`;

            // Provide user-friendly messages for common patterns
            if (pattern === '[0-9]+' || pattern === '\\d+') {
                message = 'Value must be a number (e.g., 123)';
            } else if (pattern === '[^/]+') {
                message = 'Value cannot contain forward slashes';
            } else if (pattern === '[-a-zA-Z0-9_]+') {
                message = 'Value must be alphanumeric with hyphens and underscores only';
            } else if (pattern === '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}') {
                message = 'Value must be a valid UUID';
            }

            return {isValid: false, message};
        }

        return {isValid: true, message: ''};
    } catch (error) {
        console.error('Regex error:', error);
        return {isValid: false, message: 'Invalid value for this parameter'};
    }
}

// Show/hide validation warning for a parameter row
function showValidationWarning(row, message) {
    const existingWarning = row.querySelector('.param-validation-warning');
    if (existingWarning) {
        existingWarning.remove();
    }

    const valueInput = row.querySelector('.param-value-input');

    if (message) {
        const warning = document.createElement('div');
        warning.className = 'param-validation-warning';
        warning.textContent = message;

        // Insert after the param-row
        row.appendChild(warning);
        valueInput.classList.add('param-error');
    } else {
        valueInput.classList.remove('param-error');
    }
}

// When loading path parameters
export function loadPathParameters(endpoint) {
    elements.pathParamsList.innerHTML = '';

    if (!endpoint || !endpoint.pathParams || endpoint.pathParams.length === 0) {
        const emptyState = document.createElement('div');
        emptyState.className = 'empty-params-state';
        emptyState.textContent = 'No path parameters for this endpoint.';
        elements.pathParamsList.appendChild(emptyState);

        if (elements.realUrlDisplay) {
            elements.realUrlDisplay.style.display = 'none';
        }
        return;
    }

    state.originalPathPattern = endpoint.url;
    state.pathParameters = endpoint.pathParams;

    // Make sure each param has the pattern properly set
    endpoint.pathParams.forEach((param, index) => {
        const paramWithPattern = {
            name: param.name || '',
            value: param.value || '',
            description: param.description || `Path parameter: ${param.name}`,
            pattern: param.pattern || ''
        };

        addPathParamRow(elements.pathParamsList, paramWithPattern);
    });

    if (elements.realUrlDisplay) {
        elements.realUrlDisplay.style.display = 'block';
    }

    if (endpoint.friendlyUrl) {
        elements.wsUrlInput.value = endpoint.friendlyUrl;
        parseUrlAndUpdateParams();
        updateRealUrlDisplay();
    }
}

// Add path parameter row with validation
function addPathParamRow(container, param) {
    const emptyState = container.querySelector('.empty-params-state');
    if (emptyState) {
        container.removeChild(emptyState);
    }

    const row = document.createElement('div');
    row.className = 'param-row';

    // Make sure we have all the necessary data
    const name = param.name || '';
    const value = param.value || '';
    const description = param.description || '';
    const pattern = param.pattern || '';

    row.innerHTML = `
        <input type="text" class="param-key-input" value="${name}" placeholder="Parameter">
        <input type="text" class="param-value-input" value="${value}" placeholder="Value"
               data-param-name="${name}" data-pattern="${pattern}">
        <input type="text" class="param-desc-input" value="${description}" placeholder="Description">
        <div class="param-actions">
            <span class="param-pattern" >${pattern}</span>
            <button class="remove-param">×</button>
        </div>
    `;

    const valueInput = row.querySelector('.param-value-input');
    const nameInput = row.querySelector('.param-key-input');
    const removeBtn = row.querySelector('.remove-param');

    // Add validation on input
    valueInput.addEventListener('input', () => {
        const currentValue = valueInput.value;
        const currentPattern = valueInput.getAttribute('data-pattern');

        const validation = validatePathParam(currentValue, currentPattern);
        showValidationWarning(row, validation.isValid ? '' : validation.message);

        updateRealUrlDisplay();
    });

    // Trigger initial validation if there's already a value and pattern
    if (value && pattern) {
        const validation = validatePathParam(value, pattern);
        if (!validation.isValid) {
            showValidationWarning(row, validation.message);
        }
    }

    nameInput.addEventListener('input', (event) => {
        valueInput.setAttribute('data-param-name', event.target.value);
        updateUrlPlaceholders();
        updateRealUrlDisplay();
    });

    removeBtn.addEventListener('click', () => {
        container.removeChild(row);
        if (container.children.length === 0) {
            const emptyState = document.createElement('div');
            emptyState.className = 'empty-params-state';
            emptyState.textContent = 'No path parameters for this endpoint.';
            container.appendChild(emptyState);

            if (elements.realUrlDisplay) {
                elements.realUrlDisplay.style.display = 'none';
            }
        }
        updateUrlPlaceholders();
        updateRealUrlDisplay();
    });

    container.appendChild(row);
}

// Parse the current URL and update both path and query parameters
function parseUrlAndUpdateParams() {
    parseExistingPathParams();
    parseExistingQueryParams();
}

// Extract path parameter from URL segment
function extractPathParamFromSegment(segment) {
    if (segment.startsWith(':')) {
        return {name: segment.substring(1), value: ''};
    } else if (segment.includes('<') && segment.includes('>')) {
        const djangoMatch = segment.match(/<\w+:(\w+)>/);
        if (djangoMatch && djangoMatch[1]) {
            return {name: djangoMatch[1], value: ''};
        }
    } else if (segment.includes('(?P<') && segment.includes('>')) {
        const match = segment.match(/\(\?P<([^>]+)>/);
        if (match && match[1]) {
            return {name: match[1], value: ''};
        }
    }
    return null;
}

// Parse URL path to find all path parameters
function extractPathParamsFromUrl(url) {
    try {
        const urlObj = new URL(url);
        const pathSegments = urlObj.pathname.split('/').filter(segment => segment.length > 0);
        const params = [];

        for (const segment of pathSegments) {
            const paramMatch = extractPathParamFromSegment(segment);
            if (paramMatch) {
                params.push(paramMatch);
            }
        }
        return params;
    } catch (error) {
        console.warn('Error parsing URL:', error);
        return [];
    }
}

// Parse path parameters from the URL
export function parseExistingPathParams() {
    const currentUrl = elements.wsUrlInput.value;
    const currentParams = getPathParams();
    const valueMap = {};
    const patternMap = {};

    // Create maps of parameter names to their values and patterns
    currentParams.forEach(param => {
        if (param.name && param.value) {
            valueMap[param.name] = param.value;
        }
        if (param.name && param.pattern) {
            patternMap[param.name] = param.pattern;
        }
    });

    // Also preserve patterns from the original state
    if (state.pathParameters) {
        state.pathParameters.forEach(param => {
            if (param.name && param.pattern) {
                patternMap[param.name] = param.pattern;
            }
        });
    }

    const explicitParams = extractPathParamsFromUrl(currentUrl);
    elements.pathParamsList.innerHTML = '';

    if (explicitParams.length > 0) {
        explicitParams.forEach(param => {
            const paramObj = {
                name: param.name,
                description: `Path parameter: ${param.name}`,
                // Use the pattern from the map if available, otherwise empty
                pattern: patternMap[param.name] || '',
                // Preserve previous value if it exists
                value: valueMap[param.name] || ''
            };
            addPathParamRow(elements.pathParamsList, paramObj);
        });

        // Update state but preserve patterns
        state.pathParameters = explicitParams.map(param => ({
            name: param.name,
            description: `Path parameter: ${param.name}`,
            pattern: patternMap[param.name] || ''
        }));

        if (elements.realUrlDisplay) {
            elements.realUrlDisplay.style.display = 'block';
        }
        return;
    }

    if (elements.pathParamsList.children.length === 0) {
        const emptyState = document.createElement('div');
        emptyState.className = 'empty-params-state';
        emptyState.textContent = 'No path parameters for this endpoint.';
        elements.pathParamsList.appendChild(emptyState);

        if (elements.realUrlDisplay) {
            elements.realUrlDisplay.style.display = 'none';
        }
    }
}

// Function to collect path parameters
function getPathParams() {
    const params = [];
    const rows = elements.pathParamsList.querySelectorAll('.param-row');

    rows.forEach(row => {
        const keyInput = row.querySelector('.param-key-input');
        const valueInput = row.querySelector('.param-value-input');
        const descInput = row.querySelector('.param-desc-input');
        const patternElem = row.querySelector('.param-pattern');

        const name = keyInput ? keyInput.value.trim() : '';
        const value = valueInput ? valueInput.value.trim() : '';
        const description = descInput ? descInput.value.trim() : '';

        // Get pattern from both the display element and the data attribute
        let pattern = '';
        if (patternElem) {
            pattern = patternElem.textContent.trim();
        }
        if (!pattern && valueInput) {
            pattern = valueInput.getAttribute('data-pattern') || '';
        }

        if (name) {
            params.push({name, value, description, pattern});
        }
    });

    return params;
}

// Update the real URL display under the URL editor
function updateRealUrlDisplay() {
    if (!elements.realUrlDisplay) return;

    const urlInputValue = elements.wsUrlInput.value;
    const pathParams = getPathParams();

    if (pathParams.length === 0) {
        elements.realUrlDisplay.style.display = 'none';
        return;
    }

    let realUrl = urlInputValue;
    pathParams.forEach(param => {
        if (param.name) {
            const valueToUse = param.value || `:${param.name}`;
            realUrl = realUrl.replace(new RegExp(`:${param.name}(?=/|$)`, 'g'), encodeURIComponent(valueToUse));
            realUrl = realUrl.replace(new RegExp(`<\\w+:${param.name}>`, 'g'), encodeURIComponent(valueToUse));
            realUrl = realUrl.replace(new RegExp(`\\(\\?P<${param.name}>[^)]+\\)`, 'g'), encodeURIComponent(valueToUse));
        }
    });

    elements.realUrlDisplay.textContent = `Real URL: ${realUrl}`;
    elements.realUrlDisplay.style.display = 'block';
}

// Helper functions for URL management
function hasTrailingSlash(url) {
    try {
        const urlObj = new URL(url);
        return urlObj.pathname.endsWith('/');
    } catch (error) {
        return false;
    }
}

function updateUrlPlaceholdersWithTrailingSlash() {
    updateUrlPlaceholders();
    const currentUrl = elements.wsUrlInput.value;

    if (!hasTrailingSlash(currentUrl)) {
        try {
            const urlObj = new URL(currentUrl);
            urlObj.pathname = urlObj.pathname + '/';
            elements.wsUrlInput.value = urlObj.toString();
            updateRealUrlDisplay();
        } catch (error) {
            console.warn('Error adding trailing slash:', error);
        }
    }
}

// Simplified URL placeholder update
function updateUrlPlaceholders() {
    const currentUrl = elements.wsUrlInput.value;
    const pathParams = getPathParams();

    try {
        const urlObj = new URL(currentUrl);
        let newPath = urlObj.pathname;

        // Remove existing placeholders and rebuild with current params
        newPath = newPath.replace(/\/:[^\/]+/g, '')
            .replace(/\/<\w+:\w+>/g, '')
            .replace(/\/\(\?P<[^>]+>[^)]+\)/g, '');

        // Add current parameters
        pathParams.forEach((param, index) => {
            if (index === 0 && !newPath.endsWith('/')) {
                newPath += '/';
            } else if (index > 0) {
                newPath += '/';
            }
            newPath += `:${param.name}`;
        });

        if (!newPath.endsWith('/')) {
            newPath += '/';
        }

        urlObj.pathname = newPath;
        elements.wsUrlInput.value = urlObj.toString();
    } catch (error) {
        console.warn('Error updating URL placeholders:', error);
    }
}

// Query parameter functions
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

    const removeBtn = row.querySelector('.remove-param');
    removeBtn.addEventListener('click', () => {
        container.removeChild(row);
        updateWebSocketUrl();
    });

    const inputs = row.querySelectorAll('input');
    inputs.forEach(input => {
        input.addEventListener('input', updateWebSocketUrl);
    });

    container.appendChild(row);
}

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

    updateRealUrlDisplay();
}

export function updateTabVisibility(endpoint) {
    const hasPathParams = endpoint && endpoint.pathParams && endpoint.pathParams.length > 0;
    const pathParamsTab = document.querySelector('.tab-button[data-tab="connection-path-params"]');
    const queryParamsTab = document.querySelector('.tab-button[data-tab="connection-params"]');
    const pathParamsContent = document.getElementById('connection-path-params');
    const queryParamsContent = document.getElementById('connection-params');

    if (!hasPathParams) {
        pathParamsTab.classList.remove('active');
        queryParamsTab.classList.add('active');
        pathParamsContent.classList.remove('active');
        queryParamsContent.classList.add('active');

        if (elements.realUrlDisplay) {
            elements.realUrlDisplay.style.display = 'none';
        }
    } else {
        if (elements.realUrlDisplay) {
            elements.realUrlDisplay.style.display = 'block';
            updateRealUrlDisplay();
        }
    }
}

export function parseExistingQueryParams() {
    try {
        const url = new URL(elements.wsUrlInput.value);
        const params = Array.from(url.searchParams.entries());

        while (elements.queryParamsList.firstChild) {
            elements.queryParamsList.removeChild(elements.queryParamsList.firstChild);
        }

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

                const removeBtn = row.querySelector('.remove-param');
                removeBtn.addEventListener('click', () => {
                    elements.queryParamsList.removeChild(row);
                    updateWebSocketUrl();
                });

                const inputs = row.querySelectorAll('input');
                inputs.forEach(input => {
                    input.addEventListener('input', updateWebSocketUrl);
                });

                elements.queryParamsList.appendChild(row);
            });
        } else {
            addQueryParamRow(elements.queryParamsList);
        }
    } catch (error) {
        console.warn('Failed to parse WebSocket URL:', error);
    }
}
