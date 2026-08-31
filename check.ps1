# check.ps1 -- ONE command that checks everything a stranger can check.
#
# The Windows twin of check.sh, and deliberately the same shape: same five
# checks, same exit codes, same refusal to round a skipped check up to a
# passed one. A reader on Windows with no Python and no Unix shell still
# gets a real result, because verify.ps1 needs neither.
#
# Why the two exist separately rather than one calling the other: a reader
# who has to install something before the check runs mostly does not run
# the check. The only event that changes anything for this project is
# somebody independent running it, so the cost of that event is the number
# worth minimising.
#
# USE:  powershell -ExecutionPolicy Bypass -File check.ps1   (Windows)
#       pwsh -File check.ps1                                 (Linux, macOS)
# EXIT: 0 everything that could run agreed. 1 something disagreed.
#       2 nothing could be checked at all.
# LICENCE: public domain.

Set-Location -Path $PSScriptRoot

$pass = 0; $fail = 0; $skip = 0

# Resolve the running host by process, which works in Windows
# PowerShell 5.1 and in PowerShell Core alike. The fallback exists
# for hosts that do not report a path, and prefers pwsh because that
# is the only one present off Windows.
$PSHost = [System.Diagnostics.Process]::GetCurrentProcess().Path
if (-not $PSHost) {
    $g = Get-Command pwsh -ErrorAction SilentlyContinue
    if (-not $g) { $g = Get-Command powershell -ErrorAction SilentlyContinue }
    if ($g) { $PSHost = $g.Source }
}
$VerifyPs1 = Join-Path $PSScriptRoot "verify.ps1"

# The leading comma is load-bearing. PowerShell unrolls a one-element array
# on return, so a single match came back as a bare string and $h[0] indexed
# its first CHARACTER: the conformance root printed as "9". It passed every
# guard, because a string reports .Count of 1. Measured, not theorised --
# the first run of this script printed that 9.
#
# IsRoot below is the structural fix. Length is checked before anything is
# printed as a hash, so a truncation can never be shown as a root again.
function Hashes([string]$text) {
    $m = [regex]::Matches($text, '[0-9a-f]{64}')
    $out = @()
    foreach ($x in $m) { $out += $x.Value }
    return ,$out
}

function IsRoot($v) { return ($v -is [string]) -and ($v.Length -eq 64) }

# ------------------------------------------------------------------ runtime
$py = $null
foreach ($c in @('python', 'python3', 'py')) {
    $g = Get-Command $c -ErrorAction SilentlyContinue
    if ($g) { $py = $g.Source; break }
}

$pyLabel = 'NONE'
if ($py) { $pyLabel = Split-Path $py -Leaf }

""
"  COVENANT -- independent check, one command"
"  =========================================="
""
"  runtimes   $($PSVersionTable.PSEdition) PowerShell $($PSVersionTable.PSVersion) | python $pyLabel"
""

# --------------------------------------------------- 1+2. the constitution
#
# Two programs sharing no code, hashing the same protected text. What is
# under test is that they AGREE, so neither is compared against a number
# written down in this file. A test that checks a program against its own
# stored constant proves the constant, and a single commit can change both.

$psHash = ''
$pyHash = ''

if (Test-Path 'verify.ps1') {
    # The host this script is ALREADY running in, not a hardcoded
    # `powershell` -- which does not exist on Linux or macOS, where the
    # host is `pwsh`. Spawning a different PowerShell than the one
    # interpreting this file was never right; it only ever worked
    # because Windows has exactly one.
    $out = (& $PSHost -NoProfile -ExecutionPolicy Bypass -File $VerifyPs1 2>$null) -join "`n"
    $rc = $LASTEXITCODE
    $h = Hashes $out
    if ($rc -eq 0 -and $h.Count -ge 2 -and (IsRoot $h[0]) -and $h[0] -eq $h[1]) {
        $psHash = $h[0]
        "  [1] constitution, NO python NO shell   verify.ps1"
        "      $psHash"
    } else {
        "  [1] constitution, NO python NO shell   MISMATCH (exit $rc)"
        if ($h.Count -ge 1) { "      computed  $($h[0])" }
        if ($h.Count -ge 2) { "      anchored  $($h[1])" }
        "      The text on disk is not the text the anchor names."
        $fail++
    }
} else {
    "  [1] constitution, NO python NO shell   SKIPPED -- verify.ps1 absent"
    $skip++
}

if ($py -and (Test-Path 'constitution.py')) {
    $out = (& $py constitution.py verify 2>$null) -join "`n"
    $rc = $LASTEXITCODE
    $h = Hashes $out
    if ($rc -eq 0 -and $h.Count -ge 2 -and (IsRoot $h[0]) -and $h[0] -eq $h[1]) {
        $pyHash = $h[0]
        "  [2] constitution, python              constitution.py verify"
        "      $pyHash"
    } else {
        "  [2] constitution, python              MISMATCH (exit $rc)"
        if ($h.Count -ge 1) { "      anchored  $($h[0])" }
        if ($h.Count -ge 2) { "      current   $($h[1])" }
        $fail++
    }
} else {
    "  [2] constitution, python              SKIPPED -- no python found"
    $skip++
}

if ($psHash -and $pyHash) {
    ""
    if ($psHash -eq $pyHash) {
        "      -> TWO IMPLEMENTATIONS SHARING NO CODE AGREE."
        "         An amendment would have to alter both to pass unseen."
        $pass += 2
    } else {
        "      -> DISAGREE. This is a real finding, and the project would"
        "         rather have it than not. Please open an issue with both"
        "         hashes and your platform."
        $fail++
    }
} elseif ($psHash -or $pyHash) {
    ""
    "      -> only ONE implementation ran, so agreement was not tested."
    "         A single verifier checks the text; it cannot check itself."
    $pass++
}
""

# ------------------------------------------------------ 3. conformance root
if ($py -and (Test-Path 'conformance.py')) {
    $out = (& $py conformance.py 2>$null) -join "`n"
    $rc = $LASTEXITCODE
    $h = Hashes $out
    if ($rc -eq 0 -and $h.Count -ge 1 -and (IsRoot $h[0])) {
        "  [3] conformance root                  11 vectors, behaviour not prose"
        "      $($h[0])"
        "      NOT CROSS-CHECKED: no second implementation exists yet."
        "      This is the number an independent build must reproduce, in"
        "      any language, sharing none of this code. Reproducing it is"
        "      the single most useful thing a reader of this repository"
        "      can do, and it needs nobody's permission."
        $pass++
    } else {
        "  [3] conformance root                  FAIL (exit $rc)"
        $fail++
    }
} else {
    "  [3] conformance root                  SKIPPED -- no python found"
    "      unchecked: whether this build agrees with any other."
    $skip++
}
""

# --------------------------------------- 4. dissent survives composition
#
# scale.py exits NON-ZERO on success. A dissent three levels down reaching
# the top is the property being demonstrated, and the exit code is how it
# reports it. Zero here would mean the disagreement vanished on the way up,
# which is the failure the mechanism exists to prevent -- so a wrapper that
# called non-zero a failure would report the healthy case as broken.

if ($py -and (Test-Path 'scale.py')) {
    & $py scale.py 2>$null | Out-Null
    $rc = $LASTEXITCODE
    if ($rc -ne 0) {
        "  [4] dissent survives composition      exit $rc, which is the PASS"
        "      A single node disagreed three levels down and the federation"
        "      reports it. The obvious implementation forwards the majority"
        "      and the dissent disappears at exactly the scale where"
        "      somebody would have acted on it."
        $pass++
    } else {
        "  [4] dissent survives composition      FAIL -- exit 0"
        "      The dissent was absorbed. That is the failure this mechanism"
        "      exists to prevent."
        $fail++
    }
} else {
    "  [4] dissent survives composition      SKIPPED -- no python found"
    $skip++
}
""

# ------------------------------------------------------- 5. what it survives
if ($py -and (Test-Path 'redundancy.py')) {
    $lines = @(& $py redundancy.py 2>$null)
    $rc = $LASTEXITCODE
    if ($rc -eq 0) {
        "  [5] redundancy floor                  redundancy.py, its own words:"
        $tail = @($lines | Where-Object { $_ -and $_.Trim() }) | Select-Object -Last 5
        foreach ($l in $tail) { "      | " + $l.TrimStart() }
        $pass++
    } else {
        "  [5] redundancy floor                  FAIL (exit $rc)"
        $fail++
    }
} else {
    "  [5] redundancy floor                  SKIPPED -- no python found"
    $skip++
}

# ------------------------------------------------------------------ verdict
""
"  ------------------------------------------------------------------"
"  $pass passed, $fail disagreed, $skip skipped."

if ($fail -gt 0) {
    ""
    "  SOMETHING DISAGREED, and that is worth more to this project than"
    "  agreement. github.com/LAWLESS1987/covenant/issues -- paste the"
    "  block above and your platform. A refutation is recorded publicly"
    "  here, the same as a confirmation."
    exit 1
}

if ($pass -eq 0) {
    ""
    "  NOTHING COULD BE CHECKED. That is a finding about this machine,"
    "  not about the repository."
    exit 2
}

""
if ($skip -gt 0) {
    "  Everything that COULD run agreed. $skip check(s) did not run, and"
    "  are listed above with what went unchecked -- a skipped check is"
    "  not a passed one, and this script will not round it up."
} else {
    "  Everything agreed."
}
""
"  What none of this proves: that the verifier and the thing it"
"  verifies are not both wrong. They ran on the same machine, from the"
"  same clone. The check that this cannot do is the one only a stranger"
"  can do -- clone it somewhere this machine cannot reach, run it"
"  again, and see whether the roots match. That is the whole ask."
""
exit 0
