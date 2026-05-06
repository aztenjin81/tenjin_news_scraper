# Deploy

How `tenjin.us` gets to production. Single OCI A1.Flex VM (ARM, Ubuntu/Oracle Linux), Cloudflare Tunnel for ingress, GitHub Actions for delivery. No inbound ports are opened on the box.

## Architecture

```
GitHub (push to main)
   │
   ▼  GHA: build linux/arm64 → ghcr.io/aztenjin81/tenjin-web:<sha>
   │
   ▼  GHA: scp + ssh → docker compose pull && up -d
   │
   OCI VM (129.153.206.53)
   ├─ docker compose: web container, bound 127.0.0.1:3000
   └─ cloudflared (host service): tunnel → CF edge
                                       │
                                       ▼
                              tenjin.us (DNS managed by CF)
```

`api.tenjin.us` lights up the same way once the FastAPI service is wired into the compose stack.

## One-time setup

### 1. Cloudflare Tunnel (public hostname)

In the CF Zero Trust dashboard → **Networks** → **Tunnels** → click your tunnel → **Public Hostnames** → **Add a public hostname**:

| Field | Value |
| --- | --- |
| Subdomain | *(leave blank)* |
| Domain | `tenjin.us` |
| Type | `HTTP` |
| URL | `localhost:3000` |

CF will create the DNS CNAME automatically. Keep the orange cloud (proxied).

> The tunnel daemon is already running on the box (connector ID visible in the dashboard). It reaches into the host's `127.0.0.1:3000` — which is where `docker compose` will publish the web container.

### 2. Install Docker on the OCI box

SSH in once and run:

```bash
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"
sudo mkdir -p /opt/tenjin && sudo chown "$USER":"$USER" /opt/tenjin
```

Log out and back in so the `docker` group takes effect.

### 3. SSH key for GitHub Actions

On your laptop:

```bash
ssh-keygen -t ed25519 -C "tenjin-deploy" -f ~/.ssh/tenjin_deploy -N ""
ssh-copy-id -i ~/.ssh/tenjin_deploy.pub <user>@129.153.206.53
```

Verify: `ssh -i ~/.ssh/tenjin_deploy <user>@129.153.206.53 'docker --version'`.

### 4. GitHub repo secrets

Repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:

| Name | Value |
| --- | --- |
| `OCI_HOST` | `129.153.206.53` |
| `OCI_USER` | the SSH user on the box (e.g. `ubuntu` or `opc`) |
| `OCI_SSH_KEY` | contents of `~/.ssh/tenjin_deploy` (the **private** key) |

`GITHUB_TOKEN` is automatic — no need to add it.

### 5. GHCR package visibility (one-time)

After the first successful build, go to your GitHub profile → **Packages** → `tenjin-web` → **Package settings** → set visibility to **Public** (so the box can pull without auth) — *or* leave it private and rely on the workflow's `docker login ghcr.io` step (already wired in).

## First deploy

```bash
# from your laptop
git checkout main
git push                # any change to apps/web/** triggers the workflow
```

Or run it manually: GitHub → Actions → **Deploy web to OCI** → **Run workflow**.

Watch the run; on success, hit `https://tenjin.us` — it should serve the home page.

## Updating

Every push to `main` that touches `apps/web/**`, `infra/docker-compose.prod.yml`, or the workflow itself rebuilds and rolls forward. Old containers are replaced via `docker compose up -d`. Old images are pruned on the box after each deploy.

## Rolling back

The image is tagged with the short commit SHA. To pin to a previous version:

```bash
ssh <user>@129.153.206.53
cd /opt/tenjin
TENJIN_WEB_TAG=<short-sha> docker compose -f docker-compose.prod.yml up -d
```

Or revert the commit on `main` and let the workflow redeploy the prior state.

## Troubleshooting

- **`tenjin.us` shows 502 / "Tunnel error"** → the web container isn't running. SSH in: `cd /opt/tenjin && docker compose -f docker-compose.prod.yml ps`. If unhealthy, check `docker compose logs web`.
- **GHA build fails on `pnpm install`** → likely the lockfile drifted from `package.json`. Rerun `pnpm install` locally and commit the updated `pnpm-lock.yaml`.
- **`docker login ghcr.io` fails inside the SSH step** → the `GITHUB_TOKEN` from the workflow doesn't have package read on a private package. Either make the package public (step 5 above) or grant the token `read:packages`.
- **Want to peek at the running site without DNS** → on the box, `curl -sI http://127.0.0.1:3000/`.
