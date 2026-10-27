# WRITTEN AGAINST THE 11-VECTOR SPEC WHOSE ROOT WAS 9d630fee...6f1c2784. PRESERVED AS THE RECORD OF THE 2026-08-31 SUFFICIENCY TEST, NOT KEPT CURRENT: IT IS EXPECTED TO FAIL AGAINST TODAY'S 23-VECTOR SPEC, AND PATCHING IT WOULD DESTROY THE INDEPENDENCE THAT MAKES IT EVIDENCE.
#
# conformance_check.ps1
#
# Independent PowerShell reimplementation of the Covenant conformance vectors,
# built ONLY from docs/CONFORMANCE_SPEC.json. No original implementation was
# read (see the "GAPS" comments below for everything the spec did not state).
#
# Run: powershell -NoProfile -ExecutionPolicy Bypass -File conformance_check.ps1
# Exits 0 if all vectors match and the computed root equals the published root.

[CmdletBinding()]
param(
    [string]$SpecPath
)

$ErrorActionPreference = 'Stop'

if (-not $SpecPath -or $SpecPath -eq '') {
    $base = $PSScriptRoot
    if (-not $base) { $base = (Get-Location).Path }
    $SpecPath = Join-Path $base 'docs\CONFORMANCE_SPEC.json'
}

# --------------------------------------------------------------------------
# GAPS: things the spec does NOT state, that I had to decide.
#
# Each "UNDERDETERMINED" gap was tested by building a variant of this script
# using the OTHER reading and re-running all 11 vectors. Every one of those
# variants also passed 11/11 and reproduced the published root -- so the
# vectors genuinely do not distinguish the readings, and two honest
# reimplementers can disagree on real inputs while both "conforming".
# --------------------------------------------------------------------------
#
# G1  UNDERDETERMINED - default quorum. Never stated. The vectors bound it to
#     exactly 2 for a 3-witness set (T.agree.one-silent: 2 answers -> AGREE;
#     T.unproven.too-few: 1 answer -> UNPROVEN). But "constant 2" and "simple
#     majority of the witnesses present" are identical at n=3 and diverge at
#     n=5 (2 vs 3). Verified: the majority variant also passes 11/11.
$DEFAULT_QUORUM = 2
#
# G2  CLOSED by the vectors, not a gap. Quorum counts ANSWERING witnesses, not
#     witnesses agreeing with the reference. The agreeing-count reading fails
#     T.diverged.three-way (1 holds A, quorum 2 -> UNPROVEN, but DIVERGED is
#     expected). Recorded because it was a live candidate reading.
#
# G3  UNDERDETERMINED - ordering of answered/outliers/silent. Never stated.
#     Here: ordinal ascending. Every vector's witnesses are named x,y,z in an
#     input order that already equals sorted order, so input-order is
#     indistinguishable. Verified: the input-order variant also passes 11/11.
#
# G4  UNDERDETERMINED - the reference root when no root holds a majority.
#     T.diverged.three-way (A,B,C) expects outliers ["y","z"], which names x's
#     root as the reference, but the spec never says how it was chosen. Here:
#     highest tally, ties broken by ordinal-lowest root value. Verified: a
#     variant that does no tallying at all and simply takes the root of the
#     ordinally-first answering witness also passes 11/11. So "majority" is
#     never actually exercised AS a majority anywhere in this suite.
#
# G5  UNSTATED - "clean" is never defined. Here: divergences == 0.
#
# G6  UNDERDETERMINED - "divergences" is never defined. Here: the number of
#     levels whose verdict is DIVERGED. "Total outlier witnesses summed over
#     the tree" gives 1 for both divergence vectors too. Verified: that
#     variant also passes 11/11. The two differ the moment one level has two
#     outliers, or two levels diverge.
#
# G7  UNTESTED - "speaks_upward" for an UNPROVEN level. Only AGREE (true) and
#     DIVERGED (false) appear. Here: only AGREE speaks upward.
#
# G8  UNTESTED - WHICH root an AGREEing level speaks upward. Every climb vector
#     uses the single root "A", so nothing pins this. Here: the agreed root.
#
# G9  UNSTATED - whether quorum applies to climb levels at all, and with what
#     default. Here: the same default of 2. Note the level "three" in
#     S.compose.height-invariant has only 2 children and must clear quorum.
#
# G10 UNSTATED - the tree node schema. There is no grammar; leaf-vs-level is
#     inferred from the presence of a "leaf" or "level" key in the sample data.
#     A climb whose root node is a bare leaf is undefined.
#
# G11 UNSTATED - the `roots` map is never actually needed. Comparing symbolic
#     names ("A" vs "B") gives identical results to resolving them to the
#     64-hex values first. A reimplementer cannot tell from the spec whether
#     resolution is required.
#
# G12 AMBIGUOUS WORDING (self-correcting) - "sha256 over spec". Read here as
#     the UTF-8 bytes of the `spec` field ("covenant-conformance-v1"). It could
#     equally have meant the whole spec file. This one is resolved by trying
#     it: the field reading reproduces the published root. Costs trial and
#     error, not correctness.
#
# G13 UNSTATED - canonical JSON details beyond "sorted keys, no spaces":
#     string encoding, non-ASCII escaping, number formatting, and the
#     collation used for both key sorting and "sorted by id". Not exercised
#     (all ids/keys are ASCII, all numbers are 0 or 1), so any reasonable
#     choice works here but would not be pinned for a richer vector set.

# --------------------------------------------------------------------------
# Canonical JSON (sorted keys, no spaces) - per the spec's "note" field
# --------------------------------------------------------------------------
$Utf8 = New-Object System.Text.UTF8Encoding($false)

function ConvertTo-OrdinalSorted {
    param([object[]]$Items)
    $a = [string[]]@($Items)
    [Array]::Sort($a, [System.StringComparer]::Ordinal)
    return ,$a
}

function ConvertTo-JsonStringLiteral {
    param([string]$s)
    $sb = New-Object System.Text.StringBuilder
    [void]$sb.Append('"')
    foreach ($ch in $s.ToCharArray()) {
        $code = [int]$ch
        if ($ch -eq '"') { [void]$sb.Append('\"') }
        elseif ($ch -eq '\') { [void]$sb.Append('\\') }
        elseif ($code -eq 8) { [void]$sb.Append('\b') }
        elseif ($code -eq 12) { [void]$sb.Append('\f') }
        elseif ($code -eq 10) { [void]$sb.Append('\n') }
        elseif ($code -eq 13) { [void]$sb.Append('\r') }
        elseif ($code -eq 9) { [void]$sb.Append('\t') }
        elseif ($code -lt 32) { [void]$sb.Append(('\u{0:x4}' -f $code)) }
        else { [void]$sb.Append($ch) }
    }
    [void]$sb.Append('"')
    return $sb.ToString()
}

function ConvertTo-CanonicalJson {
    param($Value)

    if ($null -eq $Value) { return 'null' }
    if ($Value -is [bool]) { if ($Value) { return 'true' } else { return 'false' } }
    if ($Value -is [string]) { return (ConvertTo-JsonStringLiteral $Value) }
    if ($Value -is [int] -or $Value -is [long] -or $Value -is [int16] -or $Value -is [byte]) {
        return $Value.ToString([System.Globalization.CultureInfo]::InvariantCulture)
    }
    if ($Value -is [double] -or $Value -is [decimal] -or $Value -is [single]) {
        return $Value.ToString('R', [System.Globalization.CultureInfo]::InvariantCulture)
    }
    if ($Value -is [System.Collections.IDictionary]) {
        $keys = ConvertTo-OrdinalSorted @($Value.Keys)
        $parts = @()
        foreach ($k in $keys) {
            $parts += ((ConvertTo-JsonStringLiteral $k) + ':' + (ConvertTo-CanonicalJson $Value[$k]))
        }
        return '{' + ($parts -join ',') + '}'
    }
    if ($Value -is [System.Management.Automation.PSCustomObject] -or $Value -is [psobject] -and -not ($Value -is [System.Collections.IEnumerable])) {
        $names = ConvertTo-OrdinalSorted @($Value.PSObject.Properties.Name)
        $parts = @()
        foreach ($n in $names) {
            $parts += ((ConvertTo-JsonStringLiteral $n) + ':' + (ConvertTo-CanonicalJson $Value.$n))
        }
        return '{' + ($parts -join ',') + '}'
    }
    if ($Value -is [System.Collections.IEnumerable]) {
        $parts = @()
        foreach ($item in $Value) { $parts += (ConvertTo-CanonicalJson $item) }
        return '[' + ($parts -join ',') + ']'
    }
    throw "ConvertTo-CanonicalJson: unsupported type $($Value.GetType().FullName)"
}

# --------------------------------------------------------------------------
# op: attest
# --------------------------------------------------------------------------
# Pairs: array of hashtables @{ name = <string>; root = <64-hex or $null> }
# $null root means the witness was silent (did not answer).
function Invoke-Attest {
    param([object[]]$Pairs, [int]$Quorum)

    $answered = @()
    $silent = @()
    foreach ($p in $Pairs) {
        if ($null -eq $p.root) { $silent += $p.name } else { $answered += $p.name }
    }

    $answeredSorted = ConvertTo-OrdinalSorted $answered
    $silentSorted = ConvertTo-OrdinalSorted $silent

    $outliers = @()
    $reference = $null
    $verdict = 'UNPROVEN'
    $agreed = $false

    if ($answeredSorted.Count -ge $Quorum) {
        # tally the answered roots; reference = highest tally,
        # ties broken by ordinal-lowest root value (G4)
        $tally = @{}
        foreach ($p in $Pairs) {
            if ($null -ne $p.root) {
                if ($tally.ContainsKey($p.root)) { $tally[$p.root] = $tally[$p.root] + 1 }
                else { $tally[$p.root] = 1 }
            }
        }
        $best = -1
        foreach ($k in (ConvertTo-OrdinalSorted @($tally.Keys))) {
            if ($tally[$k] -gt $best) { $best = $tally[$k]; $reference = $k }
        }

        $out = @()
        foreach ($p in $Pairs) {
            if ($null -ne $p.root -and $p.root -ne $reference) { $out += $p.name }
        }
        $outliers = ConvertTo-OrdinalSorted $out

        if ($outliers.Count -eq 0) { $verdict = 'AGREE'; $agreed = $true }
        else { $verdict = 'DIVERGED'; $agreed = $false }
    }
    else {
        # below quorum: nothing is adjudicated, so no outliers are named (G2)
        $reference = $null
    }

    return @{
        agreed     = $agreed
        answered   = $answeredSorted
        outliers   = $outliers
        silent     = $silentSorted
        verdict    = $verdict
        _reference = $reference
    }
}

# --------------------------------------------------------------------------
# op: climb
# --------------------------------------------------------------------------
function Resolve-RootSymbol {
    param($Symbol, $RootsMap)
    $names = @($RootsMap.PSObject.Properties.Name)
    if ($names -contains $Symbol) { return $RootsMap.$Symbol }
    throw "climb: unknown root symbol '$Symbol'"
}

function Invoke-ClimbNode {
    param($Node, $RootsMap, [int]$Quorum)

    $props = @($Node.PSObject.Properties.Name)

    if ($props -contains 'leaf') {
        return @{
            name        = [string]$Node.leaf
            root        = (Resolve-RootSymbol -Symbol $Node.root -RootsMap $RootsMap)
            divergences = 0
            verdict     = 'AGREE'
            speaks      = $true
        }
    }

    if (-not ($props -contains 'level')) { throw "climb: node is neither a leaf nor a level" }

    $pairs = @()
    $div = 0
    foreach ($child in @($Node.children)) {
        $r = Invoke-ClimbNode -Node $child -RootsMap $RootsMap -Quorum $Quorum
        $div += $r.divergences
        # a child that does not speak upward contributes silence, never its root
        $pairs += , @{ name = $r.name; root = $r.root }
    }

    $at = Invoke-Attest -Pairs $pairs -Quorum $Quorum
    if ($at.verdict -eq 'DIVERGED') { $div = $div + 1 }

    $speaks = ($at.verdict -eq 'AGREE')
    $spoken = $null
    if ($speaks) { $spoken = $at._reference }

    return @{
        name        = [string]$Node.level
        root        = $spoken
        divergences = $div
        verdict     = $at.verdict
        speaks      = $speaks
    }
}

# --------------------------------------------------------------------------
# Vector dispatch
# --------------------------------------------------------------------------
function Invoke-Vector {
    # NB: do not name this parameter $Input - that is a PowerShell automatic variable.
    param($VectorInput, $RootsMap)

    $op = $VectorInput.op

    if ($op -eq 'attest') {
        $quorum = $DEFAULT_QUORUM
        if (@($VectorInput.PSObject.Properties.Name) -contains 'quorum' -and $null -ne $VectorInput.quorum) {
            $quorum = [int]$VectorInput.quorum
        }
        $pairs = @()
        foreach ($n in @($VectorInput.roots.PSObject.Properties.Name)) {
            $sym = $VectorInput.roots.$n
            $val = $null
            if ($null -ne $sym) { $val = Resolve-RootSymbol -Symbol $sym -RootsMap $RootsMap }
            $pairs += , @{ name = $n; root = $val }
        }
        $r = Invoke-Attest -Pairs $pairs -Quorum $quorum
        return @{
            agreed   = $r.agreed
            answered = $r.answered
            outliers = $r.outliers
            silent   = $r.silent
            verdict  = $r.verdict
        }
    }

    if ($op -eq 'climb') {
        $quorum = $DEFAULT_QUORUM
        if (@($VectorInput.PSObject.Properties.Name) -contains 'quorum' -and $null -ne $VectorInput.quorum) {
            $quorum = [int]$VectorInput.quorum
        }
        $r = Invoke-ClimbNode -Node $VectorInput.tree -RootsMap $RootsMap -Quorum $quorum
        return @{
            clean         = ($r.divergences -eq 0)
            divergences   = [int]$r.divergences
            speaks_upward = $r.speaks
            verdict       = $r.verdict
        }
    }

    throw "unknown op '$op'"
}

# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
if (-not (Test-Path -LiteralPath $SpecPath)) { throw "spec not found: $SpecPath" }
$specText = Get-Content -LiteralPath $SpecPath -Raw
$spec = $specText | ConvertFrom-Json

Write-Host "spec file : $SpecPath"
Write-Host "spec id   : $($spec.spec)"
Write-Host ""

# id-sorted vectors (ordinal)
$byId = @{}
foreach ($v in @($spec.vectors)) { $byId[$v.id] = $v }
$ids = ConvertTo-OrdinalSorted @($byId.Keys)

$failed = @()
$passed = 0

foreach ($id in $ids) {
    $v = $byId[$id]
    $expectedJson = ConvertTo-CanonicalJson $v.expected
    $ok = $false
    $gotJson = ''
    try {
        $got = Invoke-Vector -VectorInput $v.input -RootsMap $spec.roots
        $gotJson = ConvertTo-CanonicalJson $got
        $ok = ($gotJson -ceq $expectedJson)
    }
    catch {
        $gotJson = "ERROR: $($_.Exception.Message)"
        $ok = $false
    }

    if ($ok) {
        $passed = $passed + 1
        Write-Host ("PASS  {0}" -f $id)
    }
    else {
        $failed += $id
        Write-Host ("FAIL  {0}" -f $id)
        Write-Host ("        expected: {0}" -f $expectedJson)
        Write-Host ("        got     : {0}" -f $gotJson)
    }
}

Write-Host ""
Write-Host ("vectors: {0}/{1} passed" -f $passed, $ids.Count)
Write-Host ""

# --------------------------------------------------------------------------
# Root: sha256 over spec, then for each vector sorted by id:
#   NUL, id, NUL, canonical JSON of expected
# --------------------------------------------------------------------------
function Get-ConformanceRoot {
    param([string]$SpecId, [string[]]$Ids, [hashtable]$JsonById)
    $ms = New-Object System.IO.MemoryStream
    $b = $Utf8.GetBytes($SpecId)
    $ms.Write($b, 0, $b.Length)
    foreach ($id in $Ids) {
        $ms.WriteByte(0)
        $b = $Utf8.GetBytes($id)
        $ms.Write($b, 0, $b.Length)
        $ms.WriteByte(0)
        $b = $Utf8.GetBytes($JsonById[$id])
        $ms.Write($b, 0, $b.Length)
    }
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try { $digest = $sha.ComputeHash($ms.ToArray()) } finally { $sha.Dispose(); $ms.Dispose() }
    $sb = New-Object System.Text.StringBuilder
    foreach ($x in $digest) { [void]$sb.Append($x.ToString('x2')) }
    return $sb.ToString()
}

# root from the spec's published `expected` objects (the note's literal reading)
$expectedJsonById = @{}
foreach ($id in $ids) { $expectedJsonById[$id] = (ConvertTo-CanonicalJson $byId[$id].expected) }
$computedRoot = Get-ConformanceRoot -SpecId $spec.spec -Ids $ids -JsonById $expectedJsonById

# root from THIS implementation's own results (identical iff every vector passes)
$ourJsonById = @{}
$ourRoot = $null
try {
    foreach ($id in $ids) {
        $ourJsonById[$id] = (ConvertTo-CanonicalJson (Invoke-Vector -VectorInput $byId[$id].input -RootsMap $spec.roots))
    }
    $ourRoot = Get-ConformanceRoot -SpecId $spec.spec -Ids $ids -JsonById $ourJsonById
}
catch { $ourRoot = "ERROR: $($_.Exception.Message)" }

Write-Host ("computed root  : {0}" -f $computedRoot)
Write-Host ("from own output: {0}" -f $ourRoot)
Write-Host ("published root : {0}" -f $spec.root)

$rootOk = ($computedRoot -ceq $spec.root) -and ($ourRoot -ceq $spec.root)
if ($rootOk) { Write-Host "ROOT MATCH" } else { Write-Host "ROOT MISMATCH" }

Write-Host ""
if ($failed.Count -eq 0 -and $rootOk) {
    Write-Host "CONFORMANCE: OK"
    exit 0
}
else {
    if ($failed.Count -gt 0) { Write-Host ("failed vectors: {0}" -f ($failed -join ', ')) }
    Write-Host "CONFORMANCE: FAILED"
    exit 1
}
