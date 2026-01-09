# Troubleshooting Guide

This guide covers common issues you might encounter when using Instancepedia and how to resolve them.

## Table of Contents

- [Installation Issues](#installation-issues)
- [AWS Credentials and Authentication](#aws-credentials-and-authentication)
- [Region and Access Issues](#region-and-access-issues)
- [Pricing Data Issues](#pricing-data-issues)
- [TUI Performance and Display](#tui-performance-and-display)
- [CLI Issues](#cli-issues)
- [Filter Issues](#filter-issues)
- [Cache Issues](#cache-issues)
- [Network and Timeout Issues](#network-and-timeout-issues)
- [Getting Help](#getting-help)

---

## Installation Issues

### Problem: `pip install instancepedia` fails

**Symptoms:**
```
ERROR: Could not find a version that satisfies the requirement instancepedia
```

**Solutions:**

1. **Update pip**:
   ```bash
   pip install --upgrade pip
   ```

2. **Check Python version** (requires Python >= 3.9):
   ```bash
   python --version
   # or
   python3 --version
   ```

3. **Use pip3 explicitly**:
   ```bash
   pip3 install instancepedia
   ```

4. **Install in a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install instancepedia
   ```

### Problem: `ModuleNotFoundError` after installation

**Symptoms:**
```
ModuleNotFoundError: No module named 'instancepedia'
```

**Solutions:**

1. **Verify installation**:
   ```bash
   pip show instancepedia
   ```

2. **Check if you're in the correct virtual environment**:
   ```bash
   which python  # Should point to your venv if using one
   ```

3. **Try reinstalling**:
   ```bash
   pip uninstall instancepedia
   pip install instancepedia
   ```

---

## AWS Credentials and Authentication

### Problem: "Unable to locate credentials"

**Symptoms:**
```
botocore.exceptions.NoCredentialsError: Unable to locate credentials
```

**Solutions:**

1. **Configure AWS credentials** (choose one method):

   **Option A: AWS CLI**:
   ```bash
   aws configure
   ```

   **Option B: Environment variables**:
   ```bash
   export AWS_ACCESS_KEY_ID=your_access_key
   export AWS_SECRET_ACCESS_KEY=your_secret_key
   export AWS_DEFAULT_REGION=us-east-1
   ```

   **Option C: AWS profile**:
   ```bash
   # In ~/.aws/credentials:
   [your-profile]
   aws_access_key_id = your_access_key
   aws_secret_access_key = your_secret_key

   # Use the profile:
   export AWS_PROFILE=your-profile
   # Or:
   instancepedia --tui  # Will use INSTANCEPEDIA_AWS_PROFILE env var
   ```

2. **Verify credentials are working**:
   ```bash
   aws sts get-caller-identity
   ```

### Problem: "Access Denied" or "Not Authorized"

**Symptoms:**
```
An error occurred (UnauthorizedOperation) when calling the DescribeInstanceTypes operation
```

**Solutions:**

1. **Verify IAM permissions** - ensure your user/role has required permissions:
   ```json
   {
       "Version": "2012-10-17",
       "Statement": [
           {
               "Effect": "Allow",
               "Action": [
                   "ec2:DescribeRegions",
                   "ec2:DescribeInstanceTypes",
                   "ec2:DescribeSpotPriceHistory",
                   "pricing:GetProducts"
               ],
               "Resource": "*"
           }
       ]
   }
   ```

2. **Check if you're using the right AWS account**:
   ```bash
   aws sts get-caller-identity
   ```

3. **Try a different profile** if you have multiple:
   ```bash
   export AWS_PROFILE=your-other-profile
   instancepedia --tui
   ```

### Problem: "Security token expired"

**Symptoms:**
```
ExpiredToken: The security token included in the request is expired
```

**Solutions:**

1. **Refresh temporary credentials** (if using assume-role or SSO):
   ```bash
   aws sso login  # For SSO
   # or
   # Re-run your assume-role command
   ```

2. **Use permanent credentials** for long-running sessions

3. **Clear any cached credentials**:
   ```bash
   rm -rf ~/.aws/cli/cache/
   ```

---

## Region and Access Issues

### Problem: "Region not enabled for your account"

**Symptoms:**
```
OptInRequired: You are not authorized to perform this operation.
This region may not be enabled for your account.
```

**Solutions:**

1. **Check available regions**:
   ```bash
   instancepedia regions
   ```

2. **Enable the region** in AWS Console:
   - Go to AWS Console → Account → AWS Regions
   - Enable the desired region
   - Wait a few minutes for activation

3. **Use a different region**:
   ```bash
   instancepedia --tui --region us-east-1
   ```

### Problem: "Invalid region name"

**Symptoms:**
```
Could not connect to the endpoint URL
```

**Solutions:**

1. **List valid regions**:
   ```bash
   instancepedia regions
   ```

2. **Check region spelling**:
   ```bash
   # Correct:
   instancepedia --tui --region us-east-1

   # Incorrect:
   instancepedia --tui --region us-east1  # Missing hyphen
   ```

3. **Verify region exists**:
   ```bash
   aws ec2 describe-regions --all-regions
   ```

---

## Pricing Data Issues

### Problem: Pricing shows as "N/A" or not loading

**Symptoms:**
- TUI shows "Loading..." indefinitely
- CLI shows "N/A" for prices
- Status bar shows "X prices unavailable"

**Solutions:**

1. **Wait for background load to complete** (TUI mode):
   - Pricing loads in background after instance types are displayed
   - Check status bar for progress: "⏳ Loading prices... (X/Y)"
   - Can take 30-60 seconds for first load in large regions

2. **Check pricing permissions**:
   ```bash
   aws pricing get-products \
     --service-code AmazonEC2 \
     --filters Type=TERM_MATCH,Field=location,Value="US East (N. Virginia)" \
     --max-results 1
   ```

3. **Retry failed pricing** (TUI mode):
   - Press `R` to retry failed pricing requests
   - Lower concurrency retry for better reliability

4. **Clear cache and retry**:
   ```bash
   instancepedia cache clear --force
   instancepedia --tui
   ```

5. **Check debug logs** (TUI mode):
   ```bash
   instancepedia --tui --debug
   # Watch the debug pane for pricing errors
   ```

6. **Try CLI mode to see detailed errors**:
   ```bash
   instancepedia pricing t3.micro --region us-east-1
   ```

### Problem: Spot prices not showing

**Symptoms:**
- On-demand pricing works
- Spot pricing shows "N/A" or "Loading..."

**Solutions:**

1. **Check spot price permissions**:
   - Ensure `ec2:DescribeSpotPriceHistory` is in your IAM policy

2. **Wait for async fetch** (TUI detail view):
   - Spot prices fetch in background when viewing instance details
   - Takes a few seconds per instance

3. **Some instance types don't support spot**:
   - Check if the instance type actually supports spot instances
   - Not all instance types are available as spot

4. **Verify with AWS CLI**:
   ```bash
   aws ec2 describe-spot-price-history \
     --instance-types t3.micro \
     --max-results 1
   ```

### Problem: Pricing data seems stale or incorrect

**Symptoms:**
- Prices don't match AWS Console
- Old pricing showing

**Solutions:**

1. **Clear cache to force refresh**:
   ```bash
   instancepedia cache clear --force
   ```

2. **Check cache age**:
   ```bash
   instancepedia cache stats
   # Look at "Average age" field
   ```

3. **Verify you're checking the same region**:
   - Pricing varies by region
   - Ensure you're comparing same region in Console

4. **Check cache TTL** (default 4 hours):
   - Cache automatically refreshes after 4 hours
   - Or clear manually as shown above

---

## TUI Performance and Display

### Problem: TUI is slow or unresponsive

**Symptoms:**
- Keypresses lag
- Screen updates slowly
- "Loading..." persists

**Solutions:**

1. **Wait for initial pricing load**:
   - First run fetches all pricing data
   - Can take 30-60 seconds in large regions
   - Subsequent runs use cache and are instant

2. **Close other terminal applications**:
   - Some terminals have performance limits
   - Try a different terminal emulator

3. **Reduce terminal size**:
   - Very large terminals (>200x50) can be slow
   - Resize to more standard size

4. **Check system resources**:
   ```bash
   top  # Check CPU/memory usage
   ```

5. **Use CLI mode for quick queries**:
   ```bash
   instancepedia list --region us-east-1 --format table
   ```

### Problem: TUI display is garbled or incorrectly rendered

**Symptoms:**
- Characters overlapping
- Box drawing characters show as `?` or wrong symbols
- Colors not displaying

**Solutions:**

1. **Ensure UTF-8 locale**:
   ```bash
   echo $LANG
   # Should show something like: en_US.UTF-8

   # If not, set it:
   export LANG=en_US.UTF-8
   export LC_ALL=en_US.UTF-8
   ```

2. **Use a modern terminal**:
   - iTerm2 (macOS)
   - Windows Terminal (Windows)
   - GNOME Terminal or Konsole (Linux)
   - Avoid very old terminals or basic terminals

3. **Check terminal color support**:
   ```bash
   echo $TERM
   # Should be xterm-256color or similar

   # If not:
   export TERM=xterm-256color
   ```

4. **Try a different terminal emulator**

5. **Resize terminal and restart**:
   - Sometimes resizing fixes rendering issues

### Problem: Tree categories not expanding

**Symptoms:**
- Pressing Enter doesn't expand categories
- Categories show ">" but don't open

**Solutions:**

1. **Use Space key instead**:
   - Both Enter and Space should work
   - Space is dedicated expand/collapse key

2. **Wait for data to load**:
   - Tree may not respond until instance types are loaded
   - Check for "Loading..." in header

3. **Check if you're on a leaf node**:
   - Instance types (leaves) open detail view
   - Only categories and families expand

4. **Restart the application**:
   ```bash
   # Press Q to quit, then restart
   instancepedia --tui
   ```

### Problem: Search not working

**Symptoms:**
- Pressing `/` doesn't activate search
- Typing doesn't filter results

**Solutions:**

1. **Press `/` to focus search input**:
   - Search input should be highlighted
   - Cursor should be blinking in search box

2. **Clear existing search**:
   - Delete text in search box
   - Or press Esc to cancel search

3. **Use filters instead for complex queries**:
   - Press `F` to open filter modal
   - More powerful than simple search

4. **Check keyboard is working**:
   - Try other keyboard shortcuts (Q, C, etc.)

---

## CLI Issues

### Problem: No output from CLI commands

**Symptoms:**
- Command completes but shows nothing
- Exit code is 0 but no data displayed

**Solutions:**

1. **Check output format**:
   ```bash
   # Explicitly set format:
   instancepedia list --region us-east-1 --format table
   ```

2. **Verify you're not in quiet mode**:
   ```bash
   # Don't use --quiet if you want to see output:
   instancepedia list --region us-east-1  # Good
   instancepedia list --region us-east-1 --quiet  # Suppresses progress
   ```

3. **Check if output is redirected**:
   ```bash
   # If using --output, file is written instead of stdout:
   instancepedia list --region us-east-1 --format csv --output out.csv
   # Check the file:
   cat out.csv
   ```

4. **Look for errors in stderr**:
   ```bash
   instancepedia list --region us-east-1 2>&1
   ```

### Problem: JSON output is invalid

**Symptoms:**
- `jq` fails to parse output
- JSON linters show errors

**Solutions:**

1. **Ensure using `--format json`**:
   ```bash
   instancepedia list --region us-east-1 --format json
   ```

2. **Use `--quiet` to suppress progress messages**:
   ```bash
   # Progress messages go to stderr, but to be safe:
   instancepedia list --region us-east-1 --format json --quiet | jq
   ```

3. **Check for error messages mixed in output**:
   ```bash
   # Separate stdout and stderr:
   instancepedia list --region us-east-1 --format json 2>/dev/null | jq
   ```

4. **Validate JSON**:
   ```bash
   instancepedia list --region us-east-1 --format json | python -m json.tool
   ```

### Problem: CSV output has incorrect formatting

**Symptoms:**
- CSV shows extra quotes or escaping
- Columns misaligned in spreadsheet

**Solutions:**

1. **Save to file instead of stdout**:
   ```bash
   instancepedia list --region us-east-1 --format csv --output out.csv
   ```

2. **Check for special characters in data**:
   - Instance types shouldn't have special chars
   - But descriptions might

3. **Use proper CSV parser**:
   - Excel, Google Sheets, LibreOffice Calc
   - Or Python pandas: `pd.read_csv('out.csv')`

4. **Verify file encoding**:
   ```bash
   file out.csv  # Should show UTF-8 or ASCII
   ```

---

## Filter Issues

### Problem: No GPU instances found with filter

**Symptoms:**
- Filtering for GPU instances returns empty results
- `--processor-family` or GPU filters show nothing

**Solutions:**

1. **Check region availability**:
   - Not all GPU instances are available in every region
   - Try `us-east-1` or `us-west-2` which have the most GPU options
   ```bash
   instancepedia list --region us-east-1 --family g5
   instancepedia list --region us-east-1 --family p4d
   ```

2. **Use correct family prefixes**:
   - GPU instances: `g4dn`, `g5`, `g6`, `p3`, `p4d`, `p5`
   - Inference: `inf1`, `inf2`
   - Training: `trn1`
   ```bash
   instancepedia search gpu --region us-east-1
   ```

3. **Check if combining incompatible filters**:
   ```bash
   # This won't work - GPU instances aren't ARM/Graviton:
   instancepedia list --processor-family graviton --family g5  # Empty!

   # This works:
   instancepedia list --family g5 --region us-east-1
   ```

### Problem: Price filters not working as expected

**Symptoms:**
- `--min-price` or `--max-price` filters return unexpected results
- Some instances missing from filtered results

**Solutions:**

1. **Enable pricing data first**:
   - Price filters only work when `--include-pricing` is used
   - Instances without pricing data are NOT filtered out (to avoid hiding them)
   ```bash
   # Include pricing to enable price filtering:
   instancepedia list --include-pricing --max-price 0.10 --region us-east-1
   ```

2. **Understand what's included**:
   - Price filters use **on-demand** hourly pricing
   - Instances with N/A pricing are kept (not filtered)
   - This prevents hiding instances due to pricing API issues

3. **Check the price range is reasonable**:
   ```bash
   # Very small instances start around $0.005/hr
   # Large instances can be $20+/hr
   instancepedia list --include-pricing --min-price 0.01 --max-price 0.10
   ```

### Problem: Storage type filter not matching expected instances

**Symptoms:**
- `--storage-type ebs-only` or `--storage-type instance-store` returns wrong results

**Solutions:**

1. **Understand the difference**:
   - `ebs-only`: Instances with NO local instance store (most common)
   - `instance-store`: Instances WITH local NVMe or SSD storage
   ```bash
   # EBS-only instances (t3, m5, c5, etc.):
   instancepedia list --storage-type ebs-only --region us-east-1

   # Instances with local storage (i3, d2, etc.):
   instancepedia list --storage-type instance-store --region us-east-1
   ```

2. **Combine with NVMe filter for high-performance storage**:
   ```bash
   # NVMe instance store (fastest local storage):
   instancepedia list --storage-type instance-store --nvme required
   ```

### Problem: Processor family filter missing instances

**Symptoms:**
- `--processor-family intel` missing some Intel instances
- AMD or Graviton filter not matching expected types

**Solutions:**

1. **Understand the detection logic**:
   - **Intel**: Default for x86_64 instances without 'a' suffix
   - **AMD**: Instances with 'a' suffix (e.g., `m5a`, `c5a`, `r6a`)
   - **Graviton**: ARM64 architecture instances (e.g., `m6g`, `c7g`, `t4g`)

2. **Some edge cases**:
   ```bash
   # Metal instances may not match processor filters:
   instancepedia list --family m5 --processor-family intel

   # Graviton includes all ARM instances:
   instancepedia list --processor-family graviton  # t4g, m6g, c7g, etc.
   ```

3. **Verify with show command**:
   ```bash
   instancepedia show m5a.large --region us-east-1
   # Check "Processor" field to verify architecture
   ```

### Problem: Network performance filter too broad/narrow

**Symptoms:**
- `--network-performance` returns too many or too few results

**Solutions:**

1. **Understand the tiers**:
   - `low`: Up to 5 Gbps (small instances)
   - `moderate`: 5-12 Gbps (medium instances)
   - `high`: 12-25 Gbps (large instances)
   - `very-high`: 25+ Gbps (xlarge and metal instances)

2. **Combine with other filters for precision**:
   ```bash
   # High network + compute optimized:
   instancepedia list --network-performance very-high --family c6i

   # Moderate network + memory optimized:
   instancepedia list --network-performance moderate --family r6i
   ```

### Problem: Free tier filter shows nothing

**Symptoms:**
- `--free-tier-only` returns empty results

**Solutions:**

1. **Only t2.micro and t3.micro are free tier eligible**:
   ```bash
   instancepedia list --free-tier-only --region us-east-1
   # Should show t2.micro and t3.micro only
   ```

2. **Check region**:
   - Free tier is available in most regions
   - But instance availability varies
   ```bash
   instancepedia list --free-tier-only --region eu-west-1
   ```

---

## Cache Issues

### Problem: Cache files growing too large

**Symptoms:**
- `~/.instancepedia/cache/` directory is large
- Many old cache files

**Solutions:**

1. **Check cache size**:
   ```bash
   instancepedia cache stats
   # Look at "Total size" and "Total entries"
   ```

2. **Clear cache**:
   ```bash
   # Clear all cache:
   instancepedia cache clear --force

   # Clear specific region:
   instancepedia cache clear --region us-east-1 --force

   # Clear specific instance type:
   instancepedia cache clear --instance-type t3.micro --force
   ```

3. **Let cache TTL handle cleanup**:
   - Cache entries expire after 4 hours
   - Expired entries are cleaned up automatically

4. **Manually delete old files**:
   ```bash
   find ~/.instancepedia/cache/ -type f -mtime +7 -delete
   # Deletes files older than 7 days
   ```

### Problem: Cache corruption or invalid data

**Symptoms:**
- Errors reading cache files
- `instancepedia cache stats` fails
- Prices showing as unexpected values

**Solutions:**

1. **Clear and rebuild cache**:
   ```bash
   rm -rf ~/.instancepedia/cache/
   instancepedia --tui  # Will rebuild cache
   ```

2. **Check file permissions**:
   ```bash
   ls -la ~/.instancepedia/cache/
   # Should be readable/writable by your user
   ```

3. **Check disk space**:
   ```bash
   df -h ~  # Ensure you have available space
   ```

4. **Verify JSON files are valid**:
   ```bash
   find ~/.instancepedia/cache/ -name "*.json" -exec python -m json.tool {} \; > /dev/null
   # Will show which files are corrupted
   ```

### Problem: Cache not being used (always fetching from AWS)

**Symptoms:**
- Every run is slow
- Cache stats show no hits
- "⏳ Loading prices..." every time

**Solutions:**

1. **Check if cache is enabled**:
   - Cache is enabled by default
   - No configuration needed

2. **Verify cache directory exists**:
   ```bash
   ls -la ~/.instancepedia/cache/
   ```

3. **Check cache write permissions**:
   ```bash
   touch ~/.instancepedia/cache/test.txt
   rm ~/.instancepedia/cache/test.txt
   ```

4. **Look for error messages**:
   ```bash
   instancepedia --tui --debug
   # Check debug log for cache-related errors
   ```

5. **Verify cache files are being created**:
   ```bash
   # Before:
   ls ~/.instancepedia/cache/ | wc -l

   # Run instancepedia
   instancepedia list --region us-east-1 --include-pricing --quiet

   # After:
   ls ~/.instancepedia/cache/ | wc -l  # Should be higher
   ```

---

## Network and Timeout Issues

### Problem: Connection timeouts

**Symptoms:**
```
ConnectTimeoutError: Connect timeout on endpoint URL
ReadTimeoutError: Read timeout on endpoint URL
```

**Solutions:**

1. **Increase timeout values**:
   ```bash
   export INSTANCEPEDIA_AWS_CONNECT_TIMEOUT=30
   export INSTANCEPEDIA_AWS_READ_TIMEOUT=120
   export INSTANCEPEDIA_PRICING_READ_TIMEOUT=180
   instancepedia --tui
   ```

2. **Check your network connection**:
   ```bash
   ping 8.8.8.8
   curl -I https://ec2.us-east-1.amazonaws.com
   ```

3. **Try a different region** (if specific region is timing out):
   ```bash
   instancepedia --tui --region us-west-2
   ```

4. **Use a VPN if behind firewall**:
   - Some corporate firewalls block AWS API access
   - Try connecting via VPN

5. **Wait and retry**:
   - AWS APIs occasionally have temporary issues
   - Wait a few minutes and try again

### Problem: SSL certificate verification failures

**Symptoms:**
```
SSLError: certificate verify failed
```

**Solutions:**

1. **Update certificates**:
   ```bash
   # macOS:
   /Applications/Python\ 3.x/Install\ Certificates.command

   # Linux:
   sudo update-ca-certificates

   # Or:
   pip install --upgrade certifi
   ```

2. **Check system time**:
   ```bash
   date
   # Ensure system time is correct
   ```

3. **Temporarily bypass SSL verification** (not recommended for production):
   ```bash
   export PYTHONHTTPSVERIFY=0
   instancepedia --tui
   ```

### Problem: Rate limiting errors

**Symptoms:**
```
ThrottlingException: Rate exceeded
TooManyRequestsException
```

**Solutions:**

1. **Wait and retry**:
   - Application has automatic retry with exponential backoff
   - Usually resolves itself

2. **Reduce concurrency** (in TUI mode pricing fetch):
   - Automatic retry uses lower concurrency (3 instead of 10)
   - Press `R` to retry with reduced load

3. **Clear cache and try again**:
   ```bash
   instancepedia cache clear --force
   instancepedia --tui
   # Fresh cache may reduce API calls
   ```

4. **Space out your requests** (CLI mode):
   ```bash
   # Instead of rapid-fire requests:
   for instance in t3.micro t3.small t3.medium; do
     instancepedia pricing $instance --region us-east-1
     sleep 2  # Wait between requests
   done
   ```

---

## Getting Help

If you've tried the solutions above and still have issues:

### 1. Check GitHub Issues

Search existing issues: https://github.com/pfrederiksen/instancepedia/issues

### 2. Enable Debug Mode

```bash
instancepedia --tui --debug
```

Watch the debug pane for detailed error messages and stack traces.

### 3. Collect Information

When reporting an issue, include:
- **Version**: `pip show instancepedia | grep Version`
- **Python version**: `python --version`
- **Operating system**: `uname -a` (Linux/macOS) or `ver` (Windows)
- **Error message**: Full error text or screenshot
- **Steps to reproduce**: Exact commands you ran
- **Debug logs**: If available from `--debug` mode

### 4. Create a GitHub Issue

https://github.com/pfrederiksen/instancepedia/issues/new

Include all information from step 3.

### 5. Workarounds

While waiting for a fix:

**For TUI issues:**
- Try CLI mode: `instancepedia list --region us-east-1 --format table`
- Use AWS Console as fallback

**For pricing issues:**
- Use AWS Pricing Calculator: https://calculator.aws/
- Check AWS documentation: https://aws.amazon.com/ec2/pricing/

**For authentication issues:**
- Verify with AWS CLI: `aws ec2 describe-instance-types --max-results 1`
- Check IAM permissions in AWS Console

---

## Common Environment-Specific Issues

### macOS

**Problem**: Terminal colors don't work in default Terminal.app

**Solution**: Use iTerm2 or enable color support:
```bash
export CLICOLOR=1
export TERM=xterm-256color
```

### Windows

**Problem**: TUI doesn't render correctly in Command Prompt

**Solution**: Use Windows Terminal or PowerShell:
```powershell
# Install Windows Terminal from Microsoft Store
# Then run:
instancepedia --tui
```

**Problem**: UTF-8 encoding issues

**Solution**:
```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
instancepedia --tui
```

### Linux

**Problem**: Missing locale support

**Solution**:
```bash
sudo locale-gen en_US.UTF-8
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
```

**Problem**: Permission denied accessing cache directory

**Solution**:
```bash
mkdir -p ~/.instancepedia/cache
chmod 755 ~/.instancepedia
chmod 755 ~/.instancepedia/cache
```

---

## Quick Reference: Debug Commands

```bash
# Check version
pip show instancepedia

# Check AWS credentials
aws sts get-caller-identity

# List available regions
instancepedia regions

# Check cache status
instancepedia cache stats

# Clear all cache
instancepedia cache clear --force

# Run with debug mode
instancepedia --tui --debug

# Test specific instance
instancepedia show t3.micro --region us-east-1

# Test pricing separately
instancepedia pricing t3.micro --region us-east-1

# Export logs (debug mode output)
instancepedia --tui --debug 2> debug.log
```

---

**Last Updated**: January 2026
**Version Compatibility**: v0.5.0+
