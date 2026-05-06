# Deploy

How `tenjin.us` gets to production. Single OCI A1.Flex VM (ARM, 2 cores / 12 GB), Cloudflare Tunnel for ingress, a self-hosted GitHub Actions runner on the box for delivery. No inbound ports are opened.

## Architecture

```
GitHub (push to main)
   │
   ▼  self-hosted runner on OCI box pulls the job over outbound HTTPS
   │
   ▼  runner runs `docker compose up -d --build` in /opt/tenjin
   │
   OCI VM (129.153.206.53)
   ├─ Docker: web container, bound 127.0.0.1:3000
   └─ cloudflared (host service): tunnel → CF edge
                                       │
                                       ▼
                              tenjin.us (DNS managed by CF)
```

`api.tenjin.us` lights up the same way once the FastAPI service is wired into the compose stack.

## Safety posture

- **Workflow triggers on `push` to `main` only.** Forked PRs cannot run it; they can only propose changes.
- **Review every PR diff before merging.** Especially anything under `.github/workflows/`. A malicious workflow change running on the self-hosted runner means arbitrary code on the production box.
- **Don't enable auto-merge.** The merge step is the safety gate.
- Optional but recommended: protect `main` (Settings → Branches → require PR review), and add a `CODEOWNERS` entry for `.github/workflows/`.

## One-time setup

### 1. Cloudflare Tunnel — Public Hostname

In the CF Zero Trust dashboard → **Networks** → **Tunnels** → click your tunnel → **Public Hostnames** → **Add a public hostname**:

| Field | Value |
| --- | --- |
| Subdomain | *(leave blank)* |
| Domain | `tenjin.us` |
| Type | `HTTP` |
| URL | `localhost:3000` |

CF creates the DNS CNAME automatically. Keep the orange cloud (proxied).

### 2. Install Docker on the OCI box

SSH in once and run:

```bash
sudo apt update
sudo apt install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"
```

Log out and back in so the `docker` group takes effect. Verify: `docker run --rm hello-world`.

### 3. Clone the repo to /opt/tenjin

```bash
sudo mkdir -p /opt/tenjin
sudo chown "$USER":"$USER" /opt/tenjin
git clone https://github.com/aztenjin81/tenjin_news_scraper /opt/tenjin
cd /opt/tenjin
git checkout main
```

### 4. Install the GitHub Actions self-hosted runner

In the GitHub repo → **Settings** → **Actions** → **Runners** → **New self-hosted runner**:

- **Runner image:** Linux
- **Architecture:** ARM64

GitHub will show three blocks of commands. Run them on the box, **but** when prompted:

- **Name of runner:** `oci-tenjin` (or anything memorable)
- **Labels (additional, comma-separated):** `oci`  ← important; the workflow targets `[self-hosted, oci]`
- **Work folder:** accept the default (`_work`)

After the configure step finishes, install the runner as a systemd service so it survives reboots:

```bash
cd ~/actions-runner   # or wherever you extracted it
sudo ./svc.sh install "$USER"
sudo ./svc.sh start
sudo ./svc.sh status
```

Back in the GitHub UI, the runner should now show **Idle** in the Runners list.

### 5. Per-deploy environment

If you ever need to set `NEXT_PUBLIC_API_BASE_URL` (e.g. once the FastAPI service is live at `api.tenjin.us`), put it in `/opt/tenjin/.env` on the box. `docker compose` reads it automatically. Don't commit this file.

## First deploy

```bash
# from your laptop
git checkout main
git push   # any change to apps/web/** triggers the workflow
```

Or run it manually: GitHub → **Actions** → **Deploy web** → **Run workflow** → choose `main`.

Watch the run; on success, the workflow's "Wait for health" step has already confirmed the container responds on `127.0.0.1:3000`. Hit `https://tenjin.us` — it should serve the home page.

## Updating

Every push to `main` that touches `apps/web/**`, `infra/docker-compose.prod.yml`, or the workflow itself rebuilds and rolls forward. Old containers are replaced via `docker compose up -d`. Old images are pruned after each deploy.

## Rolling back

Each deploy builds locally — there are no historical image tags. To roll back, revert the commit on `main` and let the workflow redeploy:

```bash
git revert <bad-sha>
git push
```

Or, on the box:

```bash
ssh <user>@129.153.206.53
cd /opt/tenjin
git checkout <good-sha>
docker compose -f infra/docker-compose.prod.yml up -d --build
```

## Troubleshooting

- **Workflow stuck "Waiting for runner"** → the self-hosted runner isn't running on the box. SSH in: `cd ~/actions-runner && sudo ./svc.sh status`.
- **`tenjin.us` shows 502 / "Tunnel error"** → the web container isn't running. SSH in: `cd /opt/tenjin && docker compose -f infra/docker-compose.prod.yml ps`. If unhealthy, `docker compose logs web`.
- **Build fails on `pnpm install`** → likely the lockfile drifted from `package.json`. Run `pnpm install` locally and commit the updated `pnpm-lock.yaml`.
- **Out of disk space on the box** → `docker system prune -af --volumes`. The builder cache is the main consumer.
- **Want to peek at the running site without DNS** → on the box, `curl -sI http://127.0.0.1:3000/`.
