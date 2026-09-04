/* ================================
   SHELTERS MODULE
================================ */

let allShelters = [];
let editingShelterId = null;


/* ================================
   PAGE LOAD
================================ */

document.addEventListener("DOMContentLoaded", () => {

    loadShelters();

    setupEventListeners();

});


/* ================================
   EVENT LISTENERS
================================ */

function setupEventListeners() {

    document
        .getElementById("add-shelter-btn")
        ?.addEventListener(
            "click",
            openAddModal
        );


    document
        .getElementById("close-modal")
        ?.addEventListener(
            "click",
            closeModal
        );


    document
        .getElementById("cancel-btn")
        ?.addEventListener(
            "click",
            closeModal
        );


    document
        .getElementById("shelter-form")
        ?.addEventListener(
            "submit",
            saveShelter
        );


    document
        .getElementById("search-input")
        ?.addEventListener(
            "input",
            applyFilters
        );


    document
        .getElementById("status-filter")
        ?.addEventListener(
            "change",
            applyFilters
        );


    document
        .getElementById("refresh-btn")
        ?.addEventListener(
            "click",
            loadShelters
        );


    document
        .getElementById("shelter-modal")
        ?.addEventListener(
            "click",
            event => {

                if (
                    event.target.id ===
                    "shelter-modal"
                ) {

                    closeModal();

                }

            }
        );

}


/* ================================
   LOAD SHELTERS
================================ */

async function loadShelters() {

    const tableBody =
        document.getElementById(
            "shelter-table-body"
        );


    if (!tableBody) {
        return;
    }


    tableBody.innerHTML = `
        <tr>
            <td colspan="8">
                <div class="loading">
                    Loading shelters...
                </div>
            </td>
        </tr>
    `;


    hideError();


    try {

        const response =
            await fetch(
                `${API_BASE_URL}/api/shelters/`
            );


        if (!response.ok) {

            throw new Error(
                `API returned ${response.status}`
            );

        }


        const data =
            await response.json();


        /*
         * Backend response:
         *
         * {
         *     count: 9,
         *     shelters: [...]
         * }
         */

        allShelters =
            Array.isArray(data.shelters)
                ? data.shelters
                : [];


        updateStatistics();

        applyFilters();


    } catch (error) {

        console.error(
            "Failed to load shelters:",
            error
        );


        tableBody.innerHTML = `
            <tr>
                <td colspan="8">
                    <div class="empty-state">
                        Could not load shelter data.
                    </div>
                </td>
            </tr>
        `;


        showError(
            "Could not load shelter data. Make sure the FastAPI backend is running."
        );

    }

}


/* ================================
   STATISTICS
================================ */

function updateStatistics() {

    const total =
        allShelters.length;


    const available =
        allShelters.filter(
            shelter =>
                normalize(
                    shelter.status
                ) === "available"
        ).length;


    const full =
        allShelters.filter(
            shelter =>
                normalize(
                    shelter.status
                ) === "full"
        ).length;


    const totalCapacity =
        allShelters.reduce(
            (sum, shelter) =>
                sum +
                Number(
                    shelter.capacity || 0
                ),
            0
        );


    setText(
        "total-count",
        total
    );


    setText(
        "available-count",
        available
    );


    setText(
        "full-count",
        full
    );


    setText(
        "total-capacity",
        formatNumber(totalCapacity)
    );

}


/* ================================
   FILTERS
================================ */

function applyFilters() {

    const search =
        normalize(
            document.getElementById(
                "search-input"
            )?.value
        );


    const status =
        normalize(
            document.getElementById(
                "status-filter"
            )?.value
        );


    const filtered =
        allShelters.filter(
            shelter => {

                const name =
                    normalize(
                        shelter.name
                    );


                const location =
                    String(
                        shelter.location_id ??
                        ""
                    );


                const phone =
                    normalize(
                        shelter.contact_phone
                    );


                const matchesSearch =
                    !search ||
                    name.includes(search) ||
                    location.includes(search) ||
                    phone.includes(search);


                const shelterStatus =
                    normalize(
                        shelter.status
                    );


                const matchesStatus =
                    !status ||
                    shelterStatus === status;


                return (
                    matchesSearch &&
                    matchesStatus
                );

            }
        );


    renderShelters(filtered);

}


/* ================================
   RENDER TABLE
================================ */

function renderShelters(shelters) {

    const tableBody =
        document.getElementById(
            "shelter-table-body"
        );


    if (!tableBody) {
        return;
    }


    if (!shelters.length) {

        tableBody.innerHTML = `
            <tr>
                <td colspan="8">
                    <div class="empty-state">
                        No shelters match your search.
                    </div>
                </td>
            </tr>
        `;

        return;
    }


    tableBody.innerHTML =
        shelters
            .map(
                shelter => {

                    const id =
                        shelter.shelter_id;


                    const name =
                        shelter.name ??
                        "Unnamed Shelter";


                    const location =
                        shelter.location_id ??
                        "-";


                    const capacity =
                        Number(
                            shelter.capacity || 0
                        );


                    const occupancy =
                        Number(
                            shelter.current_occupancy || 0
                        );


                    const status =
                        shelter.status ??
                        "-";


                    const phone =
                        shelter.contact_phone ??
                        "-";


                    const percentage =
                        capacity > 0
                            ? Math.min(
                                100,
                                Math.round(
                                    (occupancy / capacity) * 100
                                )
                            )
                            : 0;


                    return `
                        <tr>

                            <td>
                                ${escapeHTML(id)}
                            </td>


                            <td>
                                <strong>
                                    ${escapeHTML(name)}
                                </strong>
                            </td>


                            <td>
                                ${escapeHTML(location)}
                            </td>


                            <td>
                                ${formatNumber(capacity)}
                            </td>


                            <td>

                                <div class="occupancy-cell">

                                    <div class="occupancy-text">

                                        <span>
                                            ${formatNumber(occupancy)}
                                            /
                                            ${formatNumber(capacity)}
                                        </span>

                                        <span>
                                            ${percentage}%
                                        </span>

                                    </div>


                                    <div class="occupancy-bar">

                                        <div
                                            class="occupancy-fill"
                                            style="width: ${percentage}%">
                                        </div>

                                    </div>

                                </div>

                            </td>


                            <td>

                                <span
                                    class="badge ${getStatusClass(status)}">

                                    ${escapeHTML(status)}

                                </span>

                            </td>


                            <td>
                                ${escapeHTML(phone)}
                            </td>


                            <td>

                                <div class="action-buttons">

                                    <button
                                        class="action-btn edit-btn"
                                        title="Edit"
                                        onclick="editShelter(${id})">

                                        ✏️

                                    </button>


                                    <button
                                        class="action-btn delete-btn"
                                        title="Delete"
                                        onclick="deleteShelter(${id})">

                                        🗑️

                                    </button>

                                </div>

                            </td>

                        </tr>
                    `;

                }
            )
            .join("");

}


/* ================================
   ADD SHELTER
================================ */

function openAddModal() {

    editingShelterId = null;


    document.getElementById(
        "modal-title"
    ).textContent =
        "Add Shelter";


    document.getElementById(
        "shelter-form"
    ).reset();


    document.getElementById(
        "shelter-id"
    ).value = "";


    document.getElementById(
        "current-occupancy"
    ).value =
        0;


    document.getElementById(
        "status"
    ).value =
        "AVAILABLE";


    showModal();

}


/* ================================
   EDIT SHELTER
================================ */

function editShelter(id) {

    const shelter =
        allShelters.find(
            item =>
                Number(
                    item.shelter_id
                ) === Number(id)
        );


    if (!shelter) {

        showError(
            "Shelter record could not be found."
        );

        return;
    }


    editingShelterId =
        shelter.shelter_id;


    document.getElementById(
        "modal-title"
    ).textContent =
        "Edit Shelter";


    document.getElementById(
        "shelter-id"
    ).value =
        shelter.shelter_id;


    document.getElementById(
        "shelter-name"
    ).value =
        shelter.name ?? "";


    document.getElementById(
        "location-id"
    ).value =
        shelter.location_id ?? "";


    document.getElementById(
        "capacity"
    ).value =
        shelter.capacity ?? "";


    document.getElementById(
        "current-occupancy"
    ).value =
        shelter.current_occupancy ?? 0;


    document.getElementById(
        "contact-phone"
    ).value =
        shelter.contact_phone ?? "";


    document.getElementById(
        "status"
    ).value =
        shelter.status ?? "AVAILABLE";


    showModal();

}


/* ================================
   SAVE SHELTER
================================ */

async function saveShelter(event) {

    event.preventDefault();


    const id =
        document.getElementById(
            "shelter-id"
        ).value;


    const name =
        document.getElementById(
            "shelter-name"
        ).value.trim();


    const locationId =
        document.getElementById(
            "location-id"
        ).value;


    const capacity =
        document.getElementById(
            "capacity"
        ).value;


    const occupancy =
        document.getElementById(
            "current-occupancy"
        ).value;


    const phone =
        document.getElementById(
            "contact-phone"
        ).value.trim();


    const status =
        document.getElementById(
            "status"
        ).value;


    const payload = {

        location_id:
            Number(locationId),

        name:
            name,

        capacity:
            Number(capacity),

        current_occupancy:
            Number(occupancy),

        contact_phone:
            phone || null,

        status:
            status

    };


    /*
     * Frontend validation
     */

    if (Number(capacity) <= 0) {

        alert(
            "Capacity must be greater than 0."
        );

        return;

    }


    if (Number(occupancy) < 0) {

        alert(
            "Current occupancy cannot be negative."
        );

        return;

    }


    if (
        Number(occupancy) >
        Number(capacity)
    ) {

        alert(
            "Current occupancy cannot exceed capacity."
        );

        return;

    }


    try {

        const saveButton =
            document.getElementById(
                "save-shelter-btn"
            );


        if (saveButton) {

            saveButton.disabled = true;

            saveButton.textContent =
                "Saving...";

        }


        let url =
            `${API_BASE_URL}/api/shelters/`;


        let method =
            "POST";


        if (id) {

            url =
                `${API_BASE_URL}/api/shelters/${id}`;

            method =
                "PUT";

        }


        const response =
            await fetch(
                url,
                {
                    method: method,

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(payload)
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            let message =
                `Request failed (${response.status})`;


            if (data.detail) {

                message =
                    typeof data.detail === "string"
                        ? data.detail
                        : JSON.stringify(
                            data.detail
                        );

            }


            throw new Error(message);

        }


        closeModal();

        await loadShelters();


    } catch (error) {

        console.error(
            "Save shelter error:",
            error
        );


        alert(
            `Could not save shelter.\n\n${error.message}`
        );


    } finally {

        const saveButton =
            document.getElementById(
                "save-shelter-btn"
            );


        if (saveButton) {

            saveButton.disabled = false;

            saveButton.textContent =
                "Save Shelter";

        }

    }

}


/* ================================
   DELETE SHELTER
================================ */

async function deleteShelter(id) {

    const shelter =
        allShelters.find(
            item =>
                Number(
                    item.shelter_id
                ) === Number(id)
        );


    const name =
        shelter?.name ??
        `Shelter #${id}`;


    const confirmed =
        confirm(
            `Are you sure you want to delete "${name}"?`
        );


    if (!confirmed) {
        return;
    }


    try {

        const response =
            await fetch(
                `${API_BASE_URL}/api/shelters/${id}`,
                {
                    method: "DELETE"
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            let message =
                `Delete failed (${response.status})`;


            if (data.detail) {

                message =
                    typeof data.detail === "string"
                        ? data.detail
                        : JSON.stringify(
                            data.detail
                        );

            }


            throw new Error(message);

        }


        await loadShelters();


    } catch (error) {

        console.error(
            "Delete shelter error:",
            error
        );


        alert(
            `Could not delete shelter.\n\n${error.message}`
        );

    }

}


/* ================================
   MODAL
================================ */

function showModal() {

    document
        .getElementById(
            "shelter-modal"
        )
        ?.classList.add("show");

}


function closeModal() {

    document
        .getElementById(
            "shelter-modal"
        )
        ?.classList.remove("show");


    editingShelterId = null;

}


/* ================================
   STATUS CLASS
================================ */

function getStatusClass(status) {

    const value =
        normalize(status);


    if (value === "available") {
        return "badge-available";
    }


    if (value === "full") {
        return "badge-full";
    }


    if (value === "closed") {
        return "badge-closed";
    }


    return "badge-closed";

}


/* ================================
   HELPERS
================================ */

function normalize(value) {

    return String(
        value ?? ""
    )
        .trim()
        .toLowerCase()
        .replace(
            /[\s-]+/g,
            "_"
        );

}


function formatNumber(value) {

    return Number(
        value || 0
    )
        .toLocaleString("en-IN");

}


function showError(message) {

    const errorBox =
        document.getElementById(
            "page-error"
        );


    if (!errorBox) {
        return;
    }


    errorBox.innerHTML = `
        <div class="page-error-box">
            ${escapeHTML(message)}
        </div>
    `;

}


function hideError() {

    const errorBox =
        document.getElementById(
            "page-error"
        );


    if (errorBox) {
        errorBox.innerHTML = "";
    }

}