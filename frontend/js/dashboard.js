/* ================================
   DASHBOARD
================================ */

document.addEventListener("DOMContentLoaded", () => {
    loadDashboard();
});


/* ================================
   LOAD DASHBOARD
================================ */

async function loadDashboard() {

    try {

        const response =
            await fetch(`${API_BASE_URL}/api/dashboard/`);


        if (!response.ok) {
            throw new Error(
                `Dashboard API returned ${response.status}`
            );
        }


        const data =
            await response.json();


        updateDashboard(data);

        loadDisasters();

        loadResources();


    } catch (error) {

        console.error(
            "Dashboard error:",
            error
        );


        const errorBox =
            document.getElementById(
                "dashboard-error"
            );


        if (errorBox) {

            errorBox.innerHTML = `
                <div class="error-state">
                    Unable to load dashboard data.
                    Make sure the FastAPI backend is running.
                </div>
            `;

        }

    }

}


/* ================================
   UPDATE DASHBOARD
================================ */

function updateDashboard(data) {


    /* MAIN STATISTICS */

    setText(
        "total-disasters",
        data.disasters?.total ?? 0
    );


    setText(
        "active-disasters",
        data.disasters?.active ?? 0
    );


    setText(
        "available-shelters",
        data.shelters?.available ?? 0
    );


    setText(
        "available-volunteers",
        data.volunteers?.available ?? 0
    );


    setText(
        "available-resources",
        formatNumber(
            data.resources?.available_quantity ?? 0
        )
    );


    setText(
        "emergency-reports",
        data.emergency_reports?.total ?? 0
    );


    /* SHELTER OCCUPANCY */

    const occupancy =
        data.shelters?.total_occupancy ?? 0;


    const capacity =
        data.shelters?.total_capacity ?? 0;


    const percentage =
        capacity > 0
            ? Math.round(
                (occupancy / capacity) * 100
            )
            : 0;


    setText(
        "occupancy-current",
        formatNumber(occupancy)
    );


    setText(
        "occupancy-total",
        `/ ${formatNumber(capacity)}`
    );


    setText(
        "occupancy-percent",
        `${percentage}% occupied`
    );


    const progress =
        document.getElementById(
            "occupancy-progress"
        );


    if (progress) {
        progress.style.width =
            `${percentage}%`;
    }


    /* QUICK SUMMARY */

    setText(
        "critical-disasters",
        data.disasters?.critical ?? 0
    );


    setText(
        "resolved-disasters",
        data.disasters?.resolved ?? 0
    );


    setText(
        "pending-reports",
        data.emergency_reports?.pending ?? 0
    );


    setText(
        "active-reports",
        data.emergency_reports?.in_progress ?? 0
    );


    setText(
        "registered-people",
        data.shelter_registrations?.active ?? 0
    );


    setText(
        "assigned-volunteers",
        data.volunteer_assignments?.active ?? 0
    );


    /* EMERGENCY REPORT CARD */

    setText(
        "pending-reports-2",
        data.emergency_reports?.pending ?? 0
    );


    setText(
        "active-reports-2",
        data.emergency_reports?.in_progress ?? 0
    );


    setText(
        "resolved-reports",
        data.emergency_reports?.resolved ?? 0
    );


    setText(
        "critical-reports",
        data.emergency_reports?.critical ?? 0
    );

}


/* ================================
   LOAD ACTIVE DISASTERS
================================ */

async function loadDisasters() {

    const tableBody =
        document.getElementById(
            "disaster-table-body"
        );


    if (!tableBody) {
        return;
    }


    try {

        const response =
            await fetch(
                `${API_BASE_URL}/api/disasters/`
            );


        if (!response.ok) {

            throw new Error(
                `Disaster API returned ${response.status}`
            );

        }


        const data =
            await response.json();


        /*
         * IMPORTANT
         *
         * /api/disasters/ returns:
         *
         * {
         *     count: 8,
         *     disasters: [...]
         * }
         *
         * Therefore we must use
         * data.disasters.
         */

        const disasters =
            Array.isArray(data.disasters)
                ? data.disasters
                : [];


        const activeDisasters =
            disasters.filter(
                disaster =>
                    String(
                        disaster.status
                    ).toLowerCase() !== "resolved"
            );


        if (activeDisasters.length === 0) {

            tableBody.innerHTML = `
                <tr>
                    <td colspan="5">
                        <div class="empty-state">
                            No active disasters found.
                        </div>
                    </td>
                </tr>
            `;

            return;
        }


        tableBody.innerHTML =
            activeDisasters
                .slice(0, 5)
                .map(disaster => {

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
                                ${escapeHTML(title)}
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

                        </tr>
                    `;

                })
                .join("");


    } catch (error) {

        console.error(
            "Disaster loading error:",
            error
        );


        tableBody.innerHTML = `
            <tr>
                <td colspan="5">
                    <div class="error-state">
                        Could not load disaster data.
                    </div>
                </td>
            </tr>
        `;

    }

}


/* ================================
   LOAD RESOURCES
================================ */

async function loadResources() {

    const resourceList =
        document.getElementById(
            "resource-list"
        );


    if (!resourceList) {
        return;
    }


    try {

        const response =
            await fetch(
                `${API_BASE_URL}/api/resources/`
            );


        if (!response.ok) {

            throw new Error(
                `Resource API returned ${response.status}`
            );

        }


        const data =
            await response.json();


        /*
         * Support both:
         *
         * [...]
         *
         * and:
         *
         * {
         *     resources: [...]
         * }
         */

        const resources =
            Array.isArray(data)
                ? data
                : Array.isArray(data.resources)
                    ? data.resources
                    : [];


        if (resources.length === 0) {

            resourceList.innerHTML = `
                <div class="empty-state">
                    No resources found.
                </div>
            `;

            return;
        }


        resourceList.innerHTML =
            resources
                .slice(0, 6)
                .map(resource => {

                    const name =
                        resource.resource_name ??
                        resource.name ??
                        resource.resource_type ??
                        resource.type ??
                        "Resource";


                    const quantity =
                        resource.available_quantity ??
                        resource.quantity ??
                        0;


                    return `
                        <div class="resource-item">

                            <span class="resource-name">
                                ${escapeHTML(name)}
                            </span>

                            <span class="resource-quantity">
                                ${formatNumber(quantity)}
                            </span>

                        </div>
                    `;

                })
                .join("");


    } catch (error) {

        console.error(
            "Resource loading error:",
            error
        );


        resourceList.innerHTML = `
            <div class="error-state">
                Could not load resources.
            </div>
        `;

    }

}


/* ================================
   NUMBER FORMAT
================================ */

function formatNumber(value) {

    return Number(value || 0)
        .toLocaleString("en-IN");

}


/* ================================
   SEVERITY CLASS
================================ */

function getSeverityClass(severity) {

    const value =
        String(severity ?? "")
            .trim()
            .toLowerCase();


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


/* ================================
   STATUS CLASS
================================ */

function getStatusClass(status) {

    const value =
        String(status ?? "")
            .trim()
            .toLowerCase()
            .replace(/[\s-]+/g, "_");


    if (value === "active") {
        return "badge-active";
    }


    if (value === "resolved") {
        return "badge-resolved";
    }


    if (value === "pending") {
        return "badge-pending";
    }


    if (value === "in_progress") {
        return "badge-progress";
    }


    return "badge-default";

}