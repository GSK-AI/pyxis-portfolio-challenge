# Copy Node.js from Program Files to a directory without spaces
$sourcePath = "C:\Program Files\nodejs"
$destinationPath = "C:\nodejs_copy"
Write-Host "Copying Node.js from '$sourcePath' to '$destinationPath'..."

# Create destination directory if it doesn't exist
if (-Not (Test-Path -Path $destinationPath)) {
    New-Item -ItemType Directory -Force -Path $destinationPath | Out-Null
    Write-Host "Created destination directory: $destinationPath"
}

# Copy all files and folders
Copy-Item -Path "$sourcePath\*" -Destination $destinationPath -Recurse -Force
Write-Host "Copied Node.js files to $destinationPath"

# Verify the copy was successful - check both node.exe AND npm.cmd
if (Test-Path -Path "$destinationPath\node.exe") {
    Write-Host "Successfully copied node.exe"
    $nodeVersion = & "$destinationPath\node.exe" -v
    Write-Host "Node.js version: $nodeVersion"
} else {
    Write-Host "Failed to copy node.exe"
    exit 1
}

# Explicitly verify npm.cmd exists
if (Test-Path -Path "$destinationPath\npm.cmd") {
    Write-Host "Successfully copied npm.cmd"
} else {
    Write-Host "Failed to copy npm.cmd - this will cause failures in the runner stage"
    
    # Check if npm.cmd exists in the source
    if (Test-Path -Path "$sourcePath\npm.cmd") {
        Write-Host "npm.cmd exists in source but failed to copy"
    } else {
        Write-Host "npm.cmd does NOT exist in source directory"
    }
    
    # List all files in both directories for debugging
    Write-Host "Source directory contents:"
    Get-ChildItem -Path $sourcePath | ForEach-Object { Write-Host $_.Name }
    
    Write-Host "Destination directory contents:"
    Get-ChildItem -Path $destinationPath | ForEach-Object { Write-Host $_.Name }
    
    exit 1
}

# Verify node is accessible
try {
    $nodeVersion = & "$destinationPath\node.exe" -v
    Write-Host "Node version: $nodeVersion"
    $npmVersion = & "$destinationPath\npm.cmd" -v
    Write-Host "NPM version: $npmVersion"
}
catch {
    Write-Host "Error executing Node.js: $_"
    exit 1
}

# Update system PATH to include the new location
[System.Environment]::SetEnvironmentVariable('Path', "$destinationPath;$env:Path", 'Process')
Write-Host "Updated PATH: $env:Path"

# List all critical files one more time to confirm they're ready for the runner stage
Write-Host "Final verification of critical files:"
foreach ($file in @("node.exe", "npm.cmd", "npx.cmd")) {
    if (Test-Path -Path "$destinationPath\$file") {
        Write-Host "$file - OK"
    } else {
        Write-Host "$file - MISSING"
        exit 1
    }
}