const USERS_API = `${API_BASE_URL}/api/users`;

let allUsers = [];

let editingUserId = null;


/* =========================================
   INITIAL LOAD
   ========================================= */

document.addEventListener("DOMContentLoaded", () => {

    loadUsers();

});


/* =========================================
   LOAD USERS
   ========================================= */

async function loadUsers() {

    const tableBody =
        document.getElementById(
            "users-table-body"
        );


    tableBody.innerHTML = `
        <tr>
            <td
                colspan="8"
                class="loading"
            >
                Loading users...
            </td>
        </tr>
    `;


    try {

        const response =
            await fetch(
                `${USERS_API}/`
            );


        if (!response.ok) {

            throw new Error(
                "Failed to load users"
            );

        }


        const data =
            await response.json();


        allUsers =
            data.users || [];


        updateStats();

        filterUsers();


    } catch (error) {

        console.error(error);


        tableBody.innerHTML = `
            <tr>

                <td
                    colspan="8"
                    style="
                        text-align:center;
                        padding:30px;
                    "
                >

                    <strong>
                        Failed to load users.
                    </strong>

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
        allUsers.length;


    const active =
        allUsers.filter(
            user =>
                user.status === "ACTIVE"
        ).length;


    const inactive =
        allUsers.filter(
            user =>
                user.status === "INACTIVE"
        ).length;


    const suspended =
        allUsers.filter(
            user =>
                user.status === "SUSPENDED"
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
        "inactive-count",
        inactive
    );


    setText(
        "suspended-count",
        suspended
    );

}


/* =========================================
   FILTER USERS
   ========================================= */

function filterUsers() {

    const searchValue =
        document.getElementById(
            "search-input"
        )
        .value
        .trim()
        .toLowerCase();


    const roleValue =
        document.getElementById(
            "role-filter"
        ).value;


    const statusValue =
        document.getElementById(
            "status-filter"
        ).value;


    const filteredUsers =
        allUsers.filter(user => {


            const searchableText = [

                user.user_id,

                user.full_name,

                user.email,

                user.phone,

                user.role,

                user.status

            ]
                .map(
                    value =>
                        value ?? ""
                )
                .join(" ")
                .toLowerCase();


            const matchesSearch =
                !searchValue ||
                searchableText.includes(
                    searchValue
                );


            const matchesRole =
                !roleValue ||
                user.role === roleValue;


            const matchesStatus =
                !statusValue ||
                user.status === statusValue;


            return (
                matchesSearch &&
                matchesRole &&
                matchesStatus
            );

        });


    renderUsers(
        filteredUsers
    );

}


/* =========================================
   RENDER USERS
   ========================================= */

function renderUsers(users) {

    const tableBody =
        document.getElementById(
            "users-table-body"
        );


    if (users.length === 0) {

        tableBody.innerHTML = `
            <tr>

                <td
                    colspan="8"
                    style="
                        text-align:center;
                        padding:35px;
                    "
                >
                    No users found.
                </td>

            </tr>
        `;

        return;
    }


    tableBody.innerHTML =
        users.map(user => {


            return `
                <tr>


                    <!-- ID -->

                    <td class="user-id">

                        #${escapeHTML(
                            user.user_id
                        )}

                    </td>



                    <!-- USER -->

                    <td>

                        <div class="user-name">

                            ${escapeHTML(
                                user.full_name
                            )}

                        </div>

                    </td>



                    <!-- EMAIL -->

                    <td class="email-cell">

                        ${escapeHTML(
                            user.email
                        )}

                    </td>



                    <!-- PHONE -->

                    <td>

                        ${
                            user.phone
                                ? escapeHTML(
                                    user.phone
                                )
                                : "—"
                        }

                    </td>



                    <!-- ROLE -->

                    <td>

                        <span
                            class="role-badge ${getRoleClass(
                                user.role
                            )}"
                        >

                            ${formatRole(
                                user.role
                            )}

                        </span>

                    </td>



                    <!-- STATUS -->

                    <td>

                        <span
                            class="status-badge ${getStatusClass(
                                user.status
                            )}"
                        >

                            ${formatStatus(
                                user.status
                            )}

                        </span>

                    </td>



                    <!-- CREATED -->

                    <td>

                        ${formatDate(
                            user.created_at
                        )}

                    </td>



                    <!-- ACTIONS -->

                    <td>

                        <div class="action-buttons">


                            <button
                                class="action-btn edit-btn"
                                onclick="openEditModal(
                                    ${user.user_id}
                                )"
                            >
                                Edit
                            </button>


                            <button
                                class="action-btn delete-btn"
                                onclick="deleteUser(
                                    ${user.user_id}
                                )"
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
   ROLE CLASS
   ========================================= */

function getRoleClass(role) {

    switch (role) {

        case "ADMIN":
            return "role-admin";

        case "DISASTER_MANAGER":
            return "role-manager";

        case "VOLUNTEER":
            return "role-volunteer";

        case "PUBLIC_USER":
            return "role-public";

        default:
            return "";

    }

}


/* =========================================
   FORMAT ROLE
   ========================================= */

function formatRole(role) {

    if (!role) {
        return "—";
    }


    switch (role) {

        case "ADMIN":
            return "Admin";

        case "DISASTER_MANAGER":
            return "Disaster Manager";

        case "VOLUNTEER":
            return "Volunteer";

        case "PUBLIC_USER":
            return "Public User";

        default:
            return role;

    }

}


/* =========================================
   STATUS CLASS
   ========================================= */

function getStatusClass(status) {

    switch (status) {

        case "ACTIVE":
            return "status-active";

        case "INACTIVE":
            return "status-inactive";

        case "SUSPENDED":
            return "status-suspended";

        default:
            return "";

    }

}


/* =========================================
   FORMAT STATUS
   ========================================= */

function formatStatus(status) {

    if (!status) {
        return "—";
    }


    return (
        status.charAt(0) +
        status
            .slice(1)
            .toLowerCase()
    );

}


/* =========================================
   FORMAT DATE
   ========================================= */

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

        return escapeHTML(
            value
        );

    }


    return date.toLocaleString(
        "en-IN",
        {
            day: "2-digit",
            month: "short",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit"
        }
    );

}


/* =========================================
   OPEN ADD MODAL
   ========================================= */

function openAddModal() {

    editingUserId = null;


    document.getElementById(
        "modal-title"
    ).textContent =
        "Add User";


    document.getElementById(
        "user-form"
    ).reset();


    document.getElementById(
        "user-id"
    ).value = "";


    document.getElementById(
        "role"
    ).value =
        "PUBLIC_USER";


    document.getElementById(
        "status"
    ).value =
        "ACTIVE";


    document.getElementById(
        "user-modal"
    ).classList.add("show");

}


/* =========================================
   OPEN EDIT MODAL
   ========================================= */

async function openEditModal(
    userId
) {

    try {

        const response =
            await fetch(
                `${USERS_API}/${userId}`
            );


        if (!response.ok) {

            throw new Error(
                "Failed to fetch user"
            );

        }


        const user =
            await response.json();


        editingUserId =
            userId;


        document.getElementById(
            "modal-title"
        ).textContent =
            "Edit User";


        document.getElementById(
            "user-id"
        ).value =
            user.user_id;


        document.getElementById(
            "full-name"
        ).value =
            user.full_name ?? "";


        document.getElementById(
            "email"
        ).value =
            user.email ?? "";


        /*
         * GET /users does not return
         * password_hash.
         *
         * Therefore it must be entered
         * again while editing.
         */

        document.getElementById(
            "password-hash"
        ).value = "";


        document.getElementById(
            "phone"
        ).value =
            user.phone ?? "";


        document.getElementById(
            "role"
        ).value =
            user.role ?? "PUBLIC_USER";


        document.getElementById(
            "status"
        ).value =
            user.status ?? "ACTIVE";


        document.getElementById(
            "user-modal"
        ).classList.add("show");


    } catch (error) {

        console.error(error);


        alert(
            "Failed to load user."
        );

    }

}


/* =========================================
   SAVE USER
   ========================================= */

async function saveUser(event) {

    event.preventDefault();


    const fullName =
        document.getElementById(
            "full-name"
        )
        .value
        .trim();


    const email =
        document.getElementById(
            "email"
        )
        .value
        .trim();


    const passwordHash =
        document.getElementById(
            "password-hash"
        )
        .value
        .trim();


    const phone =
        document.getElementById(
            "phone"
        )
        .value
        .trim();


    const role =
        document.getElementById(
            "role"
        ).value;


    const status =
        document.getElementById(
            "status"
        ).value;



    /* =====================================
       FRONTEND VALIDATION
       ===================================== */

    if (!fullName) {

        alert(
            "Please enter the full name."
        );

        return;

    }


    if (!email) {

        alert(
            "Please enter the email."
        );

        return;

    }


    if (!passwordHash) {

        alert(
            "Please enter the password hash."
        );

        return;

    }


    if (!role) {

        alert(
            "Please select a role."
        );

        return;

    }


    if (!status) {

        alert(
            "Please select a status."
        );

        return;

    }



    /* =====================================
       PAYLOAD
       ===================================== */

    const payload = {

        full_name:
            fullName,

        email:
            email,

        password_hash:
            passwordHash,

        phone:
            phone || null,

        role:
            role,

        status:
            status

    };



    try {

        let response;


        /* =================================
           CREATE
           ================================= */

        if (
            editingUserId === null
        ) {

            response =
                await fetch(
                    `${USERS_API}/`,
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body:
                            JSON.stringify(
                                payload
                            )
                    }
                );

        }


        /* =================================
           UPDATE
           ================================= */

        else {

            response =
                await fetch(
                    `${USERS_API}/${editingUserId}`,
                    {
                        method: "PUT",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body:
                            JSON.stringify(
                                payload
                            )
                    }
                );

        }


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Failed to save user"
            );

        }


        alert(
            editingUserId === null
                ? "User added successfully!"
                : "User updated successfully!"
        );


        closeModal();


        await loadUsers();


    } catch (error) {

        console.error(error);


        alert(
            error.message
        );

    }

}


/* =========================================
   DELETE USER
   ========================================= */

async function deleteUser(
    userId
) {

    const confirmed =
        confirm(
            `Are you sure you want to delete User #${userId}?`
        );


    if (!confirmed) {
        return;
    }


    try {

        const response =
            await fetch(
                `${USERS_API}/${userId}`,
                {
                    method: "DELETE"
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Failed to delete user"
            );

        }


        alert(
            "User deleted successfully!"
        );


        await loadUsers();


    } catch (error) {

        console.error(error);


        alert(
            error.message
        );

    }

}


/* =========================================
   CLOSE MODAL
   ========================================= */

function closeModal() {

    document.getElementById(
        "user-modal"
    ).classList.remove(
        "show"
    );


    editingUserId = null;

}


/* =========================================
   CLICK OUTSIDE MODAL
   ========================================= */

document.addEventListener(
    "click",
    event => {

        const modal =
            document.getElementById(
                "user-modal"
            );


        if (
            event.target === modal &&
            modal.classList.contains(
                "show"
            )
        ) {

            closeModal();

        }

    }
);


/* =========================================
   ESCAPE KEY
   ========================================= */

document.addEventListener(
    "keydown",
    event => {

        if (
            event.key === "Escape"
        ) {

            closeModal();

        }

    }
);