from unittest.mock import patch
import pytest
from app.main import app
from app.security import current_user
from conftest import ADMIN, PUBLIC

MODULES = [
    "disasters",
    "shelters",
    "volunteers",
    "resources",
    "locations",
    "users",
    "resource-allocations",
    "volunteer-assignments",
    "shelter-registrations",
    "emergency-reports",
]


@pytest.mark.parametrize("module", MODULES)
def test_global_search_all_modules_and_roles(client, db, module):
    assert client.get("/api/search/" + module).status_code == 401
    app.dependency_overrides[current_user] = lambda: PUBLIC
    db.execute.return_value.scalar_one.return_value = 0
    db.execute.return_value.mappings.return_value.all.return_value = []
    assert client.get("/api/search/" + module).status_code == (
        200 if module == "emergency-reports" else 403
    )
    app.dependency_overrides[current_user] = lambda: ADMIN
    response = client.get("/api/search/" + module + "?q=needle&limit=2&offset=3")
    assert response.status_code == 200, response.text
    assert module.replace("-", "_") in response.json()
    query, params = db.execute.call_args.args
    assert params["q"] == "%needle%" and params["limit"] == 2 and params["offset"] == 3
    assert "needle" not in str(query)


def test_manager_cannot_search_private_account_module(client, db):
    app.dependency_overrides[current_user] = lambda: {**ADMIN, "role": "DISASTER_MANAGER"}
    assert client.get("/api/search/users").status_code == 403
    db.execute.assert_not_called()


@pytest.mark.parametrize("command", ["create-admin", "reset-password"])
def test_account_cli_invalid_password_is_never_printed(command, capsys):
    from app.manage import main

    private = "short!"
    with (
        patch("sys.argv", ["manage", command, "--email", "owner@example.com"]),
        patch("app.manage.getpass.getpass", return_value=private),
        patch("app.manage.SessionLocal") as sessions,
    ):
        with pytest.raises(SystemExit) as error:
            main()
        assert "password" in str(error.value) and private not in str(error.value)
        sessions.assert_not_called()
    output = capsys.readouterr()
    assert private not in output.out + output.err
