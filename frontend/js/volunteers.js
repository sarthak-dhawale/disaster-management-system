let allVolunteers = [];
let editingVolunteerId = null;


/* =========================
   PAGE LOAD
========================= */

document.addEventListener("DOMContentLoaded", () => {
    loadVolunteers();
});


/* =========================
   LOAD VOLUNTEERS
========================= */

async function loadVolunteers() {

    hideError();

    const tableBody = document.getElementById("volunteers-table-body");

    tableBody.innerHTML = `
        <tr>
            <td colspan="8" class="loading">
                Loading volunteers...
            </td>
        </tr>
    `;

    try {

        const response = await fetch(`${API_BASE_URL}/api/volunteers/`);

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail || "Failed to load volunteers"
            );
        }

        allVolunteers = Array.isArray(data.volunteers)
            ? data.volunteers
            : [];

        updateStatistics();
        applyFilters();

    } catch (error) {

        console.error("Error loading volunteers:", error);

        tableBody.innerHTML = `
            <tr>
                <td colspan="8" class="empty-state">
                    Failed to load volunteers.
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

    const total = allVolunteers.length;

    const available = allVolunteers.filter(
        volunteer =>
            volunteer.availability_status === "AVAILABLE"
    ).length;

    const assigned = allVolunteers.filter(
        volunteer =>
            volunteer.availability_status === "ASSIGNED"
    ).length;

    const unavailable = allVolunteers.filter(
        volunteer =>
            volunteer.availability_status === "UNAVAILABLE"
    ).length;


    setText("total-count", total);
    setText("available-count", available);
    setText("assigned-count", assigned);
    setText("unavailable-count", unavailable);
}


/* =========================
   SEARCH + FILTER
========================= */

function applyFilters() {

    const searchInput =
        document.getElementById("search-input");

    const statusFilter =
        document.getElementById("status-filter");

    const searchTerm =
        searchInput.value.trim().toLowerCase();

    const selectedStatus =
        statusFilter.value;


    const filteredVolunteers = allVolunteers.filter(
        volunteer => {

            const matchesSearch =
                String(volunteer.volunteer_id ?? "")
                    .toLowerCase()
                    .includes(searchTerm) ||

                String(volunteer.user_id ?? "")
                    .toLowerCase()
                    .includes(searchTerm) ||

                String(volunteer.full_name ?? "")
                    .toLowerCase()
                    .includes(searchTerm) ||

                String(volunteer.email ?? "")
                    .toLowerCase()
                    .includes(searchTerm) ||

                String(volunteer.skills ?? "")
                    .toLowerCase()
                    .includes(searchTerm) ||

                String(volunteer.phone ?? "")
                    .toLowerCase()
                    .includes(searchTerm);


            const matchesStatus =
                selectedStatus === "ALL" ||
                volunteer.availability_status === selectedStatus;


            return matchesSearch && matchesStatus;
        }
    );


    renderVolunteers(filteredVolunteers);
}


/* =========================
   RENDER TABLE
========================= */

function renderVolunteers(volunteers) {

    const tableBody =
        document.getElementById("volunteers-table-body");


    if (volunteers.length === 0) {

        tableBody.innerHTML = `
            <tr>
                <td colspan="8" class="empty-state">
                    No volunteers found.
                </td>
            </tr>
        `;

        return;
    }


    tableBody.innerHTML = volunteers.map(
        volunteer => {

            const status =
                volunteer.availability_status || "AVAILABLE";

            const statusClass =
                getStatusClass(status);

            const skills =
                volunteer.skills
                    ? escapeHTML(volunteer.skills)
                    : "—";

            const emergencyContact =
                volunteer.emergency_contact
                    ? escapeHTML(volunteer.emergency_contact)
                    : "—";

            const fullName =
                volunteer.full_name
                    ? escapeHTML(volunteer.full_name)
                    : "Unknown User";

            const email =
                volunteer.email
                    ? escapeHTML(volunteer.email)
                    : "—";

            const phone =
                volunteer.phone
                    ? escapeHTML(volunteer.phone)
                    : "—";

            const joinedDate =
                formatDate(volunteer.joined_at);


            return `
                <tr>

                    <td>
                        ${escapeHTML(volunteer.volunteer_id)}
                    </td>


                    <td>

                        <div class="volunteer-name">

                            <strong>
                                ${fullName}
                            </strong>

                            <small>
                                User ID: ${escapeHTML(volunteer.user_id)}
                            </small>

                        </div>

                    </td>


                    <td>

                        <div class="contact-info">

                            <span>
                                ${email}
                            </span>

                            <small>
                                ${phone}
                            </small>

                        </div>

                    </td>


                    <td>

                        <div class="skills-text">
                            ${skills}
                        </div>

                    </td>


                    <td>

                        <span class="badge ${statusClass}">
                            ${escapeHTML(status)}
                        </span>

                    </td>


                    <td>

                        <span class="emergency-contact">
                            ${emergencyContact}
                        </span>

                    </td>


                    <td>

                        <span class="joined-date">
                            ${joinedDate}
                        </span>

                    </td>


                    <td>

                        <div class="action-buttons">

                            <button
                                class="action-btn edit"
                                title="Edit Volunteer"
                                onclick="editVolunteer(${volunteer.volunteer_id})"
                            >
                                ✏️
                            </button>


                            <button
                                class="action-btn delete"
                                title="Delete Volunteer"
                                onclick="deleteVolunteer(${volunteer.volunteer_id})"
                            >
                                🗑️
                            </button>

                        </div>

                    </td>

                </tr>
            `;
        }
    ).join("");
}


/* =========================
   ADD VOLUNTEER
========================= */

function openAddModal() {

    editingVolunteerId = null;

    document.getElementById("modal-title").textContent =
        "Add Volunteer";

    document.getElementById("modal-subtitle").textContent =
        "Register a new emergency volunteer";

    document.getElementById("save-button").textContent =
        "Save Volunteer";


    document.getElementById("volunteer-form").reset();

    document.getElementById("volunteer-id").value = "";

    document.getElementById("availability-status").value =
        "AVAILABLE";

    hideModalError();


    document
        .getElementById("volunteer-modal")
        .classList.add("show");
}


/* =========================
   EDIT VOLUNTEER
========================= */

function editVolunteer(volunteerId) {

    const volunteer = allVolunteers.find(
        item =>
            Number(item.volunteer_id) === Number(volunteerId)
    );


    if (!volunteer) {

        showError("Volunteer record not found.");

        return;
    }


    editingVolunteerId = volunteer.volunteer_id;


    document.getElementById("modal-title").textContent =
        "Edit Volunteer";

    document.getElementById("modal-subtitle").textContent =
        "Update volunteer information";

    document.getElementById("save-button").textContent =
        "Update Volunteer";


    document.getElementById("volunteer-id").value =
        volunteer.volunteer_id;

    document.getElementById("user-id").value =
        volunteer.user_id;

    document.getElementById("skills").value =
        volunteer.skills || "";

    document.getElementById("availability-status").value =
        volunteer.availability_status || "AVAILABLE";

    document.getElementById("emergency-contact").value =
        volunteer.emergency_contact || "";


    hideModalError();


    document
        .getElementById("volunteer-modal")
        .classList.add("show");
}


/* =========================
   SAVE / UPDATE
========================= */

async function saveVolunteer(event) {

    event.preventDefault();

    hideModalError();


    const userId =
        Number(
            document.getElementById("user-id").value
        );

    const skills =
        document.getElementById("skills").value.trim();

    const availabilityStatus =
        document.getElementById("availability-status").value;

    const emergencyContact =
        document
            .getElementById("emergency-contact")
            .value
            .trim();


    /* FRONTEND VALIDATION */

    if (!userId || userId < 1) {

        showModalError(
            "Please enter a valid User ID."
        );

        return;
    }


    const validStatuses = [
        "AVAILABLE",
        "ASSIGNED",
        "UNAVAILABLE"
    ];


    if (!validStatuses.includes(availabilityStatus)) {

        showModalError(
            "Please select a valid availability status."
        );

        return;
    }


    const payload = {
        user_id: userId,
        skills: skills || null,
        availability_status: availabilityStatus,
        emergency_contact: emergencyContact || null
    };


    const saveButton =
        document.getElementById("save-button");

    saveButton.disabled = true;
    saveButton.textContent = editingVolunteerId
        ? "Updating..."
        : "Saving...";


    try {

        let response;


        if (editingVolunteerId) {

            response = await fetch(
                `${API_BASE_URL}/api/volunteers/${editingVolunteerId}`,
                {
                    method: "PUT",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(payload)
                }
            );

        } else {

            response = await fetch(
                `${API_BASE_URL}/api/volunteers/`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(payload)
                }
            );
        }


        const data = await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Failed to save volunteer"
            );
        }


        alert(
            editingVolunteerId
                ? "Volunteer updated successfully!"
                : "Volunteer created successfully!"
        );


        closeModal();

        await loadVolunteers();


    } catch (error) {

        console.error(
            "Error saving volunteer:",
            error
        );

        showModalError(error.message);


    } finally {

        saveButton.disabled = false;

        saveButton.textContent =
            editingVolunteerId
                ? "Update Volunteer"
                : "Save Volunteer";
    }
}


/* =========================
   DELETE VOLUNTEER
========================= */

async function deleteVolunteer(volunteerId) {

    const volunteer = allVolunteers.find(
        item =>
            Number(item.volunteer_id) === Number(volunteerId)
    );


    if (!volunteer) {

        showError("Volunteer record not found.");

        return;
    }


    const name =
        volunteer.full_name || "this volunteer";


    const confirmed = confirm(
        `Are you sure you want to delete volunteer "${name}"?`
    );


    if (!confirmed) {
        return;
    }


    try {

        const response = await fetch(
            `${API_BASE_URL}/api/volunteers/${volunteerId}`,
            {
                method: "DELETE"
            }
        );


        const data = await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Failed to delete volunteer"
            );
        }


        alert("Volunteer deleted successfully!");


        await loadVolunteers();


    } catch (error) {

        console.error(
            "Error deleting volunteer:",
            error
        );

        showError(error.message);
    }
}


/* =========================
   MODAL
========================= */

function closeModal() {

    document
        .getElementById("volunteer-modal")
        .classList.remove("show");

    hideModalError();

    editingVolunteerId = null;
}


/* Close when clicking outside */

document.addEventListener("click", event => {

    const modal =
        document.getElementById("volunteer-modal");

    if (
        event.target === modal &&
        modal.classList.contains("show")
    ) {
        closeModal();
    }

});


/* Close with Escape */

document.addEventListener("keydown", event => {

    if (event.key === "Escape") {

        const modal =
            document.getElementById("volunteer-modal");

        if (modal.classList.contains("show")) {
            closeModal();
        }

    }

});


/* =========================
   STATUS HELPERS
========================= */

function getStatusClass(status) {

    switch (status) {

        case "AVAILABLE":
            return "badge-available";

        case "ASSIGNED":
            return "badge-assigned";

        case "UNAVAILABLE":
            return "badge-unavailable";

        default:
            return "";
    }
}


/* =========================
   DATE FORMAT
========================= */

function formatDate(value) {

    if (!value) {
        return "—";
    }


    const date = new Date(value);


    if (Number.isNaN(date.getTime())) {
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
   ERROR HANDLING
========================= */

function showError(message) {

    const errorBox =
        document.getElementById("page-error");


    if (!errorBox) {
        return;
    }


    errorBox.innerHTML =
        escapeHTML(message);

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