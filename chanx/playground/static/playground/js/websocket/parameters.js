// Module for handling path and query parameters

import { addStatusMessage } from './messages.js';

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
        addPathParamRow(elements.pathParamsList, { name: '', pattern: '', description: '' });
        // After adding a path parameter, update the URL with trailing slash
        updateUrlPlaceholdersWithTrailingSlash();
    });

    // Add event listener to URL input for parsing both path and query parameters
    elements.wsUrlInput.addEventListener('change', () => {
        parseUrlAndUpdateParams();
        updateRealUrlDisplay();
    });

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

        // Hide the real URL display since there are no path parameters
        if (elements.realUrlDisplay) {
            elements.realUrlDisplay.style.display = 'none';
        }
        return;
    }

    // Store the original pattern for replacements
    state.originalPathPattern = endpoint.url;
    state.pathParameters = endpoint.path_params;

    // Add UI for each path parameter - all are now editable
    endpoint.path_params.forEach(param => {
        addPathParamRow(elements.pathParamsList, param);
    });

    // Show the real URL display
    if (elements.realUrlDisplay) {
        elements.realUrlDisplay.style.display = 'block';
    }

    // Initialize with friendly URL if available
    if (endpoint.friendly_url) {
        elements.wsUrlInput.value = endpoint.friendly_url;

        // Parse initial values from the friendly URL
        parseUrlAndUpdateParams();
        updateRealUrlDisplay();
    }
}

// Parse the current URL and update both path and query parameters
function parseUrlAndUpdateParams() {
    parseExistingPathParams();
    parseExistingQueryParams();
}

// Extract path parameter from URL segment
function extractPathParamFromSegment(segment) {
    // Check if segment starts with ":" or contains regex pattern
    if (segment.startsWith(':')) {
        return {
            name: segment.substring(1), // Remove ":" prefix
            value: ''
        };
    } else if (segment.includes('(?P<') && segment.includes('>')) {
        // Extract parameter name from regex pattern
        const match = segment.match(/\(\?P<([^>]+)>/);
        if (match && match[1]) {
            return {
                name: match[1],
                value: ''
            };
        }
    }
    return null;
}

// Parse URL path to find all path parameters
function extractPathParamsFromUrl(url) {
    try {
        // Parse the URL and extract path segments
        const urlObj = new URL(url);
        const pathSegments = urlObj.pathname.split('/').filter(segment => segment.length > 0);

        // Look for path parameters (segments starting with ":" or containing regex pattern)
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

    // Get current parameter values before clearing the UI
    const currentParams = getPathParams();
    const valueMap = {};

    // Create a map of parameter names to their values
    currentParams.forEach(param => {
        if (param.name && param.value) {
            valueMap[param.name] = param.value;
        }
    });

    // Extract explicit path parameters from URL
    const explicitParams = extractPathParamsFromUrl(currentUrl);

    // Clear existing path parameters - important for when parameters are removed from URL
    elements.pathParamsList.innerHTML = '';

    if (explicitParams.length > 0) {
        // Add UI for each explicit parameter, preserving values if they exist
        explicitParams.forEach(param => {
            const paramObj = {
                name: param.name,
                description: `Path parameter: ${param.name}`,
                pattern: '',
                // Preserve previous value if it exists
                value: valueMap[param.name] || ''
            };
            addPathParamRow(elements.pathParamsList, paramObj);
        });

        // Update state
        state.pathParameters = explicitParams.map(param => ({
            name: param.name,
            description: `Path parameter: ${param.name}`,
            pattern: ''
        }));

        // Show the real URL display since we have parameters
        if (elements.realUrlDisplay) {
            elements.realUrlDisplay.style.display = 'block';
        }

        return;
    }

    // If no parameters found and we cleared the list, add empty state message
    if (elements.pathParamsList.children.length === 0) {
        const emptyState = document.createElement('div');
        emptyState.className = 'empty-params-state';
        emptyState.textContent = 'No path parameters for this endpoint.';
        elements.pathParamsList.appendChild(emptyState);

        // Hide the real URL display
        if (elements.realUrlDisplay) {
            elements.realUrlDisplay.style.display = 'none';
        }
    }
}

// Add path parameter row - all parameters are now editable and removable
function addPathParamRow(container, param) {
    // If container has an empty state message, remove it
    const emptyState = container.querySelector('.empty-params-state');
    if (emptyState) {
        container.removeChild(emptyState);
    }

    const row = document.createElement('div');
    row.className = 'param-row';

    // Create HTML structure for the parameter row - all fields are editable now
    row.innerHTML = `
        <input type="text" class="param-key-input" value="${param.name}" placeholder="Parameter">
        <input type="text" class="param-value-input" value="${param.value || ''}" placeholder="Value" data-param-name="${param.name}">
        <input type="text" class="param-desc-input" value="${param.description || ''}" placeholder="Description">
        <div class="param-actions">
            <span class="param-pattern" title="Pattern: ${param.pattern || ''}">${param.pattern || ''}</span>
            <button class="remove-param">×</button>
        </div>
    `;

    // Add event listener to value input for URL updating
    const valueInput = row.querySelector('.param-value-input');
    valueInput.addEventListener('input', () => {
        // Only update the real URL display, not the editor
        updateRealUrlDisplay();
    });

    // Add event listener to name input for placeholder updating
    const nameInput = row.querySelector('.param-key-input');
    nameInput.addEventListener('input', (event) => {
        // Update data-param-name attribute when the name changes
        valueInput.setAttribute('data-param-name', event.target.value);

        // Update placeholders in the WebSocket URL editor
        updateUrlPlaceholders();

        // Update real URL display
        updateRealUrlDisplay();
    });

    // Add event listener to remove button
    const removeBtn = row.querySelector('.remove-param');
    removeBtn.addEventListener('click', () => {
        container.removeChild(row);

        // If no parameters left, add empty state message
        if (container.children.length === 0) {
            const emptyState = document.createElement('div');
            emptyState.className = 'empty-params-state';
            emptyState.textContent = 'No path parameters for this endpoint.';
            container.appendChild(emptyState);

            // Hide the real URL display
            if (elements.realUrlDisplay) {
                elements.realUrlDisplay.style.display = 'none';
            }
        }

        // Update placeholders in the WebSocket URL
        updateUrlPlaceholders();

        // Update real URL display
        updateRealUrlDisplay();
    });

    container.appendChild(row);
}

// Check if a URL already has trailing slash
function hasTrailingSlash(url) {
    try {
        const urlObj = new URL(url);
        return urlObj.pathname.endsWith('/');
    } catch (error) {
        return false;
    }
}

// Update URL placeholders with trailing slash (for "Add Path Parameter" button)
function updateUrlPlaceholdersWithTrailingSlash() {
    // First do the normal placeholder update
    updateUrlPlaceholders();

    // Then ensure we have a trailing slash
    const currentUrl = elements.wsUrlInput.value;

    if (!hasTrailingSlash(currentUrl)) {
        try {
            const urlObj = new URL(currentUrl);
            urlObj.pathname = urlObj.pathname + '/';
            elements.wsUrlInput.value = urlObj.toString();

            // Update real URL display
            updateRealUrlDisplay();
        } catch (error) {
            console.warn('Error adding trailing slash:', error);
        }
    }
}

// Helper to extract path structure from URL
function getPathStructure(url) {
    try {
        const urlObj = new URL(url);
        const fullPath = urlObj.pathname;

        // Find positions of all parameter placeholders
        const placeholderPositions = [];
        let match;

        // Find all ":param" placeholders
        const paramRegex = /:([^\/]+)/g;
        while ((match = paramRegex.exec(fullPath)) !== null) {
            placeholderPositions.push({
                start: match.index,
                end: match.index + match[0].length,
                name: match[1],
                type: 'simple'
            });
        }

        // Find all regex pattern placeholders
        const regexParamRegex = /\(\?P<([^>]+)>[^)]+\)/g;
        while ((match = regexParamRegex.exec(fullPath)) !== null) {
            placeholderPositions.push({
                start: match.index,
                end: match.index + match[0].length,
                name: match[1],
                type: 'regex'
            });
        }

        // Sort by position
        placeholderPositions.sort((a, b) => a.start - b.start);

        return {
            fullPath,
            placeholderPositions,
            hasTrailingSlash: fullPath.endsWith('/')
        };
    } catch (error) {
        console.warn('Error getting path structure:', error);
        return {
            fullPath: '',
            placeholderPositions: [],
            hasTrailingSlash: false
        };
    }
}

// Update placeholders in the WebSocket URL editor based on path parameter names
function updateUrlPlaceholders() {
    // Get current URL
    const currentUrl = elements.wsUrlInput.value;

    try {
        // Get path structure (to understand where parameters are in the path)
        const { fullPath, placeholderPositions, hasTrailingSlash } = getPathStructure(currentUrl);

        // Get all path parameters from the UI
        const pathParams = getPathParams();

        // If no parameters, remove all placeholders from URL
        if (pathParams.length === 0) {
            // Remove path parameter placeholders but preserve any normal segments
            const cleanedPath = fullPath.replace(/\/:[^\/]+|\/\(\?P<[^>]+>[^)]+\)/g, '');

            const urlObj = new URL(currentUrl);
            urlObj.pathname = cleanedPath || '/';
            elements.wsUrlInput.value = urlObj.toString();
            return;
        }

        // Parse the URL
        const urlObj = new URL(currentUrl);

        // If there are placeholders, update them with current params
        if (placeholderPositions.length > 0) {
            // Create map of processed parameters
            const processedParams = new Set();

            // We'll build a new path by replacing placeholders
            let newPath = fullPath;

            // First handle updating existing placeholders
            // We need to process them in reverse order to avoid position shifts
            for (let i = placeholderPositions.length - 1; i >= 0; i--) {
                const pos = placeholderPositions[i];

                // Check if we have a parameter that matches this position
                if (i < pathParams.length) {
                    const param = pathParams[i];
                    processedParams.add(i);

                    // Replace the placeholder with the new parameter name
                    if (pos.type === 'simple') {
                        newPath = newPath.substring(0, pos.start) +
                                  `:${param.name}` +
                                  newPath.substring(pos.end);
                    } else {
                        // For regex placeholders, keep the pattern but update the name
                        const before = newPath.substring(0, pos.start);
                        const after = newPath.substring(pos.end);
                        const middle = newPath.substring(pos.start, pos.end)
                            .replace(/\(\?P<[^>]+>/, `(?P<${param.name}>`);

                        newPath = before + middle + after;
                    }
                } else {
                    // If we have more placeholders than parameters, remove excess ones
                    // Check if this is a standalone parameter or part of a path segment
                    const isStandalone = (
                        (pos.start === 0 || newPath[pos.start - 1] === '/') &&
                        (pos.end === newPath.length || newPath[pos.end] === '/')
                    );

                    if (isStandalone) {
                        // Remove the entire segment including slash
                        const slashPos = pos.start > 0 ? pos.start - 1 : pos.start;
                        newPath = newPath.substring(0, slashPos) +
                                 newPath.substring(pos.end);
                    } else {
                        // Just remove the placeholder itself
                        newPath = newPath.substring(0, pos.start) +
                                 newPath.substring(pos.end);
                    }
                }
            }

            // Handle any parameters that didn't match existing placeholders
            pathParams.forEach((param, index) => {
                if (!processedParams.has(index)) {
                    // This is a new parameter, need to add it to the path
                    if (newPath.endsWith('/')) {
                        // If path ends with slash, just append the parameter
                        newPath += `:${param.name}`;
                    } else {
                        // Otherwise add slash then parameter
                        newPath += `/:${param.name}`;
                    }
                }
            });

            // Make sure we always end with a trailing slash
            if (!newPath.endsWith('/')) {
                newPath += '/';
            }

            // Update the URL
            urlObj.pathname = newPath;
            elements.wsUrlInput.value = urlObj.toString();
        }
        // If no placeholders but we have parameters, add them
        else if (pathParams.length > 0) {
            let newPath = urlObj.pathname;

            // Add parameters to the path
            pathParams.forEach((param, index) => {
                if (index === 0) {
                    // For first parameter, check if we need a slash
                    if (!newPath.endsWith('/')) {
                        newPath += '/';
                    }
                    newPath += `:${param.name}`;
                } else {
                    // For subsequent parameters, always add a slash
                    newPath += `/:${param.name}`;
                }
            });

            // Always add trailing slash
            if (!newPath.endsWith('/')) {
                newPath += '/';
            }

            // Update URL
            urlObj.pathname = newPath;
            elements.wsUrlInput.value = urlObj.toString();
        }
    } catch (error) {
        console.warn('Error updating URL placeholders:', error);
    }
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

// Function to collect path parameters
function getPathParams() {
    const params = [];
    const rows = elements.pathParamsList.querySelectorAll('.param-row');

    rows.forEach(row => {
        const keyInput = row.querySelector('.param-key-input');
        const valueInput = row.querySelector('.param-value-input');
        const descInput = row.querySelector('.param-desc-input');
        const patternElem = row.querySelector('.param-pattern');

        const name = keyInput.value.trim();
        const value = valueInput.value.trim();
        const description = descInput.value.trim();
        const pattern = patternElem ? patternElem.textContent.trim() : '';

        if (name) {
            params.push({name, value, description, pattern});
        }
    });

    return params;
}

// Update the real URL display under the URL editor
function updateRealUrlDisplay() {
    if (!elements.realUrlDisplay) return;

    // Get the current URL input value (with placeholders)
    const urlInputValue = elements.wsUrlInput.value;

    // Parse path parameters
    const pathParams = getPathParams();

    // If no params, hide real URL display
    if (pathParams.length === 0) {
        elements.realUrlDisplay.style.display = 'none';
        return;
    }

    // Calculate the real URL by applying all path parameter values
    let realUrl = urlInputValue;
    pathParams.forEach(param => {
        if (param.name) {
            const valueToUse = param.value || `:${param.name}`;

            // Replace :paramName syntax with actual value
            realUrl = realUrl.replace(new RegExp(`:${param.name}(?=/|$)`, 'g'), encodeURIComponent(valueToUse));

            // Also replace regex patterns (?P<n>pattern) with the value
            realUrl = realUrl.replace(new RegExp(`\\(\\?P<${param.name}>[^)]+\\)`, 'g'), encodeURIComponent(valueToUse));
        }
    });

    // Update the display
    elements.realUrlDisplay.textContent = `Real URL: ${realUrl}`;

    // Show display
    elements.realUrlDisplay.style.display = 'block';
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

    // Update the real URL display
    updateRealUrlDisplay();
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

        // Hide the real URL display
        if (elements.realUrlDisplay) {
            elements.realUrlDisplay.style.display = 'none';
        }
    } else {
        // If endpoint has path params, show the real URL display
        if (elements.realUrlDisplay) {
            elements.realUrlDisplay.style.display = 'block';
            updateRealUrlDisplay();
        }
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
