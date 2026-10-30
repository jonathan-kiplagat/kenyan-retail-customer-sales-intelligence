<#
.SYNOPSIS
    Run the project's SQL scripts with psql and save each output as evidence.

.DESCRIPTION
    Reads connection settings from the git-ignored .env file in the project root
    (PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE), runs each script in order,
    and writes the query results to milestone_4_sql/outputs/<script>.txt.

.EXAMPLE
    # From the project root:
    .\sql\run_sql.ps1                      # run all 7 scripts
    .\sql\run_sql.ps1 -Scripts 04_sales_analysis.sql
#>
param(
    [string[]]$Scripts = @(
        "01_create_tables.sql", "02_load_data.sql", "03_data_quality_checks.sql",
        "04_sales_analysis.sql", "05_customer_analysis.sql",
        "06_cohort_analysis.sql", "07_rfm_analysis.sql"),
    [string]$Psql = "C:\Program Files\PostgreSQL\18\bin\psql.exe"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# Load KEY=VALUE pairs from .env into this process's environment (psql reads PG* variables).
if (-not (Test-Path ".env")) { throw "Missing .env file in $root" }
Get-Content ".env" | Where-Object { $_ -match "^\s*[A-Z_]+\s*=" } | ForEach-Object {
    $name, $value = $_ -split "=", 2
    [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim(), "Process")
}

# Hide informational NOTICE messages (e.g. "drop cascades to ..."); warnings and errors still show.
$env:PGOPTIONS = "-c client_min_messages=warning"

$outDir = Join-Path $root "milestone_4_sql\outputs"
New-Item -ItemType Directory -Force $outDir | Out-Null

# Allow "-Scripts a.sql,b.sql" when called with powershell -File (arrives as one string).
$Scripts = $Scripts | ForEach-Object { $_ -split "," } | Where-Object { $_ }

foreach ($script in $Scripts) {
    $outFile = Join-Path $outDir ($script -replace "\.sql$", ".txt")
    Write-Host "Running $script ..."
    # -X: ignore personal psqlrc   -e: echo each query above its result
    # ON_ERROR_STOP: stop at the first error so failures are never hidden
    # cmd handles the redirection so psql's stderr is captured as plain text.
    cmd /c "`"$Psql`" -X -e -v ON_ERROR_STOP=1 -P pager=off -f `"sql\$script`" > `"$outFile`" 2>&1"
    if ($LASTEXITCODE -ne 0) {
        Get-Content $outFile -Tail 15
        throw "$script failed (exit code $LASTEXITCODE). See $outFile"
    }
    Write-Host "  OK -> milestone_4_sql\outputs\$(Split-Path $outFile -Leaf)"
}
