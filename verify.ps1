# verify.ps1 -- check the constitution with NEITHER PYTHON NOR A UNIX SHELL.
#
# WHY A THIRD ONE
#
#   constitution.py needs Python. verify.sh needs sh and awk, which a bare
#   Windows box does not have. Between them they still leave a machine where
#   the record cannot be checked at all, and "you need to install something
#   first" is exactly the dependency a record meant to outlive its machine
#   cannot afford.
#
#   PowerShell is on every Windows since 7. Python is not. So this is the
#   Windows-native witness, and with it the count is three independent
#   implementations of one check, in three languages, sharing no code:
#
#       constitution.py   Python, any platform
#       verify.sh         sh + awk + sha256sum, any Unix
#       verify.ps1        PowerShell, any Windows
#
#   Three witnesses is the same shape as triangulate.py's argument, applied to
#   the verifier rather than to the thing verified: agreement between
#   independent implementations is evidence, and a lone implementation
#   agreeing with itself is not. If any two of these disagree, the
#   disagreement is the finding. That has already happened once -- see the
#   note about the em dash in verify.sh -- and it was worth more than either
#   implementation would have been alone.
#
# USE
#   powershell -ExecutionPolicy Bypass -File verify.ps1
#   powershell -ExecutionPolicy Bypass -File verify.ps1 -Show
#
# Exit 0 matches, 1 differs, 2 could not run -- and 2 is never read as 0.

param([switch]$Show)

$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Anchor = Join-Path $Here "docs\CONSTITUTION_ANCHOR.json"

# Must match constitution.py PROTECTED and verify.sh BLOCKS.
$Protected = @(
  @{ File = "CONTRIBUTING.md";    Opens = "## Why it exists, and the one condition" },
  @{ File = "CONTRIBUTING.md";    Opens = "## What never changes" },
  @{ File = "docs\SUCCESSION.md"; Opens = "## Layer 4 - Continuation, not just preservation" }
)

function Get-Sha256Hex([byte[]]$Bytes) {
  $sha = [System.Security.Cryptography.SHA256]::Create()
  try {
    $h = $sha.ComputeHash($Bytes)
    # No -Join with a format operator here: PS 5.1 needs the explicit loop.
    $s = ""
    foreach ($b in $h) { $s += $b.ToString("x2") }
    return $s
  } finally { $sha.Dispose() }
}

function Get-HeadingDepth([string]$Line) {
  $n = 0
  while ($n -lt $Line.Length -and $Line[$n] -eq '#') { $n++ }
  return $n
}

function Get-Canon([string]$S) {
  # An em dash and an en dash mean the same heading to a reader, so they must
  # mean the same heading here.
  return $S.Replace(" $([char]0x2014) ", " - ").Replace(" $([char]0x2013) ", " - ")
}

function Get-Block([string]$Path, [string]$Opens) {
  if (-not (Test-Path -LiteralPath $Path)) { return $null }
  # Read as UTF-8 explicitly. The default encoding differs between PowerShell
  # versions, and a hash computed over the wrong decoding is a wrong answer
  # delivered confidently.
  $text = [System.IO.File]::ReadAllText($Path, [System.Text.Encoding]::UTF8)
  $lines = $text.Replace("`r`n", "`n").Split("`n")
  $target = Get-Canon $Opens
  $buf = New-Object System.Collections.Generic.List[string]
  $inb = $false
  $depth = 0
  foreach ($raw in $lines) {
    $line = $raw.TrimEnd()
    if (-not $inb) {
      if ((Get-Canon $line) -eq $target) {
        $inb = $true
        $depth = Get-HeadingDepth $line
        # The CANONICAL heading is hashed, not the file's spelling of it --
        # see the same note in verify.sh. Changing a dash is typography, not
        # an amendment.
        $buf.Add($Opens) | Out-Null
      }
      continue
    }
    if ($line -match '^#+\s' -and (Get-HeadingDepth $line) -le $depth) { break }
    $buf.Add($line) | Out-Null
  }
  if ($buf.Count -eq 0) { return $null }
  $s = 0
  $e = $buf.Count - 1
  while ($s -le $e -and $buf[$s] -eq "") { $s++ }
  while ($e -ge $s -and $buf[$e] -eq "") { $e-- }
  if ($e -lt $s) { return $null }
  return ($buf[$s..$e] -join "`n")
}

Write-Output ""
Write-Output "  CONSTITUTION -- verified with NEITHER PYTHON NOR A UNIX SHELL"
Write-Output "  --------------------------------------------------------------"

$digests = @()
$missing = 0
foreach ($p in $Protected) {
  $path = Join-Path $Here $p.File
  $body = Get-Block $path $p.Opens
  if ($null -eq $body) {
    Write-Output ("    MISSING  {0} :: {1}" -f $p.File, $p.Opens)
    $missing++
    continue
  }
  $d = Get-Sha256Hex ([System.Text.Encoding]::UTF8.GetBytes($body))
  if ($Show) { Write-Output ("    {0}  {1}" -f $d.Substring(0, 16), $p.Opens) }
  $digests += $d
}

if ($missing -gt 0) {
  Write-Output ""
  Write-Output ("  {0} protected block(s) could not be read." -f $missing)
  Write-Output "  A block that has been DELETED is the most serious result there"
  Write-Output "  is: an amendment that leaves no trace in what remains."
  exit 1
}

$joined = "covenant-constitution-v1" + (($digests | Sort-Object) -join "")
$root = Get-Sha256Hex ([System.Text.Encoding]::UTF8.GetBytes($joined))

Write-Output ""
Write-Output ("    computed  {0}" -f $root)

if (-not (Test-Path -LiteralPath $Anchor)) {
  Write-Output "    anchor    NOT FOUND at docs\CONSTITUTION_ANCHOR.json"
  Write-Output ""
  Write-Output "  Could not compare. This is not a pass."
  exit 2
}

# Pull the hash out without a JSON parser, so this works on PowerShell 5.1
# where ConvertFrom-Json behaves differently, and on a truncated file.
$anchorText = [System.IO.File]::ReadAllText($Anchor, [System.Text.Encoding]::UTF8)
$m = [regex]::Match($anchorText, '"hash"\s*:\s*"([0-9a-f]{64})"')
if (-not $m.Success) {
  Write-Output "    anchored  <no hash found>"
  Write-Output ""
  Write-Output "  Could not compare. This is not a pass."
  exit 2
}
$anchored = $m.Groups[1].Value
Write-Output ("    anchored  {0}" -f $anchored)
Write-Output ""

if ($root -eq $anchored) {
  Write-Output "  MATCH. The rules that bind the operator are the ones published."
  Write-Output ""
  Write-Output "  What this does and does not prove: the text here is the text the"
  Write-Output "  anchor names. It cannot prove the anchor was not changed together"
  Write-Output "  with the text -- for that, compare against a clone nobody on this"
  Write-Output "  machine can reach. That limit is in CONSTITUTION.md III and no"
  Write-Output "  amount of local checking removes it."
  exit 0
}

Write-Output "  DIFFERENT. The protected text does not hash to the published anchor."
Write-Output ""
Write-Output "  Not automatically wrong -- amendment is allowed. Amendment in"
Write-Output "  SILENCE is not, and this is the noise. Either the rules changed and"
Write-Output "  the anchor was not republished, or something changed that nobody"
Write-Output "  intended. Find out which before doing anything else."
exit 1
