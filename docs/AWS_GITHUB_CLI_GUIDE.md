# AWS & GitHub CLI Commands - SEVABOT Reference

Minimal, essential commands for managing SEVABOT infrastructure.

---

## Table of Contents

1. [AWS Setup](#aws-setup)
2. [AWS EC2 Commands](#aws-ec2-commands)
3. [AWS ECR Commands](#aws-ecr-commands)
4. [AWS S3 Commands](#aws-s3-commands)
5. [GitHub CLI Commands](#github-cli-commands)
6. [System Monitoring](#system-monitoring)
7. [Quick Troubleshooting](#quick-troubleshooting)

---

## AWS Setup

### Configure AWS Credentials

```bash
aws configure

# Prompts for:
AWS Access Key ID: [paste value]
AWS Secret Access Key: [paste value]
Default region: ap-south-1
Default output format: json
```

**Where to get credentials:**
- AWS Console → IAM → Users → [Your user] → Security credentials
- Or check Slack: `vcd-tech-ai-projects` channel

### Verify Configuration

```bash
aws sts get-caller-identity
```

**Expected output:**
```
{
    "UserId": "AIDA5HIBFXH6TCTJD4772",
    "Account": "908924926461",
    "Arn": "arn:aws:iam::908924926461:user/YourUsername"
}
```

---

## AWS EC2 Commands

### List EC2 Instances

```bash
aws ec2 describe-instances \
  --query "Reservations[*].Instances[*].[InstanceId,Tags[?Key=='Name']|[0].Value,PublicDnsName]" \
  --output table
```

**Example output:**
```
i-0f1ffdb49f0553fb5  |  sevabot-prod  |  ec2-13-233-157-26.ap-south-1.compute.amazonaws.com
```

### Start Instance

```bash
aws ec2 start-instances --instance-ids i-0f1ffdb49f0553fb5
```

### Stop Instance

```bash
aws ec2 stop-instances --instance-ids i-0f1ffdb49f0553fb5
```

### Reboot Instance

```bash
aws ec2 reboot-instances --instance-ids i-0f1ffdb49f0553fb5
```

### Check Instance State

```bash
aws ec2 describe-instances \
  --instance-ids i-0f1ffdb49f0553fb5 \
  --query "Reservations[*].Instances[*].State.Name" \
  --output text
```

**Possible states:** `pending` → `running` → `stopping` → `stopped`

### Get Public IP

```bash
aws ec2 describe-instances \
  --instance-ids i-0f1ffdb49f0553fb5 \
  --query "Reservations[*].Instances[*].PublicIpAddress" \
  --output text
```

---

## AWS ECR Commands

### List ECR Repositories

```bash
aws ecr describe-repositories --region ap-south-1 --output table
```

### Create ECR Repository

```bash
aws ecr create-repository \
  --repository-name vcd-tech/sevabot-mvp-gradio \
  --region ap-south-1
```

### Login to ECR

```bash
aws ecr get-login-password --region ap-south-1 | \
  docker login --username AWS --password-stdin \
  908924926461.dkr.ecr.ap-south-1.amazonaws.com
```

### Push Docker Image to ECR

```bash
docker tag sevabot:latest 908924926461.dkr.ecr.ap-south-1.amazonaws.com/vcd-tech/sevabot-mvp-gradio:latest

docker push 908924926461.dkr.ecr.ap-south-1.amazonaws.com/vcd-tech/sevabot-mvp-gradio:latest
```

### List Images in Repository

```bash
aws ecr describe-images \
  --repository-name vcd-tech/sevabot-mvp-gradio \
  --region ap-south-1 \
  --output table
```

### Delete Image from ECR

```bash
aws ecr batch-delete-image \
  --repository-name vcd-tech/sevabot-mvp-gradio \
  --image-ids imageTag=88ce55026c4fcdd4641ec2349833e149c86d4f81 \
  --region ap-south-1
```

---

## AWS S3 Commands

### List S3 Buckets

```bash
aws s3 ls
```

### List Contents of Bucket

```bash
aws s3 ls s3://sevabot-documents-prod/
```

### Copy File to S3

```bash
aws s3 cp test.pdf s3://sevabot-documents-prod/
```

### Sync Directory to S3

```bash
aws s3 sync ~/sevabot_data/user_documents s3://sevabot-documents-prod/user_documents/
```

### Sync from S3 (Download)

```bash
aws s3 sync s3://sevabot-documents-prod/user_documents ~/sevabot_data/user_documents/
```

### Delete from S3

```bash
aws s3 rm s3://sevabot-documents-prod/old-file.pdf
```

---

## GitHub CLI Commands

### Login to GitHub

```bash
gh auth login

# Choose:
# - GitHub.com
# - HTTPS
# - Authenticate with browser
```

### View Repository Details

```bash
gh repo view
```

### View Secrets

```bash
gh secret list
```

### Update Secret

```bash
gh secret set GOOGLE_CLIENT_ID --body "new_value"
```

### Create Issue

```bash
gh issue create --title "Bug: Something broken" --body "Description"
```

### View Workflow Runs

```bash
gh run list
```

### View Latest Workflow Run

```bash
gh run view --log
```

### Watch Workflow Run

```bash
gh run watch
```

### Create Pull Request

```bash
gh pr create --title "Feature: New migration guide" --body "Description"
```

---

## System Monitoring (On EC2)

### Disk Space

```bash
df -h
```

### Memory Usage (One-time)

```bash
free -h
```

### Memory Usage (Continuous, updates every 1 second)

```bash
watch -n 1 free -h
```

Press `Ctrl+C` to exit

### List Docker Containers

```bash
docker ps -a
```

### List Docker Images

```bash
docker images
```

### Remove Docker Image

```bash
docker rmi 908924926461.dkr.ecr.ap-south-1.amazonaws.com/vcd-tech/sevabot-mvp-gradio:88ce55026c4fcdd4641ec2349833e149c86d4f81
```

### View Container Logs

```bash
docker logs sevabot-container
```

### Follow Logs (Real-time)

```bash
docker logs -f sevabot-container
```

### Container Resource Usage

```bash
docker stats sevabot-container
```

---

## Quick Troubleshooting

### Container Not Running?

```bash
# Check status
docker ps | grep sevabot

# Check logs for errors
docker logs sevabot-container

# Restart
docker restart sevabot-container
```

### Can't Connect to Database?

```bash
# Verify Supabase URL and key are correct in GitHub Secrets
gh secret list | grep SUPABASE

# Test connection from EC2
curl -H "Authorization: Bearer $SUPABASE_KEY" \
  https://$SUPABASE_URL/rest/v1/conversations?select=count=exact
```

### EC2 Instance Not Responding?

```bash
# Check state
aws ec2 describe-instances --instance-ids i-0f1ffdb49f0553fb5 \
  --query "Reservations[*].Instances[*].State.Name" --output text

# If stopped, start it
aws ec2 start-instances --instance-ids i-0f1ffdb49f0553fb5

# Wait 30 seconds, then SSH
ssh -i key.pem ubuntu@IP
```

### Out of Disk Space?

```bash
# Check usage
df -h

# Remove old Docker images (keep latest)
docker image prune -f

# Remove stopped containers
docker container prune -f

# Check what's taking space
du -sh ~/sevabot_data/*
```

---

## Git Commands (Related)

### Revert Commit (Keep Changes Staged)

```bash
git reset --soft HEAD~1
```

Then commit again with different message:

```bash
git commit -m "New message"
```

### Force Push (After Reverting)

```bash
git push origin HEAD --force
```

### View Commit History

```bash
git log --oneline | head -10
```

### Revert to Previous Commit (Undo Changes)

```bash
git revert <commit-hash>
```

### Discard Local Changes

```bash
git reset --hard HEAD
```

---

## Common Workflows

### Update Credentials & Deploy

```bash
# 1. Update GitHub secrets
gh secret set GOOGLE_CLIENT_ID --body "new_value"
gh secret set GOOGLE_CLIENT_SECRET --body "new_value"

# 2. Push code (triggers deployment)
git push origin main

# 3. Monitor deployment
gh run watch

# 4. Verify
ssh -i key.pem ubuntu@IP
curl http://localhost:8080/health
```

### Backup & Migration

```bash
# 1. Export database from Supabase Dashboard
# (Or use SQL export)

# 2. Backup S3 documents
aws s3 sync s3://old-bucket ~/backup/

# 3. Create new S3 bucket
aws s3 mb s3://new-bucket

# 4. Copy files
aws s3 sync ~/backup/ s3://new-bucket/

# 5. Update GitHub secrets
gh secret set AWS_ACCESS_KEY_ID --body "new_value"

# 6. Deploy
git push origin main
```

### Clean Up Old Infrastructure

```bash
# 1. Stop old EC2 instance
aws ec2 stop-instances --instance-ids i-old-id

# 2. Delete old ECR images
aws ecr batch-delete-image \
  --repository-name vcd-tech/sevabot-mvp-gradio \
  --image-ids imageTag=old-tag

# 3. Delete old S3 bucket (after verifying it's empty)
# AWS Console → S3 → Select bucket → Delete
```

---

## Useful Resources

- [AWS CLI Documentation](https://docs.aws.amazon.com/cli/)
- [AWS EC2 User Guide](https://docs.aws.amazon.com/ec2/)
- [GitHub CLI Reference](https://cli.github.com/manual)
- [Docker Documentation](https://docs.docker.com/)

---

## Cheat Sheet

| Task | Command |
|------|---------|
| **List EC2** | `aws ec2 describe-instances --output table` |
| **Start EC2** | `aws ec2 start-instances --instance-ids i-xxxxx` |
| **Stop EC2** | `aws ec2 stop-instances --instance-ids i-xxxxx` |
| **Get IP** | `aws ec2 describe-instances --instance-ids i-xxxxx --query "Reservations[*].Instances[*].PublicIpAddress" --output text` |
| **List ECR** | `aws ecr describe-repositories --output table` |
| **List S3** | `aws s3 ls` |
| **Sync S3** | `aws s3 sync ~/data s3://bucket/` |
| **View Logs** | `docker logs sevabot-container` |
| **Check Disk** | `df -h` |
| **Check Memory** | `free -h` |
| **Docker Stats** | `docker stats sevabot-container` |
| **GitHub Secrets** | `gh secret list` |
| **Update Secret** | `gh secret set KEY --body "value"` |

---

**Last Updated:** February 2, 2026  
**Status:** Essential Commands Only ✅
