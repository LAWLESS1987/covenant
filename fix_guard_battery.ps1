# fix_guard_battery.ps1 -- the top of the supervision chain stops on battery.
#
# WHAT IS WRONG, measured on this machine 2026-08-30
#
#   The CovenantGuard scheduled task revives the watchdog, and the watchdog
#   revives the nodes. Nothing sits above the guard, so the guard not running
#   means nothing is supervising anything.
#
#   Its settings are:
#       DisallowStartIfOnBatteries = True
#       StopIfGoingOnBatteries     = True
#       StartWhenAvailable         = False
#       ExecutionTimeLimit         = PT72H
#
#   Measured from logs/guard.log over its 1459-minute logged life: six gaps
#   longer than five minutes -- 168.3, 133.8, 115.8, 37.8, 27.9 and 20.5
#   minutes -- totalling 504 minutes. THIRTY-FIVE PERCENT of that window had
#   nothing supervising the watchdog.
#
#   And it self-clears on mains power. BatteryStatus reads 2 right now, the
#   task reads Ready, LastTaskResult 0, MissedRuns 0. So every time anyone
#   checks while plugged in, it looks perfect. That is what makes it chronic
#   rather than an incident: the condition erases its own evidence.
#
# WHAT THIS CHANGES, and nothing else
#
#   DisallowStartIfOnBatteries  True  -> False
#   StopIfGoingOnBatteries      True  -> False
#   StartWhenAvailable          False -> True
#   ExecutionTimeLimit          PT72H -> PT10M
#
#   The time limit matters more than it looks. MultipleInstances is IgnoreNew,
#   so one wedged guard run currently blocks every later run for up to three
#   days. Ten minutes is far longer than a healthy pass and bounds the damage.
#
# WHY IT MUTATES THE SETTINGS OBJECT INSTEAD OF BUILDING A NEW ONE
#
#   Set-ScheduledTask -Settings (New-ScheduledTaskSettingsSet ...) REPLACES the
#   whole settings object, silently dropping anything not restated -- here
#   Compatibility=Vista and Priority=7. This reads the existing object, changes
#   four fields, and writes that same object back. Everything else survives
#   because it was never re-created.
#
# WHAT THIS DELIBERATELY DOES NOT DO
#
#   * It does NOT move the task to S4U or RunLevel Highest. That is the obvious
#     "make it run when nobody is logged on" change and it would be worse than
#     the problem. An S4U task runs in session 0; covenant_watchdog_guard.py
#     revive and covenant_watchdog.py start_node both spawn DETACHED_PROCESS
#     and inherit that session, and start_node hardwires
#     COVENANT_LOCAL_JUDGE_URL to 127.0.0.1:11434 -- while Ollama runs in the
#     INTERACTIVE session from the Startup folder. So in exactly the scenario
#     S4U exists to cover, a revived chain would start nodes whose judge is
#     unreachable, and the judge sits inside consensus. Make Ollama a service
#     first, or teach the guard to refuse to revive while the judge is down.
#   * It does NOT add a second supervisor. redundancy.py already rejects that
#     in the project's own words: the fix is not a third supervisor, which
#     regresses forever, but an OS-level service. A second scheduled task would
#     inherit the same battery gating anyway.
#   * It does NOT restart the guard, the watchdog, the nodes, or anything else.
#
# REVERSIBLE, exactly:
#   $t=Get-ScheduledTask CovenantGuard; $s=$t.Settings
#   $s.DisallowStartIfOnBatteries=$true; $s.StopIfGoingOnBatteries=$true
#   $s.StartWhenAvailable=$false; $s.ExecutionTimeLimit='PT72H'
#   Set-ScheduledTask -TaskName CovenantGuard -Settings $s

$ErrorActionPreference = "Stop"
$TASK = "CovenantGuard"

# Takes the task, prints, returns NOTHING.
#
# The first version both printed and returned the task, and was called as
# `$t = Show "BEFORE"`. In PowerShell every un-redirected Write-Output inside a
# function goes to the pipeline, so the assignment swallowed all five lines --
# the operator never saw the BEFORE block at all -- and $t came back as an
# array of strings with the task on the end. It still limped along through
# member enumeration, which is worse than failing: a script that shows you
# nothing and then reports success is exactly the shape this whole exercise
# keeps finding. Printing and returning are now separate.
function Show([string]$when, $task) {
    $s = $task.Settings
    Write-Output ("  {0,-6} DisallowStartIfOnBatteries : {1}" -f $when, $s.DisallowStartIfOnBatteries)
    Write-Output ("  {0,-6} StopIfGoingOnBatteries     : {1}" -f $when, $s.StopIfGoingOnBatteries)
    Write-Output ("  {0,-6} StartWhenAvailable         : {1}" -f $when, $s.StartWhenAvailable)
    Write-Output ("  {0,-6} ExecutionTimeLimit         : {1}" -f $when, $s.ExecutionTimeLimit)
    Write-Output ("  {0,-6} Compatibility / Priority   : {1} / {2}   (must survive)" -f $when, $s.Compatibility, $s.Priority)
}

Write-Output ""
Write-Output "  COVENANT GUARD -- stop the supervisor stopping on battery"
Write-Output "  =========================================================="
Write-Output ""
$t = Get-ScheduledTask -TaskName $TASK -ErrorAction SilentlyContinue
if (-not $t) {
    Write-Output ("  task '{0}' NOT FOUND. Nothing to change, and that is NOT" -f $TASK)
    Write-Output "  a pass: it means nothing is supervising the watchdog at all."
    exit 2
}
Show "BEFORE" $t

$batt = Get-CimInstance Win32_Battery -ErrorAction SilentlyContinue | Select-Object -First 1
if ($batt) {
    $onAC = ($batt.BatteryStatus -eq 2)
    Write-Output ""
    Write-Output ("  Power right now: {0}" -f $(if ($onAC) { "MAINS -- which is why this reads healthy every time you look" } else { "BATTERY -- the guard is gated OFF at this moment" }))
}

Write-Output ""
Write-Output "  WILL CHANGE, and nothing else:"
Write-Output "      DisallowStartIfOnBatteries  ->  False"
Write-Output "      StopIfGoingOnBatteries      ->  False"
Write-Output "      StartWhenAvailable          ->  True"
Write-Output "      ExecutionTimeLimit          ->  PT10M   (from PT72H)"
Write-Output ""
Write-Output "  Does NOT touch RunLevel, LogonType, Compatibility, Priority,"
Write-Output "  the trigger, or the action. Does NOT restart the guard, the"
Write-Output "  watchdog, or any node. Reversal is printed at the end."
Write-Output ""
$ok = Read-Host "  Type YES to apply, anything else to cancel"
if ($ok -ne "YES") { Write-Output ""; Write-Output "  Cancelled. Nothing changed."; exit 0 }

try {
    # Mutate the EXISTING object. Building a new one with
    # New-ScheduledTaskSettingsSet would silently drop Compatibility and
    # Priority, which is a quieter bug than the one being fixed.
    $s = $t.Settings
    $s.DisallowStartIfOnBatteries = $false
    $s.StopIfGoingOnBatteries     = $false
    $s.StartWhenAvailable         = $true
    $s.ExecutionTimeLimit         = "PT10M"
    Set-ScheduledTask -TaskName $TASK -Settings $s | Out-Null
} catch {
    Write-Output ""
    Write-Output ("  FAILED: {0}" -f $_.Exception.Message)
    Write-Output "  Nothing was changed. Do not assume the guard is now covered."
    exit 1
}

Write-Output ""
$t2 = Get-ScheduledTask -TaskName $TASK
Show "AFTER" $t2
$s2 = $t2.Settings
$good = (-not $s2.DisallowStartIfOnBatteries) -and (-not $s2.StopIfGoingOnBatteries) `
        -and $s2.StartWhenAvailable -and ($s2.Compatibility -eq "Vista") -and ($s2.Priority -eq 7)

Write-Output ""
if ($good) {
    Write-Output "  APPLIED, and Compatibility and Priority survived."
} else {
    Write-Output "  APPLIED BUT THE READBACK IS NOT WHAT WAS INTENDED. Read the"
    Write-Output "  AFTER block above before trusting the guard. Reversal below."
}

Write-Output ""
Write-Output "  This raises COVERAGE. It does not add a level: the guard is"
Write-Output "  still the top of the chain with nothing above it, which"
Write-Output "  redundancy.py reports as L4 N=2. The durable fix is an"
Write-Output "  OS-level service that does not die with a console -- and that"
Write-Output "  needs Ollama out of the interactive session first."
Write-Output ""
Write-Output "  PROVE IT, rather than trusting this message: unplug the"
Write-Output "  machine, leave it a while, then check that logs/guard.log has"
Write-Output "  no gap longer than five minutes across the unplugged window."
Write-Output "      python guard_freshness.py"
Write-Output ""
Write-Output "  Reverse:"
Write-Output "      `$t=Get-ScheduledTask CovenantGuard; `$s=`$t.Settings"
Write-Output "      `$s.DisallowStartIfOnBatteries=`$true; `$s.StopIfGoingOnBatteries=`$true"
Write-Output "      `$s.StartWhenAvailable=`$false; `$s.ExecutionTimeLimit='PT72H'"
Write-Output "      Set-ScheduledTask -TaskName CovenantGuard -Settings `$s"
Write-Output ""
exit 0
