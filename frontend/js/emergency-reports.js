const REPORTS_API = `${API_BASE_URL}/api/emergency-reports`;

let allReports = [];
let editingReportId = null;


/* =========================================
   INITIAL LOAD
   ========================================= */

document.addEventListener("DOMContentLoaded", () => {
    loadReports();
});


/* =========================================
   LOAD REPORTS
   ========================================= */

async function loadReports() {

    const tableBody = document.getElementById("reports-table-body");

    tableBody.innerHTML = `
        <tr>
            <td colspan="10" class="loading">
                Loading emergency reports...
            </td>
        </tr>
    `;

    try {

        const response = await fetch(`${REPORTS_API}/`);

        if (!response.ok) {
            throw new Error("Failed to load emergency reports");
        }

        const data = await response.json();

        allReports = data.emergency_reports || [];

        updateStats();
        filterReports();

    } catch (error) {

        console.error(error);

        tableBody.innerHTML = `
            <tr>
                <td colspan="10" style="text-align:center; padding:30px;">
                    <strong>Failed to load emergency reports.</strong>
                    <br>
                    <small>Make sure the FastAPI backend is running.</small>
                </td>
            </tr>
        `;
    }
}


/* =========================================
   UPDATE STATISTICS
   ========================================= */

function updateStats() {

    const total = allReports.length;

    const pending = allReports.filter(
        report => report.status === "PENDING"
    ).length;

    const inProgress = allReports.filter(
        report => report.status === "IN_PROGRESS"
    ).length;

    const resolved = allReports.filter(
        report => report.status === "RESOLVED"
    ).length;

    const critical = allReports.filter(
        report => report.severity === "CRITICAL"
    ).length;

    setText("total-count", total);
    setText("pending-count", pending);
    setText("progress-count", inProgress);
    setText("resolved-count", resolved);
    setText("critical-count", critical);
}


/* =========================================
   FILTER REPORTS
   ========================================= */

function filterReports() {

    const searchValue =
        document.getElementById("search-input").value
            .trim()
            .toLowerCase();

    const statusValue =
        document.getElementById("status-filter").value;

    const severityValue =
        document.getElementById("severity-filter").value;


    const filteredReports = allReports.filter(report => {

        const searchableText = [
            report.report_id,
            report.disaster_id,
            report.location_id,
            report.city,
            report.district,
            report.state,
            report.reported_by,
            report.reported_by_name,
            report.report_type,
            report.description,
            report.severity,
            report.status
        ]
            .map(value => value ?? "")
            .join(" ")
            .toLowerCase();


        const matchesSearch =
            !searchValue ||
            searchableText.includes(searchValue);


        const matchesStatus =
            !statusValue ||
            report.status === statusValue;


        const matchesSeverity =
            !severityValue ||
            report.severity === severityValue;


        return (
            matchesSearch &&
            matchesStatus &&
            matchesSeverity
        );
    });


    renderReports(filteredReports);
}


/* =========================================
   RENDER REPORTS
   ========================================= */

function renderReports(reports) {

    const tableBody =
        document.getElementById("reports-table-body");


    if (reports.length === 0) {

        tableBody.innerHTML = `
            <tr>
                <td colspan="10" style="text-align:center; padding:35px;">
                    No emergency reports found.
                </td>
            </tr>
        `;

        return;
    }


    tableBody.innerHTML = reports.map(report => {

        const location = [
            report.city,
            report.district,
            report.state
        ]
            .filter(Boolean)
            .map(escapeHTML)
            .join(", ");


        const reportedBy =
            report.reported_by_name
                ? escapeHTML(report.reported_by_name)
                : report.reported_by
                    ? `User #${escapeHTML(report.reported_by)}`
                    : "—";


        const disaster =
            report.disaster_id
                ? `Disaster #${escapeHTML(report.disaster_id)}`
                : "—";


        return `
            <tr>

                <td>
                    <strong>#${escapeHTML(report.report_id)}</strong>
                </td>


                <td class="report-type-cell">

                    <span class="report-badge">
                        ${formatReportType(report.report_type)}
                    </span>

                </td>


                <td class="description-cell"
                    title="${escapeHTML(report.description)}">

                    ${escapeHTML(
                        truncateText(report.description, 70)
                    )}

                </td>


                <td class="location-cell">

                    <strong>${location || "—"}</strong>

                    <br>

                    <small>
                        Location #${escapeHTML(report.location_id)}
                    </small>

                    <br>

                    <small>
                        ${disaster}
                    </small>

                </td>


                <td>
                    ${reportedBy}
                </td>


                <td>
                    <span class="severity-badge ${getSeverityClass(report.severity)}">
                        ${escapeHTML(report.severity)}
                    </span>
                </td>


                <td>
                    <span class="status-badge ${getStatusClass(report.status)}">
                        ${formatStatus(report.status)}
                    </span>
                </td>


                <td>
                    ${formatDate(report.reported_at)}
                </td>


                <td>
                    ${formatDate(report.resolved_at)}
                </td>


                <td>

                    <div class="action-buttons">

                        <button
                            class="action-btn edit-btn"
                            onclick="openEditModal(${report.report_id})"
                        >
                            Edit
                        </button>

                        <button
                            class="action-btn delete-btn"
                            onclick="deleteReport(${report.report_id})"
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
   FORMAT REPORT TYPE
   ========================================= */

function formatReportType(type) {

    if (!type) {
        return "—";
    }

    return type
        .split("_")
        .map(word =>
            word.charAt(0) + word.slice(1).toLowerCase()
        )
        .join(" ");
}


/* =========================================
   FORMAT STATUS
   ========================================= */

function formatStatus(status) {

    if (!status) {
        return "—";
    }

    return status
        .split("_")
        .map(word =>
            word.charAt(0) + word.slice(1).toLowerCase()
        )
        .join(" ");
}


/* =========================================
   SEVERITY CLASS
   ========================================= */

function getSeverityClass(severity) {

    switch (severity) {

        case "LOW":
            return "severity-low";

        case "MEDIUM":
            return "severity-medium";

        case "HIGH":
            return "severity-high";

        case "CRITICAL":
            return "severity-critical";

        default:
            return "";
    }
}


/* =========================================
   STATUS CLASS
   ========================================= */

function getStatusClass(status) {

    switch (status) {

        case "PENDING":
            return "status-pending";

        case "IN_PROGRESS":
            return "status-in-progress";

        case "RESOLVED":
            return "status-resolved";

        case "REJECTED":
            return "status-rejected";

        default:
            return "";
    }
}


/* =========================================
   FORMAT DATE
   ========================================= */

function formatDate(value) {

    if (!value) {
        return "—";
    }

    const date = new Date(value);

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


/* =========================================
   OPEN ADD MODAL
   ========================================= */

function openAddModal() {

    editingReportId = null;

    document.getElementById("modal-title").textContent =
        "Add Emergency Report";

    document.getElementById("report-form").reset();

    document.getElementById("report-id").value = "";

    document.getElementById("status").value = "PENDING";

    document.getElementById("report-modal").classList.add("show");
}


/* =========================================
   OPEN EDIT MODAL
   ========================================= */

async function openEditModal(reportId) {

    try {

        const response =
            await fetch(`${REPORTS_API}/${reportId}`);

        if (!response.ok) {
            throw new Error("Failed to fetch report");
        }

        const report = await response.json();

        editingReportId = reportId;

        document.getElementById("modal-title").textContent =
            "Edit Emergency Report";


        document.getElementById("report-id").value =
            report.report_id;


        document.getElementById("disaster-id").value =
            report.disaster_id ?? "";


        document.getElementById("location-id").value =
            report.location_id ?? "";


        document.getElementById("reported-by").value =
            report.reported_by ?? "";


        document.getElementById("report-type").value =
            report.report_type ?? "";


        document.getElementById("description").value =
            report.description ?? "";


        document.getElementById("severity").value =
            report.severity ?? "";


        document.getElementById("status").value =
            report.status ?? "PENDING";


        document.getElementById("resolved-at").value =
            convertToDateTimeLocal(report.resolved_at);


        document.getElementById("report-modal")
            .classList.add("show");


    } catch (error) {

        console.error(error);

        alert("Failed to load emergency report.");
    }
}


/* =========================================
   SAVE REPORT
   ========================================= */

async function saveReport(event) {

    event.preventDefault();


    const disasterIdValue =
        document.getElementById("disaster-id").value.trim();

    const reportedByValue =
        document.getElementById("reported-by").value.trim();

    const resolvedAtValue =
        document.getElementById("resolved-at").value.trim();


    const payload = {

        disaster_id:
            disasterIdValue
                ? Number(disasterIdValue)
                : null,

        location_id:
            Number(
                document.getElementById("location-id").value
            ),

        reported_by:
            reportedByValue
                ? Number(reportedByValue)
                : null,

        report_type:
            document.getElementById("report-type").value,

        description:
            document.getElementById("description").value.trim(),

        severity:
            document.getElementById("severity").value,

        status:
            document.getElementById("status").value
    };


    /* -----------------------------------------
       FRONTEND VALIDATION
       ----------------------------------------- */

    if (!payload.location_id || payload.location_id < 1) {
        alert("Please enter a valid Location ID.");
        return;
    }

    if (!payload.report_type) {
        alert("Please select a report type.");
        return;
    }

    if (!payload.description) {
        alert("Please enter a description.");
        return;
    }

    if (!payload.severity) {
        alert("Please select severity.");
        return;
    }

    if (!payload.status) {
        alert("Please select status.");
        return;
    }


    /* -----------------------------------------
       RESOLVED AT
       ----------------------------------------- */

    if (editingReportId !== null) {

        payload.resolved_at =
            resolvedAtValue
                ? new Date(resolvedAtValue).toISOString()
                : null;
    }


    try {

        let response;

        if (editingReportId === null) {

            response = await fetch(`${REPORTS_API}/`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });

        } else {

            response = await fetch(
                `${REPORTS_API}/${editingReportId}`,
                {
                    method: "PUT",
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
                data.detail || "Failed to save emergency report"
            );
        }


        alert(
            editingReportId === null
                ? "Emergency report added successfully!"
                : "Emergency report updated successfully!"
        );


        closeModal();

        await loadReports();


    } catch (error) {

        console.error(error);

        alert(error.message);
    }
}


/* =========================================
   DELETE REPORT
   ========================================= */

async function deleteReport(reportId) {

    const confirmed = confirm(
        `Are you sure you want to delete Emergency Report #${reportId}?`
    );


    if (!confirmed) {
        return;
    }


    try {

        const response =
            await fetch(`${REPORTS_API}/${reportId}`, {
                method: "DELETE"
            });


        const data = await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail || "Failed to delete report"
            );
        }


        alert("Emergency report deleted successfully!");

        await loadReports();


    } catch (error) {

        console.error(error);

        alert(error.message);
    }
}


/* =========================================
   CLOSE MODAL
   ========================================= */

function closeModal() {

    document.getElementById("report-modal")
        .classList.remove("show");

    editingReportId = null;
}


/* =========================================
   CLOSE MODAL WHEN CLICKING OUTSIDE
   ========================================= */

document.addEventListener("click", (event) => {

    const modal =
        document.getElementById("report-modal");

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
   DATETIME LOCAL CONVERSION
   ========================================= */

function convertToDateTimeLocal(value) {

    if (!value) {
        return "";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return "";
    }

    const year = date.getFullYear();

    const month = String(
        date.getMonth() + 1
    ).padStart(2, "0");

    const day = String(
        date.getDate()
    ).padStart(2, "0");

    const hours = String(
        date.getHours()
    ).padStart(2, "0");

    const minutes = String(
        date.getMinutes()
    ).padStart(2, "0");


    return `${year}-${month}-${day}T${hours}:${minutes}`;
}