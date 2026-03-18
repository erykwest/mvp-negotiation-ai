param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("company", "candidate", "admin")]
    [string]$Role,

    [int]$Port
)

$appMap = @{
    company = "company_app.py"
    candidate = "candidate_app.py"
    admin = "admin_app.py"
}

$defaultPorts = @{
    company = 8501
    candidate = 8502
    admin = 8503
}

if (-not $Port) {
    $Port = $defaultPorts[$Role]
}

$python = ".\.venv\Scripts\python.exe"
$script = $appMap[$Role]

& $python -m streamlit run $script --server.port $Port
