# WeasyPrint Deployment Fix

## Problem
WeasyPrint was not working after deployment because the Docker container was missing required system libraries.

## Root Cause
WeasyPrint requires several system-level dependencies that must be installed in the Docker image:
- **Pango** - Text layout and rendering
- **Cairo** - 2D graphics library
- **GDK-Pixbuf** - Image loading library
- **libffi** - Foreign function interface
- **shared-mime-info** - MIME type detection
- **fonts-liberation** - Free fonts for better rendering

## Solution Applied
Updated `Dockerfile` to include all required WeasyPrint dependencies in the runtime stage:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-liberation \
    wkhtmltopdf \
    curl \
    && rm -rf /var/lib/apt/lists/*
```

## How to Deploy the Fix

1. **Commit the changes:**
   ```bash
   git add Dockerfile
   git commit -m "Fix WeasyPrint deployment: Add required system dependencies"
   git push origin staging
   ```

2. **Rebuild the Docker image:**
   The deployment pipeline will automatically rebuild the image with the new dependencies.

3. **Verify the fix:**
   - Try generating a payslip PDF
   - Check the logs for any WeasyPrint errors
   - Confirm PDFs are being created successfully

## Testing Locally with Docker

If you want to test the fix locally before deploying:

```bash
# Build the image
docker build -t hrms-pbs:test .

# Run the container
docker run -p 8000:8000 hrms-pbs:test

# Test payslip generation
```

## Alternative: Fallback to xhtml2pdf

The application already has a fallback mechanism using `xhtml2pdf` if WeasyPrint fails. However, WeasyPrint produces better quality PDFs with:
- Better CSS support
- More accurate rendering
- Better font handling
- Proper page breaks

## Common WeasyPrint Errors and Solutions

### Error: "cannot load library 'gobject-2.0-0'"
**Solution:** Install `libgobject-2.0-0` (included in our fix)

### Error: "cannot load library 'pango-1.0-0'"
**Solution:** Install `libpango-1.0-0` (included in our fix)

### Error: "Failed to load font"
**Solution:** Install `fonts-liberation` or other font packages (included in our fix)

### Error: "OSError: cannot load library"
**Solution:** Ensure all Cairo and Pango libraries are installed (included in our fix)

## Image Size Impact

Adding these dependencies will increase the Docker image size by approximately:
- **~15-20 MB** for the additional libraries
- This is acceptable given the improved PDF quality

## Notes

- The fix applies to both staging and production environments
- No code changes were needed, only infrastructure updates
- The application will automatically use WeasyPrint once the dependencies are available
- If WeasyPrint still fails, the app gracefully falls back to xhtml2pdf
