/**
 * Agenda Reorder - Drag & Drop functionality for agenda items
 * 
 * Uses Sortable.js for nested drag & drop functionality.
 * Requires: Sortable.js library to be loaded
 */

document.addEventListener('DOMContentLoaded', function() {
    const agendaList = document.getElementById('agenda-items-list');
    
    if (!agendaList) {
        return; // Not on a page with agenda items
    }
    
    const agendaId = agendaList.dataset.agendaId;
    const reorderUrl = agendaList.dataset.reorderUrl;
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    if (!agendaId || !reorderUrl) {
        console.error('Missing data-agenda-id or data-reorder-url on agenda-items-list');
        return;
    }
    
    /**
     * Initialize Sortable.js on the main list and all nested lists
     */
    function initializeSortable() {
        const lists = document.querySelectorAll('.agenda-items-sortable');
        
        lists.forEach(list => {
            new Sortable(list, {
                group: 'nested',
                animation: 150,
                fallbackOnBody: true,
                swapThreshold: 0.65,
                handle: '.drag-handle',
                ghostClass: 'sortable-ghost',
                chosenClass: 'sortable-chosen',
                dragClass: 'sortable-drag',
                onStart: handleDragStart,
                onEnd: handleDragEnd
            });
        });
    }
    
    /**
     * Handle drag start event - highlight all drop zones
     * 
     * @param {Event} evt - Sortable event
     */
    function handleDragStart(evt) {
        // Add class to body to indicate dragging is active
        document.body.classList.add('drag-active');
        
        // Highlight all sortable lists as drop zones
        const allLists = document.querySelectorAll('.agenda-items-sortable');
        allLists.forEach(list => {
            list.classList.add('drop-zone-highlight');
        });
    }
    
    /**
     * Handle drag end event and save new order to backend
     * 
     * @param {Event} evt - Sortable event
     */
    function handleDragEnd(evt) {
        // Remove drag-active class from body
        document.body.classList.remove('drag-active');
        
        // Remove highlight from all drop zones
        const allLists = document.querySelectorAll('.agenda-items-sortable');
        allLists.forEach(list => {
            list.classList.remove('drop-zone-highlight');
        });
        
        // Save the new order
        const itemOrder = collectItemOrder();
        saveItemOrder(itemOrder);
    }
    
    /**
     * Collect current order of all agenda items with their parent relationships
     * 
     * @returns {Array} Array of {id: uuid, type: string, parent_id: uuid|null} objects
     */
    function collectItemOrder() {
        const items = [];
        const rootList = document.getElementById('agenda-items-list');
        
        function processItems(list, parentId = null) {
            const listItems = list.querySelectorAll(':scope > .agenda-item');
            
            listItems.forEach(item => {
                const itemId = item.dataset.itemId;
                const itemType = item.dataset.itemType || 'AgendaItemRegular';
                 
                items.push({
                    id: itemId,
                    type: itemType,
                    parent_id: parentId
                });
                
                // Check for nested items
                const nestedList = item.querySelector(':scope > .agenda-items-sortable');
                if (nestedList) {
                    processItems(nestedList, itemId);
                }
            });
        }
        
        processItems(rootList);
        return items;
    }
    
    /**
     * Save item order to backend via AJAX
     * 
     * @param {Array} itemOrder - Array of {id, parent_id} objects
     */
    function saveItemOrder(itemOrder) {
        // Show loading indicator
        showLoadingIndicator();
        
        fetch(reorderUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                item_order: itemOrder
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                updateItemNumbers(data.item_numbers);
                showSuccessMessage('Reihenfolge erfolgreich gespeichert');
            } else {
                throw new Error(data.message || 'Unknown error');
            }
        })
        .catch(error => {
            console.error('Error saving order:', error);
            showErrorMessage('Fehler beim Speichern der Reihenfolge');
        })
        .finally(() => {
            hideLoadingIndicator();
        });
    }
    
    /**
     * Update displayed item numbers after successful reorder
     * 
     * @param {Object} itemNumbers - Object mapping item UUIDs to item numbers
     */
    function updateItemNumbers(itemNumbers) {
        for (const [itemId, itemNumber] of Object.entries(itemNumbers)) {
            const item = document.querySelector(`[data-item-id="${itemId}"]`);
            if (item) {
                const numberElement = item.querySelector('.item-number');
                if (numberElement) {
                    numberElement.textContent = itemNumber;
                }
            }
        }
    }
    
    /**
     * Show loading indicator
     */
    function showLoadingIndicator() {
        const indicator = document.getElementById('loading-indicator');
        if (indicator) {
            indicator.classList.remove('d-none');
        }
    }
    
    /**
     * Hide loading indicator
     */
    function hideLoadingIndicator() {
        const indicator = document.getElementById('loading-indicator');
        if (indicator) {
            indicator.classList.add('d-none');
        }
    }
    
    /**
     * Show success message to user
     * 
     * @param {string} message - Success message text
     */
    function showSuccessMessage(message) {
        showToast(message, 'success');
    }
    
    /**
     * Show error message to user
     * 
     * @param {string} message - Error message text
     */
    function showErrorMessage(message) {
        showToast(message, 'danger');
    }
    
    /**
     * Show Bootstrap toast notification
     * 
     * @param {string} message - Toast message
     * @param {string} type - Bootstrap alert type (success, danger, etc.)
     */
    function showToast(message, type) {
        // Create toast container if it doesn't exist
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            toastContainer.style.zIndex = '9999';
            document.body.appendChild(toastContainer);
        }
        
        // Create toast element
        const toastId = 'toast-' + Date.now();
        const toastHtml = `
            <div id="${toastId}" class="toast align-items-center text-white bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="d-flex">
                    <div class="toast-body">
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Schließen"></button>
                </div>
            </div>
        `;
        
        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        
        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement, {
            autohide: true,
            delay: 3000
        });
        
        toast.show();
        
        // Remove toast element after it's hidden
        toastElement.addEventListener('hidden.bs.toast', function() {
            toastElement.remove();
        });
    }
    
    // Initialize Sortable on page load
    initializeSortable();
});
