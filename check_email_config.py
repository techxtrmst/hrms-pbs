import os
from pathlib import Path

print("=" * 60)
print("ENVIRONMENT VARIABLE DIAGNOSTIC")
print("=" * 60)

# Check if .env file exists
env_file = Path('.env')
if env_file.exists():
    print(f"✅ .env file found at: {env_file.absolute()}")
    print(f"✅ File size: {env_file.stat().st_size} bytes")
    print()
    
    # Read and display .env content (masking password)
    print("📄 .env file contents:")
    print("-" * 60)
    with open('.env', 'r') as f:
        lines = f.readlines()
        for i, line in enumerate(lines, 1):
            line = line.rstrip()
            if 'PETABYTZ_HR_EMAIL_PASSWORD' in line:
                # Mask the password
                if '=' in line:
                    key, value = line.split('=', 1)
                    if value and value.strip():
                        print(f"Line {i}: {key}=***HIDDEN*** (length: {len(value.strip())} chars)")
                    else:
                        print(f"Line {i}: {key}= ❌ EMPTY!")
                else:
                    print(f"Line {i}: {line} ❌ NO EQUALS SIGN!")
            elif line.strip() and not line.strip().startswith('#'):
                print(f"Line {i}: {line[:50]}...")
    print("-" * 60)
    print()
else:
    print("❌ .env file NOT found!")
    print()

# Check environment variable using os.environ
print("🔍 Checking os.environ:")
if 'PETABYTZ_HR_EMAIL_PASSWORD' in os.environ:
    pwd = os.environ['PETABYTZ_HR_EMAIL_PASSWORD']
    print(f"✅ Found in os.environ (length: {len(pwd)} chars)")
else:
    print("❌ NOT found in os.environ")
print()

# Try django-environ
print("🔍 Checking with django-environ:")
try:
    import environ
    env = environ.Env()
    
    # Read .env file
    env_file_path = Path('.env')
    if env_file_path.exists():
        environ.Env.read_env(str(env_file_path))
        print(f"✅ Read .env file from: {env_file_path.absolute()}")
    
    # Try to get the variable
    password = env('PETABYTZ_HR_EMAIL_PASSWORD', default='__NOT_FOUND__')
    
    if password == '__NOT_FOUND__':
        print("❌ PETABYTZ_HR_EMAIL_PASSWORD not found by django-environ")
    elif password == '':
        print("❌ PETABYTZ_HR_EMAIL_PASSWORD is EMPTY")
    else:
        print(f"✅ PETABYTZ_HR_EMAIL_PASSWORD found (length: {len(password)} chars)")
        print(f"✅ First 3 chars: {password[:3]}...")
        
except Exception as e:
    print(f"❌ Error with django-environ: {e}")

print()
print("=" * 60)
print("RECOMMENDATIONS:")
print("=" * 60)

# Check the .env file format
if env_file.exists():
    with open('.env', 'r') as f:
        content = f.read()
        
    if 'PETABYTZ_HR_EMAIL_PASSWORD' not in content:
        print("❌ PETABYTZ_HR_EMAIL_PASSWORD not found in .env file")
        print("   Add this line to .env:")
        print("   PETABYTZ_HR_EMAIL_PASSWORD=your-actual-password")
    elif 'PETABYTZ_HR_EMAIL_PASSWORD=' in content:
        # Check if it has a value
        for line in content.split('\n'):
            if line.strip().startswith('PETABYTZ_HR_EMAIL_PASSWORD='):
                value = line.split('=', 1)[1].strip()
                if not value:
                    print("❌ PETABYTZ_HR_EMAIL_PASSWORD is set but has NO VALUE")
                    print("   Update .env file:")
                    print("   PETABYTZ_HR_EMAIL_PASSWORD=your-actual-password")
                elif value in ['your-actual-password-here', 'your-hrms-petabytz-password']:
                    print("❌ PETABYTZ_HR_EMAIL_PASSWORD is set to EXAMPLE value")
                    print("   Update .env file with the REAL password:")
                    print("   PETABYTZ_HR_EMAIL_PASSWORD=actual-password")
                else:
                    print("✅ PETABYTZ_HR_EMAIL_PASSWORD appears to be set correctly")
                    print("   If emails still fail, the password might be incorrect")
                    print("   or you may need an app-specific password for Office 365")
