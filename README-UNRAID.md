# Frappe LMS on unRAID - Deployment Guide

This guide provides comprehensive instructions for deploying Frappe LMS on an unRAID server using Docker Compose. It covers prerequisites, quick setup, environment configuration, volume management, system access, import scripts, troubleshooting, backup, and updating procedures.

## Prerequisites
-   **Docker Compose Plugin**: Ensure the Docker Compose plugin is installed on your unRAID server. This is typically available via the Community Applications plugin.
-   **Storage Paths**:
    -   Persistent application data will be stored in: `/mnt/m2cache/appdata/frappe-lms/`
    -   Read-only video assets are expected at: `/mnt/user/mathmo-assets/` (ensure this path exists and contains your video files)

## Quick Start
Follow these 4-5 commands to get your Frappe LMS system running on unRAID:

1.  **Navigate to your Frappe LMS project directory**:
    ```bash
    cd /Users/petetreadaway/Projects/frappe-lms
    ```

2.  **Create your `.env` file from the example**:
    ```bash
    cp .env.unraid.example .env
    # IMPORTANT: Edit .env to change MYSQL_ROOT_PASSWORD and ADMIN_PASSWORD for security.
    ```

3.  **Build the Frappe LMS application image**:
    ```bash
    docker compose -f docker-compose.unraid.yml build
    ```

4.  **Start the Docker Compose stack**:
    ```bash
    docker compose -f docker-compose.unraid.yml up -d
    ```
    The first boot will take approximately 5 minutes to reach a healthy state. Subsequent boots are much faster (~90 seconds).

5.  **Verify container health**:
    ```bash
    docker compose -f docker-compose.unraid.yml ps
    ```
    All services (lms-db, lms-redis, lms-app) should show `healthy` status.

## Environment Variables
These variables are defined in your `.env` file and control the Frappe LMS deployment.

| Variable           | Default       | Description                                                              |
|--------------------|---------------|--------------------------------------------------------------------------|
| `MYSQL_ROOT_PASSWORD` | `frappe123`   | Root password for the MariaDB database. **Change this immediately.**     |
| `SITE_NAME`        | `lms.localhost` | The Frappe site name. Used for internal routing and configuration.       |
| `ADMIN_PASSWORD`   | `narlicwes0`  | Default password for the `Administrator` user in Frappe LMS. **Change this.** |
| `DB_HOST`          | `lms-db`      | Internal hostname for the MariaDB service within the Docker network.     |
| `REDIS_CACHE`      | `lms-redis:6379:0` | Redis connection string for caching.                                     |
| `REDIS_QUEUE`      | `lms-redis:6379:1` | Redis connection string for background jobs/queues.                      |
| `REDIS_SOCKETIO`   | `lms-redis:6379:2` | Redis connection string for Socket.IO real-time communication.           |

## Volume Management
Persistent data for Frappe LMS is stored on your unRAID array to ensure data survives container recreation.

| Host Path                               | Container Path                 | Purpose                                     |
|-----------------------------------------|--------------------------------|---------------------------------------------|
| `/mnt/m2cache/appdata/frappe-lms/db`    | `/var/lib/mysql`               | Stores all MariaDB database files.          |
| `/mnt/m2cache/appdata/frappe-lms/redis` | `/data`                        | Stores Redis AOF persistence data.          |
| `/mnt/m2cache/appdata/frappe-lms/sites` | `/home/frappe/frappe-bench/sites` | Stores Frappe site configurations, files, and uploads. |
| `/mnt/m2cache/appdata/frappe-lms/logs`  | `/home/frappe/frappe-bench/logs`  | Stores Frappe application logs.             |
| `/mnt/user/mathmo-assets`               | `/app/videos` (read-only)      | Mount point for external video assets.      |

## Deployment Checklist

### Pre-Deployment
Before starting the deployment, ensure you have completed these steps:

- [ ] Docker Compose Plugin installed on unRAID
- [ ] Directory `/mnt/user/mathmo-assets/` exists and contains video files
- [ ] Sufficient storage space in `/mnt/m2cache/appdata/` (minimum 10GB recommended)
- [ ] `.env` file created from `.env.unraid.example`
- [ ] `MYSQL_ROOT_PASSWORD` changed in `.env` (security)
- [ ] `ADMIN_PASSWORD` changed in `.env` if desired (default: `narlicwes0`)
- [ ] Ports 9000 and 9001 available on unRAID host (not used by other services)

### Post-Deployment Verification
After running `docker compose up -d`, verify the deployment:

- [ ] All containers running: `docker compose -f docker-compose.unraid.yml ps`
- [ ] MariaDB healthy: `docker inspect lms-db --format='{{.State.Health.Status}}'` returns `healthy`
- [ ] Redis healthy: `docker inspect lms-redis --format='{{.State.Health.Status}}'` returns `healthy`
- [ ] Frappe app healthy: `docker inspect lms-app --format='{{.State.Health.Status}}'` returns `healthy` (wait up to 5 minutes)
- [ ] Web interface accessible: Open `http://<unraid-ip>:9001` in browser
- [ ] Login works: Use credentials `Administrator` / `<your-admin-password>`
- [ ] LMS homepage loads: Navigate to `http://<unraid-ip>:9001/lms`
- [ ] Video mount visible: `docker exec lms-app ls /app/videos` shows video files
- [ ] Video symlinks created: `docker exec lms-app ls -la sites/lms.localhost/public/files/` shows symlinks to `/app/videos/`

## Accessing the System
-   **Web Interface**: Access Frappe LMS via your unRAID server's IP address or hostname on port `9001`.
    -   URL Example: `http://your-unraid-ip:9001`
-   **Socket.IO**: Used for real-time updates, exposed on port `9000`.
-   **Default Credentials**:
    -   Username: `Administrator`
    -   Password: `narlicwes0` (as defined in `.env.unraid.example`, **change this in your `.env` file and after first login**)

## Running Import Scripts

Frappe LMS includes custom import scripts to populate courses from JSON data sources. The primary import script is `lms.scripts.import_gcse_course.run_import`.

### Import Course Data

To run the GCSE course import script:

```bash
docker exec lms-app bench --site lms.localhost execute lms.scripts.import_gcse_course.run_import
```

**Expected Behavior:**
- Script reads from `/Users/petetreadaway/Projects/frappe-lms/templates/combined_modules_withLocalURL.json` (inside container)
- Creates Course → Chapter → Lesson hierarchy in Frappe LMS
- Embeds video content from `/app/videos` mount
- Outputs progress to console

**Verification:**
After import completes, verify courses are visible:
1. Login to LMS: `http://<unraid-ip>:9001/lms`
2. Navigate to Courses list
3. Check that imported courses appear with chapters and lessons

### Import Script Location
The import script source is at:
```
/home/frappe/frappe-bench/apps/lms/lms/scripts/import_gcse_course.py
```

### Troubleshooting Import Issues
- **Import fails with file not found**: Ensure video mount `/app/videos` contains expected files
- **Import fails with database error**: Check `lms-app` logs: `docker logs lms-app`
- **Courses don't appear**: Run `bench --site lms.localhost migrate` then retry

## Running Import Scripts (Alternative Methods)
To import courses (e.g., using `import_gcse_course.py`), you can execute commands directly within the `lms-app` container.

1.  **Access the Frappe bench directory inside the container**:
    ```bash
    docker exec -it lms-app bash
    ```

2.  **Execute the import script**:
    ```bash
    bench --site lms.localhost execute lms.scripts.import_gcse_course.run_import
    ```
    (Replace `lms.scripts.import_gcse_course.run_import` with the actual path to your import function).

3.  **Exit the container shell**:
    ```bash
    exit
    ```

## Troubleshooting
### Container Won't Start
-   **Check Logs**: The first step is always to check the container logs for errors.
    ```bash
    docker compose -f docker-compose.unraid.yml logs lms-app
    docker compose -f docker-compose.unraid.yml logs lms-db
    docker compose -f docker-compose.unraid.yml logs lms-redis
    ```
-   **Common Issues**: Port conflicts, incorrect volume paths, or syntax errors in `docker-compose.unraid.yml` or `.env`.

### Database Connection Failed
-   **Verify MariaDB Health**: Ensure `lms-db` container is healthy.
    ```bash
    docker compose -f docker-compose.unraid.yml ps
    ```
    If not healthy, check `lms-db` logs.
-   **Check `MYSQL_ROOT_PASSWORD`**: Ensure the password in `.env` matches what MariaDB expects.

### Redis Timeout
-   **Verify Redis Health**: Ensure `lms-redis` container is healthy.
    ```bash
    docker compose -f docker-compose.unraid.yml ps
    ```
    If not healthy, check `lms-redis` logs.

### Video Mount Not Visible
-   **Permissions/Path Issues**: Ensure `/mnt/user/mathmo-assets` exists on your unRAID host and the `lms-app` container has read permissions. Double-check the path in `docker-compose.unraid.yml`.

### Health Check Failing
-   **Frappe App Health**: The `lms-app` health check (`frappe.ping`) relies on the Frappe application being fully started and responsive. If `lms-db` and `lms-redis` are healthy, give `lms-app` more time (first boot can be ~5 minutes). Check `lms-app` logs for Frappe-specific errors.

## Backup/Restore
For unRAID, the recommended backup approach is to regularly back up your persistent data volumes.
-   **Backup**: Copy the entire `/mnt/m2cache/appdata/frappe-lms/` directory to a safe location on your unRAID array or an external backup target. This directory contains all your database, Redis, and Frappe site data.
-   **Restore**: In case of data loss, stop the Frappe LMS stack, restore the `/mnt/m2cache/appdata/frappe-lms/` directory from your backup, and then restart the stack.

## Updating
To update Frappe LMS (e.g., after pulling new code or a new Dockerfile.unraid):

1.  **Navigate to your Frappe LMS project directory**:
    ```bash
    cd /Users/petetreadaway/Projects/frappe-lms
    ```

2.  **Pull the latest code (if applicable)**:
    ```bash
    git pull origin main # Or your relevant branch
    ```

3.  **Rebuild the `lms-app` image**:
    ```bash
    docker compose -f docker-compose.unraid.yml build lms-app
    ```

4.  **Restart the stack to apply updates**:
    ```bash
    docker compose -f docker-compose.unraid.yml up -d
    ```
    This will recreate the `lms-app` container with the new image while preserving your persistent data volumes.
