# Build Process for Frappe LMS

## Project Structure

This project has **two separate directories**:

1. **Source Code**: `/Users/petetreadaway/Projects/frappe-lms` - Development repository
2. **Bench Environment**: `/Users/petetreadaway/Projects/lms-bench` - Frappe Bench with running app

> [!IMPORTANT]
> The bench at `lms-bench/apps/lms` is a **separate copy**, NOT a symlink to frappe-lms. Changes made in frappe-lms will NOT automatically appear in the running application.

## After Making Changes

### Frontend Changes (Vue/JavaScript)

When modifying files in `frontend/src/`:

1. **Copy changed files to bench**:
   ```bash
   cp /Users/petetreadaway/Projects/frappe-lms/frontend/src/components/YourFile.vue \
      /Users/petetreadaway/Projects/lms-bench/apps/lms/frontend/src/components/YourFile.vue
   ```

2. **Rebuild the frontend**:
   ```bash
   cd /Users/petetreadaway/Projects/lms-bench
   source env/bin/activate
   bench build --app lms
   ```

3. **Hard refresh browser** (Cmd+Shift+R) to clear cached JavaScript

### Backend Changes (Python)

When modifying Python files in `lms/`:

1. **Copy changed files to bench**:
   ```bash
   cp /Users/petetreadaway/Projects/frappe-lms/lms/lms/your_file.py \
      /Users/petetreadaway/Projects/lms-bench/apps/lms/lms/lms/your_file.py
   ```

2. **Restart the bench** (if needed for new API endpoints):
   ```bash
   cd /Users/petetreadaway/Projects/lms-bench
   bench restart
   ```

### Both Frontend and Backend

If changing both:
```bash
# Copy files
cp frappe-lms/lms/lms/your_file.py lms-bench/apps/lms/lms/lms/your_file.py
cp frappe-lms/frontend/src/components/YourComponent.vue lms-bench/apps/lms/frontend/src/components/YourComponent.vue

# Build and restart
cd /Users/petetreadaway/Projects/lms-bench
source env/bin/activate
bench build --app lms
bench restart
```

## Quick Reference Commands

| Action | Command |
|--------|---------|
| Build frontend only | `bench build --app lms` |
| Restart bench | `bench restart` |
| Clear cache | `bench --site lms.localhost clear-cache` |
| Migrate database | `bench --site lms.localhost migrate` |

## Common Issues

### Changes Not Appearing
- Ensure files were copied to `lms-bench/apps/lms/`, not just modified in `frappe-lms/`
- Run `bench build --app lms` for frontend changes
- Hard refresh browser (Cmd+Shift+R) to bypass cache

### Build Fails with "command not found"
- Activate the bench environment first: `source env/bin/activate`
- Run commands from the bench directory: `cd /Users/petetreadaway/Projects/lms-bench`

### API Endpoint Not Found (417/404)
- Ensure Python file was copied to correct path
- New API endpoints may require `bench restart`
