# SEVABOT Migration Guide - Complete Documentation

Comprehensive guide for migrating SEVABOT application in various scenarios: credentials, databases, infrastructure, users, regions, and more.

---

## Table of Contents

1. [Overview](#overview)
2. [Pre-Migration Planning](#pre-migration-planning)
3. [Data Migration](#data-migration)
4. [Credential Migration](#credential-migration)
5. [Infrastructure Migration](#infrastructure-migration)
6. [User Migration](#user-migration)
7. [Post-Migration Validation](#post-migration-validation)
8. [Rollback Procedures](#rollback-procedures)
9. [Common Issues & Solutions](#common-issues--solutions)

---

## Overview

This guide covers all types of migrations:

| Migration Type | Scenario | Difficulty | Downtime | Time |
|---|---|---|---|---|
| **Credentials** | OAuth/AWS/Supabase to different account | Easy | 5 min | 2 hrs |
| **Database** | Supabase project migration | Medium | 1 hr | 4 hrs |
| **Infrastructure** | EC2 to new account/region | Hard | 30 min | 4 hrs |
| **Users** | Import users to system | Easy | 0 | 1 hr |
| **Storage** | Local → S3 or S3 → S3 | Medium | 1 hr | 3 hrs |
| **Full Stack** | Complete system rebuild | Complex | 2 hrs | 6 hrs |

---

## Pre-Migration Planning

### Universal Checklist

**Before starting ANY migration:**

```
Preparation:
  [ ] Backup all data (Supabase, S3, GitHub)
  [ ] Document current state (credentials, versions, data size)
  [ ] Test migration in staging (if possible)
  [ ] Create new accounts/infrastructure
  [ ] Gather all new credentials
  [ ] Have rollback plan documented

Communication:
  [ ] Notify users of maintenance
  [ ] Announce expected downtime
  [ ] Set maintenance window
  [ ] Have team on standby

Safety:
  [ ] Keep old system running initially
  [ ] Don't delete anything for 1 week after migration
  [ ] Monitor logs for errors
  [ ] Have quick revert procedure
```

---

## Data Migration

### Move Between Supabase Projects

**When:** Moving to org account, changing region, upgrading

#### Export Data

```bash
# Method 1: Supabase Dashboard
1. Old Supabase Project → Table Editor
2. Select table → "Download as CSV"
3. Repeat for all 8 tables

# Method 2: SQL Export
# Old Supabase → SQL Editor → Run:
SELECT * FROM conversations;
SELECT * FROM messages;
SELECT * FROM users;
SELECT * FROM email_whitelist;
SELECT * FROM user_documents;
SELECT * FROM common_knowledge_documents;
SELECT * FROM spoc_assignments;
SELECT * FROM departments;
```

#### Create New Project

```bash
1. New Supabase account → Create new project
2. Wait for project ready (~2 min)
3. SQL Editor → Run entire database_schema.sql
4. Get credentials: Settings → API
```

#### Import Data

```bash
# Method 1: Dashboard (simple)
1. Table Editor → Select table
2. Click "Insert" → "Upload CSV"
3. Repeat for all tables

# Method 2: Python (automated)
import json, supabase
client = supabase.create_client(NEW_URL, NEW_KEY)

# Import in correct order (respect foreign keys)
import_order = ['users', 'email_whitelist', 'conversations', 
                'messages', 'user_documents', 'common_knowledge_documents']

for table in import_order:
    with open(f'{table}.json', 'r') as f:
        data = json.load(f)
    
    # Insert in batches of 100
    for i in range(0, len(data), 100):
        batch = data[i:i+100]
        client.table(table).insert(batch).execute()
        print(f"✅ {table}: batch {i//100 + 1}")
```

#### Verify

```bash
# Check row counts match
Old: 150 conversations
New: 150 conversations ✓

# Query new database
curl -H "Authorization: Bearer NEW_KEY" \
  https://NEW_URL/rest/v1/conversations?select=count=exact
```

---

### Move S3 Documents

**When:** Changing AWS account, optimizing costs, changing region

#### Create New Bucket

```bash
aws s3 mb s3://new-bucket-name --region ap-south-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket new-bucket-name \
  --versioning-configuration Status=Enabled

# Set permissions
aws s3api put-bucket-acl --bucket new-bucket-name --acl private
```

#### Copy All Files

```bash
# Via AWS CLI
aws s3 sync s3://old-bucket s3://new-bucket

# Via Python
import boto3

old_s3 = boto3.client('s3', 
  aws_access_key_id=OLD_ID, aws_secret_access_key=OLD_SECRET)
new_s3 = boto3.client('s3',
  aws_access_key_id=NEW_ID, aws_secret_access_key=NEW_SECRET)

response = old_s3.list_objects_v2(Bucket='old-bucket')
for obj in response.get('Contents', []):
    key = obj['Key']
    copy = {'Bucket': 'old-bucket', 'Key': key}
    new_s3.copy_object(CopySource=copy, Bucket='new-bucket', Key=key)
    print(f"✅ {key}")
```

#### Update Configuration

```bash
# GitHub Secrets (if bucket name changed)
S3_BUCKET_NAME = new-bucket-name
AWS_ACCESS_KEY_ID = NEW_VALUE
AWS_SECRET_ACCESS_KEY = NEW_VALUE

# Or update environment variables on EC2
export S3_BUCKET_NAME=new-bucket-name
```

---

## Credential Migration

### Change Google OAuth

**When:** Moving from personal to org Google account

```bash
# Step 1: Create OAuth app in NEW account
1. New Google Cloud account → Create project
2. APIs → Enable Google+ API
3. Credentials → Create OAuth 2.0 (Web)
4. Add redirect URIs:
   - http://localhost:8001/auth/callback
   - http://YOUR_IP:8080/auth/callback
5. Copy: Client ID, Secret

# Step 2: Setup in Supabase (new project)
1. Authentication → Providers → Google
2. Enable → Add Client ID & Secret
3. Save

# Step 3: Update GitHub Secrets
GOOGLE_CLIENT_ID = NEW_VALUE
GOOGLE_CLIENT_SECRET = NEW_VALUE

# Step 4: Deploy & Test
git push origin main
Visit: http://YOUR_IP:8080
Try login
```

---

### Change AWS Credentials

**When:** Moving from personal to org AWS account

```bash
# Step 1: Create IAM user in NEW account
1. IAM → Users → Create user
2. Attach policies:
   - AmazonEC2ContainerRegistryFullAccess
   - AmazonS3FullAccess
3. Create Access Key
4. Copy: Access Key ID, Secret

# Step 2: Create ECR repository
aws ecr create-repository \
  --repository-name vcd-tech/sevabot-mvp-gradio \
  --region ap-south-1

# Step 3: Update GitHub Secrets
AWS_ACCESS_KEY_ID = NEW_VALUE
AWS_SECRET_ACCESS_KEY = NEW_VALUE

# Step 4: Deploy & Test
git push origin main
Check: GitHub Actions workflow runs successfully
```

---

### Change OpenAI Key

**When:** Moving from personal to org account

```bash
# Step 1: Create new key
1. openai.com → API Keys
2. Create new secret key
3. Copy

# Step 2: Update GitHub Secrets
OPENAI_API_KEY = NEW_VALUE

# Step 3: Deploy & Test
git push origin main
Test in app: Ask a question, should get response
```

---

## Infrastructure Migration

### Migrate EC2 (Same/Different Account)

**When:** Account consolidation, region change, upsize/downsize

#### Launch New EC2

```bash
# AWS Console → EC2 → Launch Instance
- AMI: Ubuntu 24.04 LTS
- Type: t3.medium
- Storage: 30GB gp3
- Security group: Allow 22, 80, 443
- Get public IP/DNS
```

#### Setup Dependencies

```bash
ssh -i new-key.pem ubuntu@NEW_IP

# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu
exit
ssh -i new-key.pem ubuntu@NEW_IP

# Install Nginx
sudo apt-get install -y nginx

# Create data directories
mkdir -p ~/sevabot_data/{user_documents,rag_index,common_knowledge}
```

#### Setup GitHub Runner

```bash
cd ~
mkdir actions-runner && cd actions-runner

# Download
curl -o runner.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz

tar xzf runner.tar.gz

# Get token from: GitHub → Settings → Actions → Runners → New
./config.sh --url https://github.com/YOUR_USER/REPO --token TOKEN

# Install as service
sudo ./svc.sh install
sudo ./svc.sh start
```

#### Update Credentials

```bash
# GitHub Variables (new IP)
REDIRECT_URI = http://NEW_IP:8080/auth/callback
APP_HOST = http://NEW_IP:8080

# If changing database/AWS account:
# Also update Supabase/AWS secrets
```

#### Deploy

```bash
git push origin main

# GitHub Actions will:
# 1. Build Docker image
# 2. Push to ECR
# 3. SSH to new runner
# 4. Pull & run container
# 5. Configure Nginx

# Monitor: GitHub Actions tab
```

#### Verify

```bash
curl http://NEW_IP:8080/health
# Should return: {"status": "healthy", ...}

curl http://NEW_IP:8080/admin/docs
# Should load Swagger UI

# Test login
Visit: http://NEW_IP:8080 in browser
```

---

## User Migration

### Import Users from CSV

**When:** Moving from different system, onboarding team

#### Prepare CSV

```csv
email,role,department
swapnil@company.org,admin,Engineering
user1@company.org,user,Operations
spoc@company.org,spoc,Management
```

#### Import via Dashboard

```bash
1. Supabase → Table Editor → email_whitelist
2. Click "Insert" → "Upload CSV"
3. Map columns
4. Upload
```

#### Import via Python

```python
import csv, supabase

client = supabase.create_client(SUPABASE_URL, SERVICE_ROLE_KEY)

with open('users.csv', 'r') as f:
    for row in csv.DictReader(f):
        client.table('email_whitelist').insert({
            'email': row['email'],
            'role': row['role'],
            'added_by': 'system',
            'is_active': True,
            'department': row.get('department', '')
        }).execute()
        print(f"✅ {row['email']}")
```

#### Notify Users

```bash
Send email:
Subject: SEVABOT Access Ready

Hi [Name],
Your SEVABOT account is ready.
Visit: http://YOUR_IP:8080
Login with Google account

Questions? tech-support@company.org
```

---

## Post-Migration Validation

### Run Full Validation

```bash
# 1. Health Check
curl http://YOUR_IP:8080/health
# Expected: 200 OK with status: healthy

# 2. Database Connectivity
curl -H "Authorization: Bearer KEY" \
  https://SUPABASE_URL/rest/v1/conversations?select=count=exact
# Expected: Returns number

# 3. OAuth Login
Visit: http://YOUR_IP:8080
Click: Login with Google
Should redirect & login successfully

# 4. Swagger Docs
Visit: http://YOUR_IP:8080/admin/docs
Should show: All 18 endpoints

# 5. Logs Check
docker logs sevabot-container
# Should show: No critical errors

# 6. Performance
time curl http://YOUR_IP:8080/health
# Expected: <1 second

# 7. Data Integrity
Old project: 150 conversations
New project: 150 conversations ✓

# 8. Feature Test
- Upload document
- Search documents
- Chat with bot
- Create conversation
All should work normally
```

---

## Rollback Procedures

### Revert Credentials

```bash
# If something goes wrong:
GitHub → Settings → Secrets and variables

# Revert to old values
GOOGLE_CLIENT_ID = OLD_VALUE
GOOGLE_CLIENT_SECRET = OLD_VALUE
(etc for all 8 secrets)

# Deploy
git push origin main
Old system restored within 5 minutes
```

### Revert Infrastructure

```bash
# If new EC2 has issues:

# Option 1: Keep old EC2 running
# Tell users to use old IP temporarily
# Investigate new EC2 issue
# Retry migration

# Option 2: Terminate new EC2
aws ec2 terminate-instances --instance-ids NEW_ID

# Go back to old IP in GitHub Variables
REDIRECT_URI = OLD_IP:8080/auth/callback
APP_HOST = OLD_IP:8080

# Deploy
git push origin main
```

### Revert Database

```bash
# If Supabase migration has issues:

# Option 1: Restore from backup
Supabase → Settings → Backups → Restore
(Creates new project with old data)

# Option 2: Keep old project running
Update SUPABASE_URL back to old project
git push origin main
Old database used again
```

---

## Common Issues & Solutions

### OAuth Login Fails: "Redirect URI Mismatch"

```
Problem: After migration, login shows error

Solution:
1. Check Google Cloud Console
   APIs & Services → Credentials → OAuth 2.0 client
2. Add/update Authorized redirect URIs:
   http://NEW_IP:8080/auth/callback
3. Also update in Supabase:
   Authentication → Providers → Settings
4. Wait 5 minutes for changes to propagate
5. Try login again
```

### Database Connection Timeout

```
Problem: curl SUPABASE_URL returns error

Solution:
1. Verify Supabase project is running
   Dashboard → check project status
2. Check credentials in GitHub Secrets
   SUPABASE_URL correct?
   SUPABASE_KEY correct?
3. Test with curl:
   curl -H "Authorization: Bearer KEY" \
   https://URL/rest/v1/conversations
4. Should return 200, not 401/403
```

### GitHub Actions Runner Not Available

```
Problem: Workflow shows "No runner available"

Solution:
1. Check GitHub runner is connected
   Settings → Actions → Runners
   Should show: Idle (green)
2. SSH to EC2:
   cd ~/actions-runner
   sudo ./svc.sh status
   Should show: Running
3. If not running:
   sudo ./svc.sh start
4. Retry workflow
```

### Docker Build Fails in ECR

```
Problem: GitHub Actions fails at "Push to ECR"

Solution:
1. Verify ECR repository exists
   aws ecr describe-repositories --region ap-south-1
2. Verify AWS credentials in GitHub
   AWS_ACCESS_KEY_ID correct?
   AWS_SECRET_ACCESS_KEY correct?
3. Verify IAM user has permissions
   IAM → Users → Policies
   Should have: AmazonEC2ContainerRegistryFullAccess
4. Retry workflow
```

### S3 Upload Fails: "Access Denied"

```
Problem: Document upload to S3 fails

Solution:
1. Verify S3 bucket exists
   aws s3 ls
2. Verify IAM user has S3 permissions
   IAM → Users → Policies
   Should have: AmazonS3FullAccess
3. Verify credentials in GitHub
   AWS_ACCESS_KEY_ID correct?
   AWS_SECRET_ACCESS_KEY correct?
4. Verify S3_BUCKET_NAME in environment
5. Retry upload
```

### Data Mismatch After Migration

```
Problem: Row counts don't match
Old: 150 conversations
New: 140 conversations

Solution:
1. Identify missing rows
   SELECT id FROM old_table WHERE id NOT IN (SELECT id FROM new_table)
2. Check export was complete
3. Re-export missing rows
4. Re-import to new table
5. Verify counts match again
```

### Nginx 502 Bad Gateway

```
Problem: Browser shows 502 error

Solution:
1. Check container is running
   docker ps | grep sevabot
   Should show: sevabot-container
2. Check container logs
   docker logs sevabot-container
3. Check if port 8001 is open
   docker port sevabot-container
   Should show: 8001/tcp → 0.0.0.0:8001
4. Test direct connection
   curl http://localhost:8001/health
5. If still fails, restart
   docker restart sevabot-container
```

---

## Migration Decision Tree

```
Which migration do you need?

├─ Change Credentials?
│  ├─ OAuth → Update GOOGLE_CLIENT_ID/SECRET
│  ├─ AWS → Update AWS_ACCESS_KEY_ID/SECRET
│  ├─ OpenAI → Update OPENAI_API_KEY
│  └─ Supabase → Update SUPABASE_URL/KEY
│
├─ Change Database?
│  ├─ Supabase project → Follow "Data Migration"
│  ├─ RDS → Major refactor (see advanced docs)
│  └─ Just backup → Supabase handles automatically
│
├─ Change EC2?
│  ├─ Same account, new IP → Update DNS + GitHub vars
│  ├─ New account → New EC2 + migrate credentials
│  ├─ New region → New EC2 in region + DNS
│  └─ Scale up/down → Terminate + launch new size
│
├─ Change Storage?
│  ├─ Local → S3 → Create bucket + sync files
│  ├─ S3 → S3 → AWS CLI sync to new bucket
│  └─ S3 → Local → aws s3 sync to EC2
│
├─ Import Users?
│  ├─ From CSV → Upload to email_whitelist
│  ├─ From old system → Export + import
│  └─ Onboarding → Create manually or batch import
│
├─ Upgrade Version?
│  ├─ Code only → git checkout + deploy
│  ├─ Database schema changes → Run migrations
│  └─ Breaking changes → Follow migration guide
│
└─ Recover from Disaster?
   ├─ Data corruption → Restore from backup
   ├─ System crash → New EC2 + restore volumes
   ├─ Config error → Revert GitHub secrets
   └─ Complete rebuild → All of above
```

---

## Quick Reference

| Action | Command |
|--------|---------|
| **Backup Supabase** | Dashboard → Backups → Download |
| **Export CSV** | Table Editor → Download as CSV |
| **Copy S3 Bucket** | `aws s3 sync s3://old s3://new` |
| **Check Container** | `docker ps \| grep sevabot` |
| **View Logs** | `docker logs sevabot-container` |
| **Test Health** | `curl http://IP:8080/health` |
| **SSH to EC2** | `ssh -i key.pem ubuntu@IP` |
| **Restart Docker** | `docker restart sevabot-container` |
| **Reload Nginx** | `sudo systemctl reload nginx` |
| **View Nginx Logs** | `sudo tail -f /var/log/nginx/error.log` |

---

## Final Checklist

Before & after every migration:

**Before:**
- [ ] All new accounts created
- [ ] All credentials ready
- [ ] Backup taken
- [ ] Team notified
- [ ] Rollback plan written

**After:**
- [ ] Health check passes
- [ ] Login works
- [ ] Data verified
- [ ] Logs clean
- [ ] Users happy
- [ ] Old system kept 1 week
- [ ] Lessons documented

---

**Last Updated:** January 31, 2026  
**Status:** Complete & Production-Ready ✅

For specific migration help, find your scenario above and follow step-by-step instructions.
