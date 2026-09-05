const LOCATIONS_API = `${API_BASE_URL}/api/locations`;

let allLocations = [];
let editingLocationId = null;


/* =========================================
   INITIAL LOAD
   ========================================= */

document.addEventListener("DOMContentLoaded", () => {
    loadLocations();
});


/* =========================================
   LOAD LOCATIONS
   ========================================= */

async function loadLocations() {

    const tableBody =
        document.getElementById("locations-table-body");

    tableBody.innerHTML = `
        <tr>
            <td colspan="9" class="loading">
                Loading locations...
            </td>
        </tr>
    `;

    try {

        const response =
            await fetch(`${LOCATIONS_API}/`);

        if (!response.ok) {
            throw new Error("Failed to load locations");
        }

        const data = await response.json();

        allLocations = data.locations || [];

        updateStats();
        filterLocations();

    } catch (error) {

        console.error(error);

        tableBody.innerHTML = `
            <tr>
                <td colspan="9" style="text-align:center; padding:30px;">
                    <strong>Failed to load locations.</strong>
                    <br>
                    <small>
                        Make sure the FastAPI backend is running.
                    </small>
                </td>
            </tr>
        `;
    }
}


/* =========================================
   UPDATE STATISTICS
   ========================================= */

function updateStats() {

    const total =
        allLocations.length;

    const cities =
        new Set(
            allLocations
                .map(location => location.city)
                .filter(Boolean)
                .map(city => city.toLowerCase())
        ).size;

    const districts =
        new Set(
            allLocations
                .map(location => location.district)
                .filter(Boolean)
                .map(district => district.toLowerCase())
        ).size;

    const states =
        new Set(
            allLocations
                .map(location => location.state)
                .filter(Boolean)
                .map(state => state.toLowerCase())
        ).size;


    setText("total-count", total);
    setText("city-count", cities);
    setText("district-count", districts);
    setText("state-count", states);
}


/* =========================================
   FILTER LOCATIONS
   ========================================= */

function filterLocations() {

    const searchValue =
        document.getElementById("search-input")
            .value
            .trim()
            .toLowerCase();


    const filteredLocations =
        allLocations.filter(location => {

            const searchableText = [
                location.location_id,
                location.state,
                location.district,
                location.city,
                location.address,
                location.latitude,
                location.longitude
            ]
                .map(value => value ?? "")
                .join(" ")
                .toLowerCase();


            return (
                !searchValue ||
                searchableText.includes(searchValue)
            );
        });


    renderLocations(filteredLocations);
}


/* =========================================
   RENDER LOCATIONS
   ========================================= */

function renderLocations(locations) {

    const tableBody =
        document.getElementById("locations-table-body");


    if (locations.length === 0) {

        tableBody.innerHTML = `
            <tr>
                <td colspan="9"
                    style="text-align:center; padding:35px;">
                    No locations found.
                </td>
            </tr>
        `;

        return;
    }


    tableBody.innerHTML =
        locations.map(location => {

            return `
                <tr>

                    <td>
                        <strong>
                            #${escapeHTML(location.location_id)}
                        </strong>
                    </td>


                    <td class="city-cell">
                        ${escapeHTML(location.city)}
                    </td>


                    <td>
                        ${escapeHTML(location.district)}
                    </td>


                    <td>
                        ${escapeHTML(location.state)}
                    </td>


                    <td class="address-cell"
                        title="${escapeHTML(location.address)}">

                        ${escapeHTML(
                            truncateText(location.address, 65)
                        )}

                    </td>


                    <td class="coordinate-cell">
                        ${
                            location.latitude !== null &&
                            location.latitude !== undefined
                                ? escapeHTML(
                                    Number(location.latitude)
                                        .toFixed(6)
                                )
                                : "—"
                        }
                    </td>


                    <td class="coordinate-cell">
                        ${
                            location.longitude !== null &&
                            location.longitude !== undefined
                                ? escapeHTML(
                                    Number(location.longitude)
                                        .toFixed(6)
                                )
                                : "—"
                        }
                    </td>


                    <td>
                        ${formatDate(location.created_at)}
                    </td>


                    <td>

                        <div class="action-buttons">

                            <button
                                class="action-btn edit-btn"
                                onclick="openEditModal(${location.location_id})"
                            >
                                Edit
                            </button>

                            <button
                                class="action-btn delete-btn"
                                onclick="deleteLocation(${location.location_id})"
                            >
                                Delete
                            </button>

                        </div>

                    </td>

                </tr>
            `;

        }).join("");
}


/* =========================================
   OPEN ADD MODAL
   ========================================= */

function openAddModal() {

    editingLocationId = null;

    document.getElementById("modal-title").textContent =
        "Add Location";

    document.getElementById("location-form").reset();

    document.getElementById("location-id").value = "";

    document.getElementById("location-modal")
        .classList.add("show");
}


/* =========================================
   OPEN EDIT MODAL
   ========================================= */

async function openEditModal(locationId) {

    try {

        const response =
            await fetch(`${LOCATIONS_API}/${locationId}`);

        if (!response.ok) {
            throw new Error("Failed to fetch location");
        }

        const location =
            await response.json();


        editingLocationId = locationId;


        document.getElementById("modal-title").textContent =
            "Edit Location";


        document.getElementById("location-id").value =
            location.location_id;


        document.getElementById("state").value =
            location.state ?? "";


        document.getElementById("district").value =
            location.district ?? "";


        document.getElementById("city").value =
            location.city ?? "";


        document.getElementById("address").value =
            location.address ?? "";


        document.getElementById("latitude").value =
            location.latitude ?? "";


        document.getElementById("longitude").value =
            location.longitude ?? "";


        document.getElementById("location-modal")
            .classList.add("show");


    } catch (error) {

        console.error(error);

        alert("Failed to load location.");
    }
}


/* =========================================
   SAVE LOCATION
   ========================================= */

async function saveLocation(event) {

    event.preventDefault();


    const state =
        document.getElementById("state")
            .value
            .trim();

    const district =
        document.getElementById("district")
            .value
            .trim();

    const city =
        document.getElementById("city")
            .value
            .trim();

    const address =
        document.getElementById("address")
            .value
            .trim();

    const latitudeValue =
        document.getElementById("latitude")
            .value
            .trim();

    const longitudeValue =
        document.getElementById("longitude")
            .value
            .trim();


    const latitude =
        latitudeValue !== ""
            ? Number(latitudeValue)
            : null;

    const longitude =
        longitudeValue !== ""
            ? Number(longitudeValue)
            : null;


    /* =========================================
       FRONTEND VALIDATION
       ========================================= */

    if (!state) {
        alert("Please enter the state.");
        return;
    }

    if (!district) {
        alert("Please enter the district.");
        return;
    }

    if (!city) {
        alert("Please enter the city.");
        return;
    }

    if (!address) {
        alert("Please enter the address.");
        return;
    }


    if (
        latitude !== null &&
        (latitude < -90 || latitude > 90)
    ) {

        alert(
            "Latitude must be between -90 and 90."
        );

        return;
    }


    if (
        longitude !== null &&
        (longitude < -180 || longitude > 180)
    ) {

        alert(
            "Longitude must be between -180 and 180."
        );

        return;
    }


    const payload = {

        state: state,

        district: district,

        city: city,

        address: address,

        latitude: latitude,

        longitude: longitude
    };


    try {

        let response;


        /* =========================================
           ADD
           ========================================= */

        if (editingLocationId === null) {

            response =
                await fetch(`${LOCATIONS_API}/`, {

                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify(payload)
                });

        }


        /* =========================================
           EDIT
           ========================================= */

        else {

            response =
                await fetch(
                    `${LOCATIONS_API}/${editingLocationId}`,
                    {
                        method: "PUT",

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
                "Failed to save location"
            );
        }


        alert(
            editingLocationId === null
                ? "Location added successfully!"
                : "Location updated successfully!"
        );


        closeModal();

        await loadLocations();


    } catch (error) {

        console.error(error);

        alert(error.message);
    }
}


/* =========================================
   DELETE LOCATION
   ========================================= */

async function deleteLocation(locationId) {

    const confirmed =
        confirm(
            `Are you sure you want to delete Location #${locationId}?`
        );


    if (!confirmed) {
        return;
    }


    try {

        const response =
            await fetch(
                `${LOCATIONS_API}/${locationId}`,
                {
                    method: "DELETE"
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Failed to delete location"
            );
        }


        alert(
            "Location deleted successfully!"
        );


        await loadLocations();


    } catch (error) {

        console.error(error);

        alert(error.message);
    }
}


/* =========================================
   CLOSE MODAL
   ========================================= */

function closeModal() {

    document.getElementById("location-modal")
        .classList.remove("show");

    editingLocationId = null;
}


/* =========================================
   CLICK OUTSIDE MODAL
   ========================================= */

document.addEventListener("click", (event) => {

    const modal =
        document.getElementById("location-modal");


    if (
        event.target === modal &&
        modal.classList.contains("show")
    ) {

        closeModal();
    }
});


/* =========================================
   ESCAPE KEY
   ========================================= */

document.addEventListener("keydown", (event) => {

    if (event.key === "Escape") {
        closeModal();
    }
});


/* =========================================
   FORMAT DATE
   ========================================= */

function formatDate(value) {

    if (!value) {
        return "—";
    }


    const date =
        new Date(value);


    if (Number.isNaN(date.getTime())) {
        return escapeHTML(value);
    }


    return date.toLocaleString("en-IN", {

        day: "2-digit",

        month: "short",

        year: "numeric",

        hour: "2-digit",

        minute: "2-digit"
    });
}


/* =========================================
   TRUNCATE TEXT
   ========================================= */

function truncateText(text, maxLength) {

    if (!text) {
        return "—";
    }


    if (text.length <= maxLength) {
        return text;
    }


    return text.substring(0, maxLength) + "...";
}