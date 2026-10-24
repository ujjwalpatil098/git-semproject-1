# WattWise: Deployment & Operations Guide

This guide provides instructions for deploying and operating **WattWise: Electricity Consumption Analysis & Environmental Intelligence** in production environments.

---

## 1. Architecture & Security Overview

### Security Model
* **Authentication Engine**: PBKDF2-HMAC-SHA256 with 600,000 iterations and unique 16-byte cryptographic salts (`modules/auth.py`). Constant-time digest verification (`secrets.compare_digest`) prevents timing attacks.
* **Role-Based Access Control (RBAC)**:
  * **Admin**: Access to all analytical features, full Admin Console, user management, account activation/deactivation, role modification, and global savings intervention records.
  * **User**: Access to all analytical features and personal savings interventions. Restricted from viewing, modifying, or deleting other users' interventions. Strictly blocked from administrative endpoints.
* **Database Isolation**: SQLite persistence (`electricity.db`) with parameterized queries, schema integrity constraints, and query-level security blocking credential table dumps via SQL Analytics.
* **Session Isolation**: Uploaded custom datasets exist only in ephemeral session memory (`st.session_state`), ensuring strict privacy between concurrent users.

---

## 2. Administrator Provisioning

WattWise supports two secure provisioning pathways:

### Method A: Web Portal First-Time Setup (Zero-Configuration)
1. Launch the application with an uninitialized or fresh database.
2. The authentication gateway automatically detects that zero administrators exist and displays the **👑 Master Admin Setup** tab.
3. Choose an administrator username and a strong password (minimum 8 characters, letters & numbers).
4. Upon submission, the master administrator is created and future self-provisioning is automatically locked.

### Method B: Offline CLI Provisioning Tool (`manage_users.py`)
Run the administrative CLI directly from the terminal or container shell:

```bash
# Provision an initial or additional administrator
python manage_users.py create-admin --username sysadmin --password "SecurePass2026!"

# List all registered accounts with status and roles
python manage_users.py list-users

# Create a regular user
python manage_users.py create-user --username analyst1 --password "AnalystPass123"

# Deactivate an account
python manage_users.py set-status --id 2 --inactive

# Reactivate an account
python manage_users.py set-status --id 2 --active

# Promote a user to administrator
python manage_users.py set-role --id 2 --role admin

# Reset a user's password
python manage_users.py reset-password --id 2 --password "NewSecurePass2026!"
```

---

## 3. Large Dataset Handling for GitHub & Version Control

The default cleaned dataset `cleaned_electricity_data.csv` is approximately **130 MB**, and `electricity.db` is approximately **140 MB**. 

> [!WARNING]
> GitHub enforces a strict **100 MB single-file limit** on regular Git pushes. Pushing files larger than 100 MB without Git LFS will cause Git to reject the commit.

### Solution 1: Use Git Large File Storage (Git LFS) — Recommended
```bash
# Install Git LFS
git lfs install

# Track large data and database files
git lfs track "*.csv"
git lfs track "*.db"

# Commit attributes and code
git add .gitattributes
git add .
git commit -m "Deploy WattWise with Git LFS data tracking"
git push origin main
```

### Solution 2: Download Dataset at Container Startup (Headless/Cloud Run)
If deploying to platforms with strict image size limits, exclude `cleaned_electricity_data.csv` from Git and download it at startup from AWS S3, Google Cloud Storage, or a GitHub Release asset.

---

## 4. Deployment Pathways

### Pathway A: Streamlit Community Cloud (Fastest Free Option)
1. Push the repository to GitHub (ensuring Git LFS is configured for files > 100 MB).
2. Visit [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Click **New app**.
4. Select the repository, branch (`main`), and set the main file path to:
   ```
   dashboard.py
   ```
5. Click **Deploy!**. Streamlit Cloud automatically detects `requirements.txt` and `.streamlit/config.toml`.
6. Navigate to your live URL. You will be greeted by the **WattWise Security Protocol** gateway to configure your master administrator.

---

### Pathway B: Docker Container Deployment

#### 1. Build the Docker Image
```bash
docker build -t wattwise:latest .
```

#### 2. Run Locally or on a Virtual Private Server (VPS)
```bash
docker run -d \
  --name wattwise-app \
  -p 8501:8501 \
  -v $(pwd)/electricity.db:/app/electricity.db \
  wattwise:latest
```
*Notice: Mounting `/app/electricity.db` ensures user accounts and saving intervention records persist even if the container is rebuilt or restarted.*

#### 3. Test Container Health
```bash
curl http://localhost:8501/_stcore/health
```

---

### Pathway C: Render / Railway / Cloud PaaS
1. Connect your GitHub repository to Render or Railway.
2. Select **Docker** or **Python** environment.
3. Set Start Command:
   ```bash
   streamlit run dashboard.py --server.port=$PORT --server.address=0.0.0.0
   ```
4. Attach a **Persistent Disk** (volume) mounted at `/app` or `/data` to preserve `electricity.db`.

---

## 5. Security & Production Checklist

- [x] **Enforce HTTPS**: Cloud deployment platforms (Streamlit Community Cloud, Render, Cloud Run, AWS ALB) terminate SSL/TLS at the load balancer, ensuring all password transmissions are encrypted in transit.
- [x] **No Plaintext Passwords**: Passwords are never stored in plaintext or logged to stdout.
- [x] **OWASP Compliance**: PBKDF2-HMAC-SHA256 with 600,000 iterations and 16-byte random salt per user.
- [x] **Credential Dump Protection**: Read-only SQL query runner explicitly blocks queries attempting to access `users` or `password_hash`.
- [x] **Session State Hygiene**: User session information is stored in server-side session memory and cleared on logout.
- [x] **Admin Safeguards**: System enforces that the last active administrator cannot demote or deactivate themselves.
