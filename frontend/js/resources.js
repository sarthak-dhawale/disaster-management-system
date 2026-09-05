let allResources = [];
let editingResourceId = null;


/* =========================
   PAGE LOAD
========================= */

document.addEventListener("DOMContentLoaded", () => {
    loadResources();
});


/* =========================
   LOAD RESOURCES
========================= */

async function loadResources() {

    hideError();

    const tableBody =
        document.getElementById("resources-table-body");

    tableBody.innerHTML = `
        <tr>
            <td colspan="10" class="loading">
                Loading resources...
            </td>
        </tr>
    `;

    try {

        const response =
            await fetch(`${API_BASE_URL}/api/resources/`);

        const data =
            await response.json();

        if (!response.ok) {

            throw new Error(
                data.detail || "Failed to load resources"
            );
        }

        allResources =
            Array.isArray(data.resources)
                ? data.resources
                : [];

        updateStatistics();

        applyFilters();

    } catch (error) {

        console.error(
            "Error loading resources:",
            error
        );

        tableBody.innerHTML = `
            <tr>
                <td colspan="10" class="empty-state">
                    Failed to load resources.
                </td>
            </tr>
        `;

        showError(error.message);
    }
}


/* =========================
   STATISTICS
========================= */

function updateStatistics() {

    const total =
        allResources.length;


    const totalQuantity =
        allResources.reduce(
            (sum, resource) =>
                sum + Number(resource.total_quantity || 0),
            0
        );


    const availableQuantity =
        allResources.reduce(
            (sum, resource) =>
                sum + Number(resource.available_quantity || 0),
            0
        );


    const lowStockCount =
        allResources.filter(
            resource =>
                Number(resource.available_quantity || 0)
                <
                Number(resource.minimum_required || 0)
        ).length;


    setText(
        "total-count",
        total
    );

    setText(
        "total-quantity",
        formatNumber(totalQuantity)
    );

    setText(
        "available-quantity",
        formatNumber(availableQuantity)
    );

    setText(
        "low-stock-count",
        lowStockCount
    );
}


/* =========================
   SEARCH + FILTER
========================= */

function applyFilters() {

    const searchInput =
        document.getElementById("search-input");

    const categoryFilter =
        document.getElementById("category-filter");


    const searchTerm =
        searchInput.value.trim().toLowerCase();


    const selectedCategory =
        categoryFilter.value;


    const filteredResources =
        allResources.filter(resource => {

            const matchesSearch =

                String(resource.resource_id ?? "")
                    .toLowerCase()
                    .includes(searchTerm)

                ||

                String(resource.resource_name ?? "")
                    .toLowerCase()
                    .includes(searchTerm)

                ||

                String(resource.category ?? "")
                    .toLowerCase()
                    .includes(searchTerm)

                ||

                String(resource.unit ?? "")
                    .toLowerCase()
                    .includes(searchTerm);


            const matchesCategory =
                selectedCategory === "ALL"
                ||
                resource.category === selectedCategory;


            return (
                matchesSearch &&
                matchesCategory
            );
        });


    renderResources(filteredResources);
}


/* =========================
   RENDER TABLE
========================= */

function renderResources(resources) {

    const tableBody =
        document.getElementById("resources-table-body");


    if (resources.length === 0) {

        tableBody.innerHTML = `
            <tr>
                <td colspan="10" class="empty-state">
                    No resources found.
                </td>
            </tr>
        `;

        return;
    }


    tableBody.innerHTML =
        resources.map(resource => {

            const total =
                Number(resource.total_quantity || 0);

            const available =
                Number(resource.available_quantity || 0);

            const minimum =
                Number(resource.minimum_required || 0);


            const percentage =
                total > 0
                    ? Math.min(
                        100,
                        (available / total) * 100
                    )
                    : 0;


            const stockClass =
                getStockClass(
                    available,
                    minimum,
                    total
                );


            const stockLabel =
                getStockLabel(
                    available,
                    minimum,
                    total
                );


            const resourceName =
                escapeHTML(
                    resource.resource_name || "Unnamed Resource"
                );


            const category =
                escapeHTML(
                    resource.category || "OTHER"
                );


            const unit =
                escapeHTML(
                    resource.unit || "—"
                );


            const updated =
                formatDate(resource.updated_at);


            return `
                <tr>

                    <td>
                        ${escapeHTML(resource.resource_id)}
                    </td>


                    <td>

                        <div class="resource-name">

                            <strong>
                                ${resourceName}
                            </strong>

                        </div>

                    </td>


                    <td>

                        <span class="category-badge">
                            ${category}
                        </span>

                    </td>


                    <td>
                        ${unit}
                    </td>


                    <td>

                        <span class="quantity">
                            ${formatNumber(total)}
                        </span>

                    </td>


                    <td>

                        <span class="available-quantity">
                            ${formatNumber(available)}
                        </span>

                    </td>


                    <td>

                        <span class="quantity">
                            ${formatNumber(minimum)}
                        </span>

                    </td>


                    <td>

                        <div class="stock-cell">

                            <div class="stock-info">

                                <span>
                                    ${formatNumber(available)} ${unit}
                                </span>

                                <span>
                                    ${percentage.toFixed(0)}%
                                </span>

                            </div>


                            <div class="stock-bar">

                                <div
                                    class="stock-fill ${stockClass}"
                                    style="width: ${percentage}%"
                                ></div>

                            </div>


                            <span class="stock-label ${getStockLabelClass(stockClass)}">
                                ${stockLabel}
                            </span>

                        </div>

                    </td>


                    <td>

                        <span class="updated-date">
                            ${updated}
                        </span>

                    </td>


                    <td>

                        <div class="action-buttons">

                            <button
                                class="action-btn edit"
                                title="Edit Resource"
                                onclick="editResource(${resource.resource_id})"
                            >
                                ✏️
                            </button>


                            <button
                                class="action-btn delete"
                                title="Delete Resource"
                                onclick="deleteResource(${resource.resource_id})"
                            >
                                🗑️
                            </button>

                        </div>

                    </td>

                </tr>
            `;

        }).join("");
}


/* =========================
   STOCK HELPERS
========================= */

function getStockClass(
    available,
    minimum,
    total
) {

    if (available < minimum) {
        return "low";
    }


    if (
        total > 0 &&
        available / total < 0.4
    ) {
        return "medium";
    }


    return "";
}


function getStockLabel(
    available,
    minimum,
    total
) {

    if (available < minimum) {
        return "LOW STOCK";
    }


    if (
        total > 0 &&
        available / total < 0.4
    ) {
        return "MEDIUM";
    }


    return "GOOD";
}


function getStockLabelClass(stockClass) {

    if (stockClass === "low") {
        return "low";
    }


    if (stockClass === "medium") {
        return "medium";
    }


    return "good";
}


/* =========================
   ADD RESOURCE
========================= */

function openAddModal() {

    editingResourceId = null;


    document.getElementById("modal-title").textContent =
        "Add Resource";


    document.getElementById("modal-subtitle").textContent =
        "Add a new disaster response resource";


    document.getElementById("save-button").textContent =
        "Save Resource";


    document
        .getElementById("resource-form")
        .reset();


    document.getElementById("total-quantity-input").value =
        "0";


    document.getElementById("available-quantity-input").value =
        "0";


    document.getElementById("minimum-required").value =
        "0";


    hideModalError();


    document
        .getElementById("resource-modal")
        .classList.add("show");
}


/* =========================
   EDIT RESOURCE
========================= */

function editResource(resourceId) {

    const resource =
        allResources.find(
            item =>
                Number(item.resource_id)
                ===
                Number(resourceId)
        );


    if (!resource) {

        showError(
            "Resource record not found."
        );

        return;
    }


    editingResourceId =
        resource.resource_id;


    document.getElementById("modal-title").textContent =
        "Edit Resource";


    document.getElementById("modal-subtitle").textContent =
        "Update resource inventory";


    document.getElementById("save-button").textContent =
        "Update Resource";


    document.getElementById("resource-name").value =
        resource.resource_name || "";


    document.getElementById("category").value =
        resource.category || "";


    document.getElementById("unit").value =
        resource.unit || "";


    document.getElementById("total-quantity-input").value =
        resource.total_quantity ?? 0;


    document.getElementById("available-quantity-input").value =
        resource.available_quantity ?? 0;


    document.getElementById("minimum-required").value =
        resource.minimum_required ?? 0;


    hideModalError();


    document
        .getElementById("resource-modal")
        .classList.add("show");
}


/* =========================
   SAVE / UPDATE RESOURCE
========================= */

async function saveResource(event) {

    event.preventDefault();

    hideModalError();


    const resourceName =
        document
            .getElementById("resource-name")
            .value
            .trim();


    const category =
        document
            .getElementById("category")
            .value;


    const unit =
        document
            .getElementById("unit")
            .value
            .trim();


    const totalQuantity =
        Number(
            document
                .getElementById("total-quantity-input")
                .value
        );


    const availableQuantity =
        Number(
            document
                .getElementById("available-quantity-input")
                .value
        );


    const minimumRequired =
        Number(
            document
                .getElementById("minimum-required")
                .value
        );


    /* =========================
       FRONTEND VALIDATION
    ========================= */

    if (!resourceName) {

        showModalError(
            "Resource name is required."
        );

        return;
    }


    const validCategories = [
        "FOOD",
        "WATER",
        "MEDICINE",
        "CLOTHING",
        "EQUIPMENT",
        "SHELTER_SUPPLIES",
        "OTHER"
    ];


    if (!validCategories.includes(category)) {

        showModalError(
            "Please select a valid resource category."
        );

        return;
    }


    if (!unit) {

        showModalError(
            "Unit is required."
        );

        return;
    }


    if (
        !Number.isFinite(totalQuantity) ||
        totalQuantity < 0
    ) {

        showModalError(
            "Total quantity cannot be negative."
        );

        return;
    }


    if (
        !Number.isFinite(availableQuantity) ||
        availableQuantity < 0
    ) {

        showModalError(
            "Available quantity cannot be negative."
        );

        return;
    }


    if (
        availableQuantity > totalQuantity
    ) {

        showModalError(
            "Available quantity cannot exceed total quantity."
        );

        return;
    }


    if (
        !Number.isFinite(minimumRequired) ||
        minimumRequired < 0
    ) {

        showModalError(
            "Minimum required cannot be negative."
        );

        return;
    }


    const payload = {

        resource_name: resourceName,

        category: category,

        unit: unit,

        total_quantity: totalQuantity,

        available_quantity: availableQuantity,

        minimum_required: minimumRequired
    };


    const saveButton =
        document.getElementById("save-button");


    saveButton.disabled = true;


    saveButton.textContent =
        editingResourceId
            ? "Updating..."
            : "Saving...";


    try {

        let response;


        if (editingResourceId) {

            response =
                await fetch(
                    `${API_BASE_URL}/api/resources/${editingResourceId}`,
                    {
                        method: "PUT",

                        headers: {
                            "Content-Type": "application/json"
                        },

                        body: JSON.stringify(payload)
                    }
                );

        } else {

            response =
                await fetch(
                    `${API_BASE_URL}/api/resources/`,
                    {
                        method: "POST",

                        headers: {
                            "Content-Type": "application/json"
                        },

                        body: JSON.stringify(payload)
                    }
                );
        }


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Failed to save resource"
            );
        }


        alert(
            editingResourceId
                ? "Resource updated successfully!"
                : "Resource created successfully!"
        );


        closeModal();


        await loadResources();


    } catch (error) {

        console.error(
            "Error saving resource:",
            error
        );


        showModalError(
            error.message
        );


    } finally {

        saveButton.disabled = false;


        saveButton.textContent =
            editingResourceId
                ? "Update Resource"
                : "Save Resource";
    }
}


/* =========================
   DELETE RESOURCE
========================= */

async function deleteResource(resourceId) {

    const resource =
        allResources.find(
            item =>
                Number(item.resource_id)
                ===
                Number(resourceId)
        );


    if (!resource) {

        showError(
            "Resource record not found."
        );

        return;
    }


    const confirmed =
        confirm(
            `Are you sure you want to delete resource "${resource.resource_name}"?`
        );


    if (!confirmed) {
        return;
    }


    try {

        const response =
            await fetch(
                `${API_BASE_URL}/api/resources/${resourceId}`,
                {
                    method: "DELETE"
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Failed to delete resource"
            );
        }


        alert(
            "Resource deleted successfully!"
        );


        await loadResources();


    } catch (error) {

        console.error(
            "Error deleting resource:",
            error
        );


        showError(
            error.message
        );
    }
}


/* =========================
   MODAL
========================= */

function closeModal() {

    document
        .getElementById("resource-modal")
        .classList.remove("show");


    hideModalError();


    editingResourceId = null;
}


/* CLICK OUTSIDE MODAL */

document.addEventListener("click", event => {

    const modal =
        document.getElementById("resource-modal");


    if (
        event.target === modal &&
        modal.classList.contains("show")
    ) {

        closeModal();
    }

});


/* ESCAPE KEY */

document.addEventListener("keydown", event => {

    if (event.key === "Escape") {

        const modal =
            document.getElementById("resource-modal");


        if (
            modal.classList.contains("show")
        ) {

            closeModal();
        }
    }

});


/* =========================
   DATE FORMAT
========================= */

function formatDate(value) {

    if (!value) {
        return "—";
    }


    const date =
        new Date(value);


    if (
        Number.isNaN(
            date.getTime()
        )
    ) {

        return escapeHTML(value);
    }


    return date.toLocaleDateString(
        "en-IN",
        {
            day: "2-digit",
            month: "short",
            year: "numeric"
        }
    );
}


/* =========================
   NUMBER FORMAT
========================= */

function formatNumber(value) {

    const number =
        Number(value || 0);


    if (!Number.isFinite(number)) {
        return "0";
    }


    return number.toLocaleString(
        "en-IN",
        {
            maximumFractionDigits: 2
        }
    );
}


/* =========================
   ERROR HANDLING
========================= */

function showError(message) {

    const errorBox =
        document.getElementById("page-error");


    if (!errorBox) {
        return;
    }


    errorBox.textContent =
        message;


    errorBox.classList.add("show");
}


function hideError() {

    const errorBox =
        document.getElementById("page-error");


    if (errorBox) {

        errorBox.classList.remove("show");

        errorBox.textContent = "";
    }
}


function showModalError(message) {

    const errorBox =
        document.getElementById("modal-error");


    errorBox.textContent =
        message;


    errorBox.classList.add("show");
}


function hideModalError() {

    const errorBox =
        document.getElementById("modal-error");


    errorBox.classList.remove("show");

    errorBox.textContent = "";
}