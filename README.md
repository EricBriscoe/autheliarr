# Autheliarr

Simple Docker application to sync Wizarr users to Authelia.

## Docker Compose Setup

Add to your existing Docker Compose stack:

```yaml
services:
  autheliarr:
    image: ghcr.io/ericbriscoe/autheliarr:latest
    container_name: autheliarr
    restart: unless-stopped
    environment:
      - SYNC_INTERVAL=3600  # Sync every hour
      - DRY_RUN=false
    volumes:
      - /path/to/wizarr/database.db:/wizarr/database.db:ro
      - /path/to/authelia/users_database.yml:/authelia/users_database.yml:rw
    # user: "1000:1000"  # Remove if you get permission errors
```

## Environment Variables

- `SYNC_INTERVAL`: Seconds between syncs (0 = run once and exit, >0 = periodic)
- `DRY_RUN`: Set to `true` to preview changes without applying
- `SECURE_LOG_PATH`: Path for secure password logging (optional)

## What It Does

1. Reads users from Wizarr SQLite database
2. Creates missing Authelia accounts with generated passwords
3. Syncs email addresses between systems
4. Logs obfuscated passwords to container logs

Generated passwords are always obfuscated in main logs. Configure `SECURE_LOG_PATH` to access full passwords.

## Troubleshooting

**Permission denied errors?**

Remove the `user:` line from your Docker Compose to run as root:

```yaml
# user: "1000:1000"  # Comment out or remove this line
```

This is safe because Authelia typically runs as root and owns its config files. The container only reads one database and writes to one config file.
