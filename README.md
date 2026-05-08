# Quiniela Mundial 2026

Pool tracker for the 2026 FIFA World Cup — 48 teams, 12 groups, 104 matches.

## Requirements

- [Podman](https://podman.io/getting-started/installation)
- [podman-compose](https://github.com/containers/podman-compose#installation)

```bash
# Fedora/RHEL
sudo dnf install podman podman-compose

# Ubuntu/Debian
sudo apt install podman
pip install podman-compose

# macOS (Homebrew)
brew install podman podman-compose
podman machine init && podman machine start
```

## Local development

```bash
# Start all services (PostgreSQL + backend + frontend)
podman-compose up --build

# Seed teams and group-stage matches (run once)
podman-compose exec backend python seed_data.py

# Stop services
podman-compose down

# Wipe database volume
podman-compose down -v
```

| Service  | URL                          |
|----------|------------------------------|
| Frontend | http://localhost:3000        |
| API      | http://localhost:8000        |
| API docs | http://localhost:8000/docs   |

## Default admin account

After seeding, log in at `http://localhost:3000/register.html` with:

- **Email:** millan.ricardo@gmail.com  
- **Password:** admin123

Change the password immediately in production.

## Deployment

Configured for [Render.com](https://render.com) free tier via `render.yaml`.
