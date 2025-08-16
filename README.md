# Autheliarr

**Simple Docker application to sync Wizarr users to Authelia**

Autheliarr automatically ensures that every user who signs up through Wizarr gets a corresponding account in Authelia, enabling seamless SSO integration for your media stack.

## Features

- ✅ **Automatic User Sync** - Creates Authelia accounts for all Wizarr users
- ✅ **Email Synchronization** - Keeps email addresses in sync between systems
- ✅ **Secure Password Generation** - Generates strong random passwords for new users
- ✅ **Docker Ready** - Easy deployment with Docker Compose
- ✅ **Dry Run Mode** - Test changes before applying them
- ✅ **Minimal Dependencies** - Lightweight Python application

## Quick Start

### Docker Run (Recommended)

```bash
docker run --rm \
  -v /path/to/wizarr/database.db:/wizarr/database.db:ro \
  -v /path/to/authelia/users_database.yml:/authelia/users_database.yml:rw \
  -e DRY_RUN=false \
  ghcr.io/ericbriscoe/autheliarr:latest
```

### Test First (Dry Run)

```bash
docker run --rm \
  -v /path/to/wizarr/database.db:/wizarr/database.db:ro \
  -v /path/to/authelia/users_database.yml:/authelia/users_database.yml:ro \
  -e DRY_RUN=true \
  ghcr.io/ericbriscoe/autheliarr:latest
```

## Configuration

Configure via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `WIZARR_DB_PATH` | `/wizarr/database.db` | Path to Wizarr SQLite database |
| `AUTHELIA_USERS_PATH` | `/authelia/users_database.yml` | Path to Authelia users file |
| `DEFAULT_GROUP` | `plex_users` | Default group for new Authelia users |
| `DRY_RUN` | `false` | Set to `true` to preview changes without applying |
| `SECURE_LOG_PATH` | `/app/secure.log` | Path for secure password logging (optional) |

## Integration Options

### Option 1: Docker Compose Integration

Add to your existing Docker Compose stack:

```yaml
services:
  autheliarr:
    image: ghcr.io/ericbriscoe/autheliarr:latest
    container_name: autheliarr
    restart: "no"  # Run once and exit
    environment:
      - WIZARR_DB_PATH=/wizarr/database.db
      - AUTHELIA_USERS_PATH=/authelia/users_database.yml
      - DEFAULT_GROUP=plex_users
      - DRY_RUN=false
    volumes:
      # Adjust paths to match your setup
      - /your/wizarr/path/database.db:/wizarr/database.db:ro
      - /your/authelia/path/users_database.yml:/authelia/users_database.yml:rw
    user: "1000:1000"  # Adjust to match your user/group
```

### Option 2: Scheduled Execution

Add to crontab for automatic syncing:

```bash
# Run every hour
0 * * * * docker run --rm -v /your/wizarr/database.db:/wizarr/database.db:ro -v /your/authelia/users_database.yml:/authelia/users_database.yml:rw ghcr.io/ericbriscoe/autheliarr:latest
```

### Option 3: Manual Execution

Run when needed:

```bash
docker run --rm \
  -v /your/wizarr/database.db:/wizarr/database.db:ro \
  -v /your/authelia/users_database.yml:/authelia/users_database.yml:rw \
  -e DRY_RUN=false \
  ghcr.io/ericbriscoe/autheliarr:latest
```

## How It Works

1. **Reads Wizarr Database** - Extracts users and emails from Wizarr's SQLite database
2. **Loads Authelia Users** - Parses existing Authelia users YAML file
3. **Compares & Syncs** - Creates missing Authelia accounts with:
   - Username from Wizarr
   - Email from Wizarr
   - Auto-generated secure password
   - Default group membership (`plex_users`)
4. **Updates Configuration** - Saves updated users to Authelia's config file
5. **Logs Changes** - Reports new/updated users with generated passwords

## Security Notes

- **Password Logging** - Passwords are ALWAYS obfuscated in main logs (e.g., `ab****ef`)
- **Secure Logging** - Full passwords ONLY written to secure log file if configured
- **No Fallbacks** - Without secure log, full passwords are NOT logged anywhere
- **File permissions** - Ensure proper permissions on mounted volumes
- **Backup configs** - Always backup Authelia configuration before running
- **Dry run first** - Use `DRY_RUN=true` to preview changes

### Password Security

Generated passwords are **always obfuscated** in container logs. To access full passwords, you **must** configure secure logging:

**Required for Password Access:**
```bash
docker run --rm \
  -v /secure/path/autheliarr.log:/app/secure.log \
  -e SECURE_LOG_PATH=/app/secure.log \
  ghcr.io/ericbriscoe/autheliarr:latest
```

**Without secure log configured:** Full passwords are NOT logged anywhere and must be manually generated/provided to users.

## Troubleshooting

### Common Issues

**"Database not found"**
```bash
# Verify Wizarr database path
ls -la /your/wizarr/path/database.db
```

**"Permission denied"**
```bash
# Fix file permissions (adjust user:group as needed)
chown 1000:1000 /your/authelia/path/users_database.yml
chmod 644 /your/authelia/path/users_database.yml
```

**"No users found"**
```bash
# Check Wizarr database
sqlite3 /your/wizarr/path/database.db "SELECT username, email FROM user;"
```

### Logs

View application logs:
```bash
docker logs autheliarr
```

Enable debug logging:
```bash
docker run -e LOG_LEVEL=DEBUG ...
```

## Building from Source

```bash
git clone https://github.com/EricBriscoe/autheliarr.git
cd autheliarr
docker build -t autheliarr .
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

- 🐛 **Issues**: [GitHub Issues](https://github.com/EricBriscoe/autheliarr/issues)
- 📖 **Documentation**: This README
- 💬 **Discussions**: [GitHub Discussions](https://github.com/EricBriscoe/autheliarr/discussions)