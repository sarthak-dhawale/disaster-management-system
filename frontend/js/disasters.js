/* ================================
   DISASTERS MODULE
================================ */

let allDisasters = [];
let editingDisasterId = null;


/* ================================
   PAGE LOAD
================================ */

document.addEventListener("DOMContentLoaded", () => {

    loadDisasters();

    setupEventListeners();

});


/* ================================
   EVENT LISTENERS
================================ */

function setupEventListeners() {

    document
        .getElementById("add-disaster-btn")
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
        .getElementById("disaster-form")
        ?.addEventListener(
            "submit",
            saveDisaster
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
        .getElementById("severity-filter")
        ?.addEventListener(
            "change",
            applyFilters
        );


    document
        .getElementById("refresh-btn")
        ?.addEventListener(
            "click",
            loadDisasters
        );


    /* Close modal by clicking outside */

    document
        .getElementById("disaster-modal")
        ?.addEventListener(
            "click",
            event => {

                if (
                    event.target.id ===
                    "disaster-modal"
                ) {

                    closeModal();

                }

            }
        );

}


/* ================================
   LOAD DISASTERS
================================ */

async function loadDisasters() {

    const tableBody =
        document.getElementById(
            "disaster-table-body"
        );


    if (!tableBody) {
        return;
    }


    tableBody.innerHTML = `
        <tr>
            <td colspan="7">
                <div class="loading">
                    Loading disasters...
                </div>
            </td>
        </tr>
    `;


    hideError();


    try {

        const response =
            await fetch(
                `${API_BASE_URL}/api/disasters/`
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
         *     count: 8,
         *     disasters: [...]
         * }
         */

        allDisasters =
            Array.isArray(data.disasters)
                ? data.disasters
                : [];


        updateStatistics();

        applyFilters();


    } catch (error) {

        console.error(
            "Failed to load disasters:",
            error
        );


        tableBody.innerHTML = `
            <tr>
                <td colspan="7">
                    <div class="empty-state">
                        Could not load disaster data.
                    </div>
                </td>
            </tr>
        `;


        showError(
            "Could not load disaster data. Make sure the FastAPI backend is running."
        );

    }

}


/* ================================
   UPDATE STATISTICS
================================ */

function updateStatistics() {

    const total =
        allDisasters.length;


    const active =
        allDisasters.filter(
            disaster =>
                normalize(
                    disaster.status
                ) === "active"
        ).length;


    const critical =
        allDisasters.filter(
            disaster =>
                normalize(
                    disaster.severity
                ) === "critical"
        ).length;


    const resolved =
        allDisasters.filter(
            disaster =>
                normalize(
                    disaster.status
                ) === "resolved"
        ).length;


    setText(
        "total-count",
        total
    );


    setText(
        "active-count",
        active
    );


    setText(
        "critical-count",
        critical
    );


    setText(
        "resolved-count",
        resolved
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


    const severity =
        normalize(
            document.getElementById(
                "severity-filter"
            )?.value
        );


    const filtered =
        allDisasters.filter(
            disaster => {

                const title =
                    normalize(
                        disaster.title
                    );


                const type =
                    normalize(
                        disaster.disaster_type
                    );


                const description =
                    normalize(
                        disaster.description
                    );


                const disasterStatus =
                    normalize(
                        disaster.status
                    );


                const disasterSeverity =
                    normalize(
                        disaster.severity
                    );


                const matchesSearch =
                    !search ||
                    title.includes(search) ||
                    type.includes(search) ||
                    description.includes(search);


                const matchesStatus =
                    !status ||
                    disasterStatus === status;


                const matchesSeverity =
                    !severity ||
                    disasterSeverity === severity;


                return (
                    matchesSearch &&
                    matchesStatus &&
                    matchesSeverity
                );

            }
        );


    renderDisasters(filtered);

}


/* ================================
   RENDER TABLE
================================ */

function renderDisasters(disasters) {

    const tableBody =
        document.getElementById(
            "disaster-table-body"
        );


    if (!tableBody) {
        return;
    }


    if (!disasters.length) {

        tableBody.innerHTML = `
            <tr>
                <td colspan="7">
                    <div class="empty-state">
                        No disasters match your search.
                    </div>
                </td>
            </tr>
        `;

        return;
    }


    tableBody.innerHTML =
        disasters
            .map(
                disaster => {

                    const id =
                        disaster.disaster_id;


                    const title =
                        disaster.title ??
                        "Untitled";


                    const type =
                        disaster.disaster_type ??
                        "-";


                    const severity =
                        disaster.severity ??
                        "-";


                    const status =
                        disaster.status ??
                        "-";


                    const location =
                        disaster.location_id ??
                        "-";


                    return `
                        <tr>

                            <td>
                                ${escapeHTML(id)}
                            </td>


                            <td>
                                <strong>
                                    ${escapeHTML(title)}
                                </strong>
                            </td>


                            <td>
                                ${escapeHTML(type)}
                            </td>


                            <td>

                                <span
                                    class="badge ${getSeverityClass(severity)}">

                                    ${escapeHTML(severity)}

                                </span>

                            </td>


                            <td>

                                <span
                                    class="badge ${getStatusClass(status)}">

                                    ${escapeHTML(status)}

                                </span>

                            </td>


                            <td>
                                ${escapeHTML(location)}
                            </td>


                            <td>

                                <div class="action-buttons">

                                    <button
                                        class="action-btn edit-btn"
                                        title="Edit"
                                        onclick="editDisaster(${id})">

                                        ✏️

                                    </button>


                                    <button
                                        class="action-btn delete-btn"
                                        title="Delete"
                                        onclick="deleteDisaster(${id})">

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
   OPEN ADD MODAL
================================ */

function openAddModal() {

    editingDisasterId = null;


    document.getElementById(
        "modal-title"
    ).textContent =
        "Add Disaster";


    document.getElementById(
        "disaster-form"
    ).reset();


    document.getElementById(
        "disaster-id"
    ).value = "";


    document.getElementById(
        "status"
    ).value =
        "ACTIVE";


    /*
     * Set current date/time automatically.
     * User can change it.
     */

    const now =
        new Date();


    const localDateTime =
        new Date(
            now.getTime()
            -
            now.getTimezoneOffset() * 60000
        )
            .toISOString()
            .slice(0, 16);


    document.getElementById(
        "start-time"
    ).value =
        localDateTime;


    showModal();

}


/* ================================
   EDIT DISASTER
================================ */

function editDisaster(id) {

    const disaster =
        allDisasters.find(
            item =>
                Number(
                    item.disaster_id
                ) === Number(id)
        );


    if (!disaster) {

        showError(
            "Disaster record could not be found."
        );

        return;
    }


    editingDisasterId =
        disaster.disaster_id;


    document.getElementById(
        "modal-title"
    ).textContent =
        "Edit Disaster";


    document.getElementById(
        "disaster-id"
    ).value =
        disaster.disaster_id;


    document.getElementById(
        "disaster-name"
    ).value =
        disaster.title ?? "";


    document.getElementById(
        "disaster-type"
    ).value =
        disaster.disaster_type ?? "";


    document.getElementById(
        "severity"
    ).value =
        disaster.severity ?? "";


    document.getElementById(
        "status"
    ).value =
        disaster.status ?? "ACTIVE";


    document.getElementById(
        "location-id"
    ).value =
        disaster.location_id ?? "";


    /*
     * reported_by is not part of DisasterUpdate,
     * so we don't need to send it during edit.
     */

    const reportedBy =
        document.getElementById(
            "reported-by"
        );


    if (reportedBy) {

        reportedBy.value =
            disaster.reported_by ?? "";

        reportedBy.removeAttribute(
            "required"
        );

    }


    document.getElementById(
        "description"
    ).value =
        disaster.description ?? "";


    /*
     * Convert backend datetime into
     * datetime-local format.
     */

    if (disaster.start_time) {

        const formatted =
            String(
                disaster.start_time
            )
                .replace(" ", "T")
                .slice(0, 16);


        document.getElementById(
            "start-time"
        ).value =
            formatted;

    } else {

        document.getElementById(
            "start-time"
        ).value = "";

    }


    /*
     * Start time is required for CREATE,
     * but optional for UPDATE.
     */

    document.getElementById(
        "start-time"
    ).removeAttribute(
        "required"
    );


    showModal();

}


/* ================================
   SAVE DISASTER
================================ */

async function saveDisaster(event) {

    event.preventDefault();


    const id =
        document.getElementById(
            "disaster-id"
        ).value;


    const title =
        document.getElementById(
            "disaster-name"
        ).value.trim();


    const disasterType =
        document.getElementById(
            "disaster-type"
        ).value;


    const severity =
        document.getElementById(
            "severity"
        ).value;


    const status =
        document.getElementById(
            "status"
        ).value;


    const locationId =
        document.getElementById(
            "location-id"
        ).value;


    const reportedBy =
        document.getElementById(
            "reported-by"
        ).value;


    const description =
        document.getElementById(
            "description"
        ).value.trim();


    const startTime =
        document.getElementById(
            "start-time"
        ).value;


    /* ================================
       CREATE
    ================================= */

    if (!id) {

        if (!reportedBy) {

            alert(
                "Please enter the User ID who reported this disaster."
            );

            return;

        }


        if (!startTime) {

            alert(
                "Please select the disaster start date and time."
            );

            return;

        }


        const payload = {

            location_id:
                Number(locationId),

            reported_by:
                Number(reportedBy),

            disaster_type:
                disasterType,

            title:
                title,

            description:
                description || null,

            severity:
                severity,

            status:
                status,

            start_time:
                startTime,

            end_time:
                null

        };


        await sendDisasterRequest(
            `${API_BASE_URL}/api/disasters/`,
            "POST",
            payload
        );


        return;

    }


    /* ================================
       UPDATE
    ================================= */

    const payload = {

        location_id:
            Number(locationId),

        disaster_type:
            disasterType,

        title:
            title,

        description:
            description || null,

        severity:
            severity,

        status:
            status,

        start_time:
            startTime
                ? startTime
                : null

    };


    await sendDisasterRequest(
        `${API_BASE_URL}/api/disasters/${id}`,
        "PUT",
        payload
    );

}


/* ================================
   SEND API REQUEST
================================ */

async function sendDisasterRequest(
    url,
    method,
    payload
) {

    try {

        const saveButton =
            document.getElementById(
                "save-disaster-btn"
            );


        if (saveButton) {

            saveButton.disabled = true;

            saveButton.textContent =
                "Saving...";

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


        console.log(
            "Disaster saved successfully:",
            data
        );


        closeModal();

        await loadDisasters();


    } catch (error) {

        console.error(
            "Save disaster error:",
            error
        );


        alert(
            `Could not save disaster.\n\n${error.message}`
        );


    } finally {

        const saveButton =
            document.getElementById(
                "save-disaster-btn"
            );


        if (saveButton) {

            saveButton.disabled = false;

            saveButton.textContent =
                "Save Disaster";

        }

    }

}


/* ================================
   DELETE DISASTER
================================ */

async function deleteDisaster(id) {

    const disaster =
        allDisasters.find(
            item =>
                Number(
                    item.disaster_id
                ) === Number(id)
        );


    const title =
        disaster?.title ??
        `Disaster #${id}`;


    const confirmed =
        confirm(
            `Are you sure you want to delete "${title}"?`
        );


    if (!confirmed) {
        return;
    }


    try {

        const response =
            await fetch(
                `${API_BASE_URL}/api/disasters/${id}`,
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


        await loadDisasters();


    } catch (error) {

        console.error(
            "Delete disaster error:",
            error
        );


        alert(
            `Could not delete disaster.\n\n${error.message}`
        );

    }

}


/* ================================
   MODAL
================================ */

function showModal() {

    document
        .getElementById(
            "disaster-modal"
        )
        ?.classList.add("show");

}


function closeModal() {

    document
        .getElementById(
            "disaster-modal"
        )
        ?.classList.remove("show");


    /*
     * Restore CREATE requirements
     * for the next time the modal opens.
     */

    document
        .getElementById(
            "reported-by"
        )
        ?.setAttribute(
            "required",
            ""
        );


    document
        .getElementById(
            "start-time"
        )
        ?.setAttribute(
            "required",
            ""
        );


    editingDisasterId = null;

}


/* ================================
   ERROR
================================ */

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


function getSeverityClass(severity) {

    const value =
        normalize(severity);


    if (value === "critical") {
        return "badge-critical";
    }


    if (value === "high") {
        return "badge-high";
    }


    if (value === "medium") {
        return "badge-medium";
    }


    if (value === "low") {
        return "badge-low";
    }


    return "badge-default";

}


function getStatusClass(status) {

    const value =
        normalize(status);


    if (value === "active") {
        return "badge-active";
    }


    if (value === "resolved") {
        return "badge-resolved";
    }


    if (value === "contained") {
        return "badge-default";
    }


    return "badge-default";

}