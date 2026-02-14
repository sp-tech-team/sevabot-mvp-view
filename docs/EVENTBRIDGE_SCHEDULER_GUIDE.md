# AWS EventBridge Scheduler - EC2 Auto Start/Stop

Guide for managing automatic EC2 instance start and stop schedules.

---

## Overview

EventBridge Scheduler automatically starts and stops your EC2 instance on a schedule, saving costs when the instance is not in use.

```
Monday-Friday:
  ├─ 9:00 AM   → Start instance (ready for work)
  └─ 9:15 PM   → Stop instance (end of day)

Weekend & Holidays:
  └─ Instance stays stopped
```

---

## Most Common Tasks

### Check if Schedules Exist

```bash
aws scheduler list-schedules --query "Schedules[].Name" --output text
```

**Expected output:**
```
Stop-EC2-Instance-Daily  Start-EC2-Instance-Daily
```

### View Schedule Details

```bash
aws scheduler get-schedule --name Stop-EC2-Instance-Daily --output json
```

**Key information shown:**
- Schedule name
- Cron expression (timing)
- Current state (ENABLED or DISABLED)
- Time zone

### Disable Schedule (Temporarily Pause)

Prevents execution but keeps the configuration.

```bash
aws scheduler update-schedule \
  --name Stop-EC2-Instance-Daily \
  --state DISABLED
```

### Enable Schedule (Resume)

Reactivates a disabled schedule.

```bash
aws scheduler update-schedule \
  --name Stop-EC2-Instance-Daily \
  --state ENABLED
```

### Check Current State

```bash
aws scheduler get-schedule --name Stop-EC2-Instance-Daily --query "State"
```

**Output:**
```
"ENABLED"
```

or

```
"DISABLED"
```

---

## Manual EC2 Control

Use these when you need immediate action (not waiting for schedule).

### Start EC2 Instance Immediately

```bash
aws ec2 start-instances --instance-ids i-0f1ffdb49f0553fb5
```

### Stop EC2 Instance Immediately

```bash
aws ec2 stop-instances --instance-ids i-0f1ffdb49f0553fb5
```

### Reboot EC2 Instance

```bash
aws ec2 reboot-instances --instance-ids i-0f1ffdb49f0553fb5
```

### Check Current State

```bash
aws ec2 describe-instances \
  --instance-ids i-0f1ffdb49f0553fb5 \
  --query "Reservations[*].Instances[*].State.Name" \
  --output text
```

**States:**
- `pending` → booting up
- `running` → ready
- `stopping` → shutting down
- `stopped` → off

---

## Common Scenarios

### Scenario 1: Need to Keep Server Running (Disable Auto-Stop)

```bash
# Problem: Server is stopping at 9:15 PM but you need it running

# Solution: Disable the stop schedule
aws scheduler update-schedule \
  --name Stop-EC2-Instance-Daily \
  --state DISABLED

# Keep working...

# When done, re-enable it
aws scheduler update-schedule \
  --name Stop-EC2-Instance-Daily \
  --state ENABLED
```

### Scenario 2: Need Server Started Earlier (Manual Start)

```bash
# Problem: Schedule starts at 9:00 AM but you need it at 8:00 AM

# Solution: Start it manually
aws ec2 start-instances --instance-ids i-0f1ffdb49f0553fb5

# Wait for it to boot (~1 minute)
# Then SSH and work
```

### Scenario 3: Server Stuck or Not Responding

```bash
# Problem: Instance won't restart or hung

# Solution: Stop it manually, wait, then start
aws ec2 stop-instances --instance-ids i-0f1ffdb49f0553fb5

# Wait 30 seconds
sleep 30

aws ec2 start-instances --instance-ids i-0f1ffdb49f0553fb5

# Wait for boot, then connect
```

### Scenario 4: Check if Stop/Start Actually Worked

```bash
# After issuing a stop/start command

# Check state immediately (should be pending/stopping)
aws ec2 describe-instances \
  --instance-ids i-0f1ffdb49f0553fb5 \
  --query "Reservations[*].Instances[*].State.Name" \
  --output text

# Wait 30 seconds and check again
sleep 30
aws ec2 describe-instances \
  --instance-ids i-0f1ffdb49f0553fb5 \
  --query "Reservations[*].Instances[*].State.Name" \
  --output text
```

---

## Schedule Configuration

### Edit Schedule Timing

To change when the instance stops/starts, you need the full configuration.

**Get current config:**

```bash
aws scheduler get-schedule --name Stop-EC2-Instance-Daily --output json > schedule-backup.json
```

**Edit the JSON file** (change the cron expression), then apply:

```bash
# Full update (use the JSON from the file above)
aws scheduler update-schedule \
  --name Stop-EC2-Instance-Daily \
  --state ENABLED \
  --schedule-expression "cron(15 21 * * ? *)" \
  --schedule-expression-timezone "Asia/Calcutta" \
  --flexible-time-window '{"Mode":"OFF"}' \
  --target '{
    "Arn":"arn:aws:scheduler:::aws-sdk:ec2:stopInstances",
    "Input":"{\"InstanceIds\":[\"i-0f1ffdb49f0553fb5\"]}",
    "RetryPolicy":{"MaximumEventAgeInSeconds":86400,"MaximumRetryAttempts":0},
    "RoleArn":"arn:aws:iam::908924926461:role/EC2-Start-Stop-Scheduler-Role"
  }'
```

**Cron Expression Breakdown:**

```
cron(15 21 * * ? *)
      ↓  ↓  ↓ ↓ ↓ ↓
      │  │  │ │ │ └─ Day of week (? = any)
      │  │  │ │ └──── Month (? = any)
      │  │  │ └─────── Day of month (* = every)
      │  │  └───────── Hour (* = every)
      │  └──────────── Minute (21 = 9 PM)
      └─────────────── Second (15)
```

**Common examples:**
- `cron(0 9 * * ? *)` = 9:00 AM every day
- `cron(30 17 * * ? *)` = 5:30 PM every day
- `cron(0 0 * * ? *)` = Midnight every day
- `cron(0 9 ? * MON-FRI *)` = 9:00 AM Monday-Friday

---

## Troubleshooting

### Scheduler Command Requires Full Config

**Error:** `InvalidParameterException: One or more parameters for the request are invalid`

**Reason:** EventBridge Scheduler requires the complete configuration when updating state

**Solution:** Always include `--target`, `--schedule-expression`, etc.

### Can't Find Schedule

```bash
aws scheduler list-schedules
```

If empty, there are no schedules. Check AWS Console → EventBridge Scheduler

### Instance Didn't Stop/Start

**Check reasons:**

```bash
# 1. Is the schedule enabled?
aws scheduler get-schedule --name Stop-EC2-Instance-Daily --query "State"

# 2. Did the schedule run yet? (Check time)
date
# Compare to your cron expression

# 3. Check IAM role has permissions
# AWS Console → EventBridge Scheduler → Check execution role
```

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| `aws scheduler list-schedules` | List all schedules |
| `aws scheduler get-schedule --name NAME` | View schedule details |
| `aws scheduler update-schedule --name NAME --state DISABLED` | Disable schedule |
| `aws scheduler update-schedule --name NAME --state ENABLED` | Enable schedule |
| `aws ec2 start-instances --instance-ids ID` | Start instance now |
| `aws ec2 stop-instances --instance-ids ID` | Stop instance now |
| `aws ec2 describe-instances --instance-ids ID` | Check instance state |
| `aws scheduler delete-schedule --name NAME` | Delete schedule permanently |

---

## When to Use What

| Situation | Use This |
|-----------|----------|
| Need to work after 9:15 PM | Disable stop schedule manually |
| Server won't start at 9:00 AM | Start it manually with `start-instances` |
| Server is frozen/hung | Stop it, wait, start it manually |
| Want to keep server off for a week | Disable both start and stop schedules |
| Want to change stop time to 8:00 PM | Edit schedule JSON and update |

---

## Pro Tips

1. **Always have a backup:** Before editing schedules, export the JSON
   ```bash
   aws scheduler get-schedule --name NAME > backup.json
   ```

2. **Use manual commands more:** For one-off starts/stops, use `aws ec2` directly
   ```bash
   aws ec2 start-instances --instance-ids i-xxxxx
   ```

3. **Check state after action:** Don't assume it worked immediately
   ```bash
   aws ec2 describe-instances --instance-ids i-xxxxx --query "State.Name"
   ```

4. **Keep server running temporarily:** Easier to disable stop schedule than modify time

---

## Related Resources

- [AWS EventBridge Scheduler Docs](https://docs.aws.amazon.com/scheduler/)
- [AWS EC2 Documentation](https://docs.aws.amazon.com/ec2/)
- [Cron Expression Reference](https://docs.aws.amazon.com/scheduler/latest/UserGuide/managing-schedule-expression.html)

---

**Last Updated:** February 2, 2026  
**Status:** Essential Tasks Only ✅
