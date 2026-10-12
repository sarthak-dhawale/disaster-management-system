# Primary laptop: existing Docker MySQL 8.4

Preserve container `disaster-mysql`, its current MySQL data mount (the supplied setup names it `disaster_mysql_data`) and every record in `disaster_management`. V3 does not modify docker-compose.yml or run Docker commands on the development machine.

Start Docker Desktop. Open PowerShell at the ORIGINAL existing project root:

```powershell
Set-Location E:\CS\sarthak-disaster-management-system
docker ps -a --filter name=disaster-mysql
docker inspect disaster-mysql --format '{{json .Mounts}}'
docker inspect disaster-mysql --format '{{index .Config.Labels "com.docker.compose.project"}}'
```

Check the existing mount's actual volume name. Compose normally prefixes named volumes with the project name; do not assume the YAML key is the physical volume name. Keep the same Compose project name/root and existing root `.env`. Do not rename or replace the container/volume. When the existing container is present, the safest startup is:

```powershell
docker start disaster-mysql
```

To use the existing Compose project after confirming the mount and project identity, from that original root:

```powershell
docker compose up -d
docker ps
docker logs disaster-mysql
docker inspect disaster-mysql --format '{{.State.Health.Status}}'
docker exec -it disaster-mysql mysqladmin -u root -p ping
```

The last command prompts for the existing root password. MySQL must be ready, not merely have a running container. The Compose health probe checks MySQL responsiveness. Verify the correct database with your account:

```powershell
docker exec -it disaster-mysql mysql -u disaster_user -p disaster_management -e "SELECT DATABASE(), VERSION(); SHOW TABLES;"
```

Replace disaster_user if the existing account differs. Root `.env` MYSQL_DATABASE defaults to disaster_management; API `backend\.env` DB_NAME must match it. API DB_HOST is 127.0.0.1 when running directly on Windows. If the API is containerized later, use the Compose SERVICE hostname `mysql`, not localhost.

Port check:

```powershell
Get-NetTCPConnection -LocalPort 3306 -ErrorAction SilentlyContinue
```

If another database already owns 3306, identify which setup you are using. Do not stop unrelated services or containers. This application expects only the selected MySQL instance. Logs may indicate startup, permissions, disk space or recovery failures.

Changing MYSQL_PASSWORD in `.env` does not change an account password inside an already initialized volume. Keep existing credentials consistent; use a deliberate MySQL account-management procedure for rotation. Never paste passwords in logs or documentation.

Safe stop:

```powershell
docker stop disaster-mysql
```

`docker compose stop` is also safe from the original project. **Removing the persistent Docker volume can permanently delete all database data. Do not use `docker compose down -v`, `docker volume rm`, prune commands or legacy reset SQL.** Extracting V3 into a differently named directory must not be used to launch a second Compose project against new storage; follow TRANSFER_TO_PRIMARY.md.
