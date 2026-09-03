<#
conformance_ps.ps1 -- clean-room reimplementation of "covenant-conformance-v1"
Windows PowerShell 5.1. Reads ONLY CONFORMANCE_SPEC.json (sitting next to this
file, or given via -SpecPath). Shares no code with the covenant repository.

Run:
  powershell -ExecutionPolicy Bypass -File conformance_ps.ps1

=====================================================================
SEMANTICS INFERRED FROM THE SPEC (its "note", each vector's input,
expected and "why"). Nothing else was consulted.
=====================================================================

Root letters.  Leaf/witness roots in inputs are single letters ("A", "B",
"C") or null.  Outputs publish the FULL 64-hex value, looked up in the
spec's top-level "roots" table (A -> aaaa..., B -> bbbb..., C -> cccc...).
A letter absent from the table would be passed through unchanged
(never exercised).

---------------------------------------------------------------------
op "attest"   input: { roots: {name: letter|null, ...}, quorum?: int }
output keys:  agreed, answered, outliers, reference, silent, verdict
---------------------------------------------------------------------
  asked     = every name in roots (a null root is a witness that was ASKED
              but never answered -- SILENT, never a dissenter).
  answered  = names with a non-null root, ordinal-sorted.
  silent    = names with a null root, ordinal-sorted.
  quorum    = input.quorum if given, else a majority of those ASKED:
              floor(asked/2)+1   (3 asked -> 2, 4 -> 3, 5 -> 3).
              It is NOT a constant and NOT a majority of the answerers
              (T.quorum.*, T.unproven.too-few).
  if count(answered) < quorum:
      verdict UNPROVEN, agreed false, reference null, outliers []
      (even when every answerer agrees: T.quorum.raised).
  else:
      tally the answered roots.  reference = the root with a STRICT
      plurality (strictly more holders than any other root); if two or
      more roots tie for most-held there is NO reference (null) and no
      tie-break of any kind (T.diverged.tie-for-top, T.diverged.three-way).
      outliers  = answered names whose root differs from the reference;
                  [] when there is no reference (nothing to differ from).
      agreed    = all answered hold one single root.
      verdict   = AGREE if agreed else DIVERGED.

---------------------------------------------------------------------
op "climb"    input: { tree: <level> }
  <level> = { level: name, children: [<level>|<leaf>, ...] }
  <leaf>  = { leaf: name, root: letter|null }
output keys:  clean, divergences, reference, silent_diverged,
              silent_unproven, speaks_upward, verdict
---------------------------------------------------------------------
  Each level is evaluated recursively, bottom-up.  Every child SPEAKS one
  value upward into its parent:
    - a leaf speaks its root (null = silent);
    - a sub-level speaks its reference only if its verdict is AGREE;
      a DIVERGED or UNPROVEN sub-level speaks null (silence) --
      never its majority root (S.silence.upward, S.unproven.speaks-silence).
  The level then runs "attest" over {child name: spoken value} with the
  default quorum (majority of the children ASKED; an optional "quorum"
  on a level node would be honoured but no vector carries one).

  verdict        = the level's attest verdict.
  reference      = the level's attest reference (64-hex or null).  A
                   DIVERGED level still REPORTS its reference while
                   speaking nothing upward (S.divergences.two-outliers-
                   one-level).
  speaks_upward  = (verdict == AGREE).
  divergences    = number of DISSENTING WITNESSES anywhere in the tree
                   (not diverged levels):  sum over sub-levels'
                   divergences, plus this level's own dissenters, where
                   a level's own dissenters are
                     - its outliers, if it is DIVERGED with a reference;
                     - EVERY answered child, if it is DIVERGED with no
                       reference (three-way split / tie: every witness
                       that answered into the split is party to it --
                       S.divergences.split-counts-every-party);
                     - 0 if it is AGREE or UNPROVEN (silence is not
                       disagreement -- S.quorum.default-scales-at-a-level).
  silent_diverged = ordinal-sorted names of this level's DIRECT children
                    that are DIVERGED sub-levels.
  silent_unproven = ordinal-sorted names of this level's DIRECT children
                    that spoke silence for any other reason: null-rooted
                    leaves and UNPROVEN sub-levels.
                    (Direct children only: S.silence.two-kinds reports
                    ["un"], not un's own null leaves n1,n2.)
  clean          = speaks_upward AND divergences == 0.  An UNPROVEN
                   child does not by itself break clean
                   (S.unproven.speaks-silence); an UNPROVEN summit is
                   not clean (S.quorum.default-scales-at-a-level).

---------------------------------------------------------------------
Root rule (spec "note"):  sha256 over the spec string ("spec" field,
"covenant-conformance-v1"), then for each vector in ordinal id order:
a NUL byte, the id (UTF-8), a NUL byte, the canonical JSON of the
expected object.  Canonical JSON = keys ordinal-sorted, no spaces,
ASCII-escaped like Python json.dumps(sort_keys=True,
separators=(',',':')).  root_computed below hashes MY outputs; a
diagnostic root over the spec's own expected values is also printed so
a hashing/serializer error can be told apart from a semantics error.
#>
[CmdletBinding()]
param(
    [string]$SpecPath = ''
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrEmpty($SpecPath)) {
    $SpecPath = Join-Path $PSScriptRoot 'CONFORMANCE_SPEC.json'
}

$script:Utf8 = New-Object System.Text.UTF8Encoding($false)
$script:Ordinal = [System.StringComparer]::Ordinal

function Out-Line([string]$s) {
    [Console]::Out.WriteLine($s)
}

# ---------------------------------------------------------------- JSON out

function ConvertTo-JsonStringLiteral([string]$s) {
    $sb = New-Object System.Text.StringBuilder
    [void]$sb.Append('"')
    foreach ($ch in $s.ToCharArray()) {
        $code = [int][char]$ch
        if ($code -eq 34) { [void]$sb.Append('\"') }
        elseif ($code -eq 92) { [void]$sb.Append('\\') }
        elseif ($code -eq 10) { [void]$sb.Append('\n') }
        elseif ($code -eq 13) { [void]$sb.Append('\r') }
        elseif ($code -eq 9)  { [void]$sb.Append('\t') }
        elseif ($code -eq 8)  { [void]$sb.Append('\b') }
        elseif ($code -eq 12) { [void]$sb.Append('\f') }
        elseif ($code -lt 32 -or $code -gt 126) { [void]$sb.Append('\u' + $code.ToString('x4')) }
        else { [void]$sb.Append($ch) }
    }
    [void]$sb.Append('"')
    return $sb.ToString()
}

function ConvertTo-CanonicalJson($v) {
    if ($null -eq $v) { return 'null' }
    if ($v -is [bool]) { if ($v) { return 'true' } else { return 'false' } }
    if ($v -is [string]) { return (ConvertTo-JsonStringLiteral $v) }
    if ($v -is [int] -or $v -is [long] -or $v -is [int16] -or $v -is [byte] -or $v -is [sbyte] -or $v -is [uint16] -or $v -is [uint32] -or $v -is [uint64]) {
        return $v.ToString([System.Globalization.CultureInfo]::InvariantCulture)
    }
    if ($v -is [decimal] -or $v -is [double] -or $v -is [single]) {
        # Not needed by this spec (all numbers are small integers); emit invariant repr.
        return $v.ToString('R', [System.Globalization.CultureInfo]::InvariantCulture)
    }
    if ($v -is [System.Collections.IDictionary]) {
        $keys = New-Object 'System.Collections.Generic.List[string]'
        foreach ($k in $v.Keys) { $keys.Add([string]$k) }
        $keys.Sort($script:Ordinal)
        $parts = New-Object 'System.Collections.Generic.List[string]'
        foreach ($k in $keys) {
            $parts.Add((ConvertTo-JsonStringLiteral $k) + ':' + (ConvertTo-CanonicalJson $v[$k]))
        }
        return '{' + ($parts -join ',') + '}'
    }
    if ($v -is [System.Collections.IEnumerable]) {
        $parts = New-Object 'System.Collections.Generic.List[string]'
        foreach ($item in $v) { $parts.Add((ConvertTo-CanonicalJson $item)) }
        return '[' + ($parts -join ',') + ']'
    }
    # PSCustomObject (from ConvertFrom-Json) or any other object: its properties.
    $keys = New-Object 'System.Collections.Generic.List[string]'
    foreach ($p in $v.PSObject.Properties) { $keys.Add([string]$p.Name) }
    $keys.Sort($script:Ordinal)
    $parts = New-Object 'System.Collections.Generic.List[string]'
    foreach ($k in $keys) {
        $parts.Add((ConvertTo-JsonStringLiteral $k) + ':' + (ConvertTo-CanonicalJson $v.PSObject.Properties[$k].Value))
    }
    return '{' + ($parts -join ',') + '}'
}

# ---------------------------------------------------------------- helpers

function Test-Prop($obj, [string]$name) {
    return ($null -ne $obj.PSObject.Properties[$name])
}

function Get-Sha256Hex([byte[]]$bytes) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $hash = $sha.ComputeHash($bytes)
    } finally {
        $sha.Dispose()
    }
    return [System.BitConverter]::ToString($hash).Replace('-', '').ToLowerInvariant()
}

function Add-Text([System.IO.MemoryStream]$ms, [string]$s) {
    $b = $script:Utf8.GetBytes($s)
    $ms.Write($b, 0, $b.Length)
}

function Add-Nul([System.IO.MemoryStream]$ms) {
    $ms.WriteByte([byte]0)
}

# ---------------------------------------------------------------- attest

# $roots : Dictionary[string,object] name -> letter or $null
# $quorum: $null for the default, else an int
function Invoke-Attest([System.Collections.Generic.Dictionary[string,object]]$roots, $quorum) {
    $names = New-Object 'System.Collections.Generic.List[string]'
    foreach ($k in $roots.Keys) { $names.Add($k) }
    $names.Sort($script:Ordinal)

    $answered = New-Object 'System.Collections.Generic.List[string]'
    $silent   = New-Object 'System.Collections.Generic.List[string]'
    foreach ($n in $names) {
        if ($null -eq $roots[$n]) { $silent.Add($n) } else { $answered.Add($n) }
    }

    $asked = $names.Count
    if ($null -ne $quorum) { $q = [int]$quorum } else { $q = [int][math]::Floor($asked / 2) + 1 }

    $reference = $null
    $outliers  = New-Object 'System.Collections.Generic.List[string]'
    $agreed    = $false
    $verdict   = 'UNPROVEN'

    if ($answered.Count -ge $q) {
        $tally = New-Object 'System.Collections.Generic.Dictionary[string,int]' -ArgumentList $script:Ordinal
        foreach ($n in $answered) {
            $r = [string]$roots[$n]
            if ($tally.ContainsKey($r)) { $tally[$r] = $tally[$r] + 1 } else { $tally[$r] = 1 }
        }
        $max = 0
        foreach ($kv in $tally.GetEnumerator()) { if ($kv.Value -gt $max) { $max = $kv.Value } }
        $top = New-Object 'System.Collections.Generic.List[string]'
        foreach ($kv in $tally.GetEnumerator()) { if ($kv.Value -eq $max) { $top.Add($kv.Key) } }
        if ($top.Count -eq 1) { $reference = $top[0] }
        if ($null -ne $reference) {
            foreach ($n in $answered) {
                if (-not $script:Ordinal.Equals([string]$roots[$n], $reference)) { $outliers.Add($n) }
            }
        }
        $agreed = ($tally.Count -eq 1)
        if ($agreed) { $verdict = 'AGREE' } else { $verdict = 'DIVERGED' }
    }

    return @{
        agreed    = $agreed
        answered  = $answered.ToArray()
        outliers  = $outliers.ToArray()
        reference = $reference
        silent    = $silent.ToArray()
        verdict   = $verdict
        quorum    = $q
    }
}

# ---------------------------------------------------------------- climb

function Invoke-Climb($node) {
    $children = $node.PSObject.Properties['children'].Value
    $spoken = New-Object 'System.Collections.Generic.Dictionary[string,object]' -ArgumentList $script:Ordinal
    $silentDiverged = New-Object 'System.Collections.Generic.List[string]'
    $silentUnproven = New-Object 'System.Collections.Generic.List[string]'
    $subDivergences = 0

    foreach ($c in $children) {
        if (Test-Prop $c 'leaf') {
            $name = [string]$c.PSObject.Properties['leaf'].Value
            $r = $null
            if (Test-Prop $c 'root') { $r = $c.PSObject.Properties['root'].Value }
            $spoken[$name] = $r
            if ($null -eq $r) { $silentUnproven.Add($name) }
        }
        else {
            $name = [string]$c.PSObject.Properties['level'].Value
            $sub = Invoke-Climb $c
            $subDivergences += [int]$sub.divergences
            if ($sub.speaks_upward) {
                $spoken[$name] = $sub.reference
            }
            else {
                $spoken[$name] = $null
                if ($sub.verdict -ceq 'DIVERGED') { $silentDiverged.Add($name) } else { $silentUnproven.Add($name) }
            }
        }
    }

    $quorum = $null
    if (Test-Prop $node 'quorum') { $quorum = $node.PSObject.Properties['quorum'].Value }
    $att = Invoke-Attest $spoken $quorum

    $ownDissenters = 0
    if ($att.verdict -ceq 'DIVERGED') {
        if ($null -ne $att.reference) { $ownDissenters = $att.outliers.Count } else { $ownDissenters = $att.answered.Count }
    }
    $divergences = $subDivergences + $ownDissenters
    $speaks = ($att.verdict -ceq 'AGREE')

    $silentDiverged.Sort($script:Ordinal)
    $silentUnproven.Sort($script:Ordinal)

    return @{
        verdict         = $att.verdict
        reference       = $att.reference
        speaks_upward   = $speaks
        divergences     = $divergences
        silent_diverged = $silentDiverged.ToArray()
        silent_unproven = $silentUnproven.ToArray()
        clean           = ($speaks -and ($divergences -eq 0))
    }
}

# ---------------------------------------------------------------- driver

function Expand-Root($rootsTable, $letter) {
    if ($null -eq $letter) { return $null }
    $p = $rootsTable.PSObject.Properties[[string]$letter]
    if ($null -ne $p) { return [string]$p.Value }
    return [string]$letter
}

function Invoke-Vector($spec, $vector) {
    $rootsTable = $spec.PSObject.Properties['roots'].Value
    $in = $vector.PSObject.Properties['input'].Value
    $op = [string]$in.PSObject.Properties['op'].Value

    if ($op -ceq 'attest') {
        $rootsObj = $in.PSObject.Properties['roots'].Value
        $roots = New-Object 'System.Collections.Generic.Dictionary[string,object]' -ArgumentList $script:Ordinal
        foreach ($p in $rootsObj.PSObject.Properties) { $roots[[string]$p.Name] = $p.Value }
        $quorum = $null
        if (Test-Prop $in 'quorum') { $quorum = $in.PSObject.Properties['quorum'].Value }
        $a = Invoke-Attest $roots $quorum
        return @{
            agreed    = [bool]$a.agreed
            answered  = $a.answered
            outliers  = $a.outliers
            reference = (Expand-Root $rootsTable $a.reference)
            silent    = $a.silent
            verdict   = [string]$a.verdict
        }
    }
    elseif ($op -ceq 'climb') {
        $tree = $in.PSObject.Properties['tree'].Value
        $c = Invoke-Climb $tree
        return @{
            clean           = [bool]$c.clean
            divergences     = [int]$c.divergences
            reference       = (Expand-Root $rootsTable $c.reference)
            silent_diverged = $c.silent_diverged
            silent_unproven = $c.silent_unproven
            speaks_upward   = [bool]$c.speaks_upward
            verdict         = [string]$c.verdict
        }
    }
    else {
        throw "unknown op '$op' in vector $($vector.PSObject.Properties['id'].Value)"
    }
}

# ---- self-tests of the serializer and hashing (independent of the spec) ----
$selfOk = $true
$st1 = ConvertTo-CanonicalJson ('{"b":[],"a":["k"],"c":null,"d":true,"e":0,"f":"x\"y\\z\u00e9"}' | ConvertFrom-Json)
$st1Want = '{"a":["k"],"b":[],"c":null,"d":true,"e":0,"f":"x\"y\\z\u00e9"}'
if (-not $script:Ordinal.Equals($st1, $st1Want)) { $selfOk = $false; Out-Line ("SELFTEST serializer FAIL: got " + $st1 + " want " + $st1Want) }
$st2 = Get-Sha256Hex ($script:Utf8.GetBytes('abc'))
if (-not $script:Ordinal.Equals($st2, 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')) { $selfOk = $false; Out-Line ("SELFTEST sha256 FAIL: " + $st2) }
$stList = New-Object 'System.Collections.Generic.List[string]'
$stList.Add('S.divergences.x'); $stList.Add('S.divergence.y'); $stList.Add('S-a'); $stList.Add('S.b')
$stList.Sort($script:Ordinal)
$st3 = $stList -join '|'
if (-not $script:Ordinal.Equals($st3, 'S-a|S.b|S.divergence.y|S.divergences.x')) { $selfOk = $false; Out-Line ("SELFTEST ordinal sort FAIL: " + $st3) }
if ($selfOk) { Out-Line 'SELFTEST serializer/sha256/ordinal-sort: ok' }

# ---- load the spec ----
$specText = [System.IO.File]::ReadAllText($SpecPath, $script:Utf8)
$spec = $specText | ConvertFrom-Json
$specName = [string]$spec.PSObject.Properties['spec'].Value
$rootPublished = [string]$spec.PSObject.Properties['root'].Value
$vectors = @($spec.PSObject.Properties['vectors'].Value)

Out-Line ("spec: " + $specName)
Out-Line ("spec file: " + $SpecPath)
Out-Line ("vectors: " + $vectors.Count)

$byId = New-Object 'System.Collections.Generic.Dictionary[string,object]' -ArgumentList $script:Ordinal
$ids = New-Object 'System.Collections.Generic.List[string]'
foreach ($v in $vectors) {
    $id = [string]$v.PSObject.Properties['id'].Value
    if ($byId.ContainsKey($id)) { throw "duplicate vector id $id" }
    $byId[$id] = $v
    $ids.Add($id)
}
$ids.Sort($script:Ordinal)

$msMine = New-Object System.IO.MemoryStream
$msSpec = New-Object System.IO.MemoryStream
Add-Text $msMine $specName
Add-Text $msSpec $specName

$matching = 0
$mismatches = New-Object 'System.Collections.Generic.List[object]'
Out-Line ''
foreach ($id in $ids) {
    $v = $byId[$id]
    $mine = Invoke-Vector $spec $v
    $mineJson = ConvertTo-CanonicalJson $mine
    $expJson  = ConvertTo-CanonicalJson $v.PSObject.Properties['expected'].Value

    Add-Nul $msMine; Add-Text $msMine $id; Add-Nul $msMine; Add-Text $msMine $mineJson
    Add-Nul $msSpec; Add-Text $msSpec $id; Add-Nul $msSpec; Add-Text $msSpec $expJson

    if ($script:Ordinal.Equals($mineJson, $expJson)) {
        $matching++
        Out-Line ("[MATCH]    " + $id)
    }
    else {
        $mismatches.Add(@{ id = $id; yours = $mineJson; expected = $expJson })
        Out-Line ("[MISMATCH] " + $id)
        Out-Line ("    yours:    " + $mineJson)
        Out-Line ("    expected: " + $expJson)
    }
}

$rootComputed = Get-Sha256Hex ($msMine.ToArray())
$rootOverSpecExpected = Get-Sha256Hex ($msSpec.ToArray())

Out-Line ''
Out-Line ("vectors_matching: " + $matching + " / " + $vectors.Count)
Out-Line ("mismatches: " + $mismatches.Count)
Out-Line ("root_computed  (sha256 over MY outputs):            " + $rootComputed)
Out-Line ("root_published (from the spec file):                " + $rootPublished)
Out-Line ("roots_match: " + ($script:Ordinal.Equals($rootComputed, $rootPublished)).ToString().ToLowerInvariant())
Out-Line ("diag: root over the SPEC's own expected values:     " + $rootOverSpecExpected + "  (equals root_published iff my hashing rule + serializer reproduce the published root; independent of op semantics)")
