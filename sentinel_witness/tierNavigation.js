/**
 * tierNavigation.js
 *
 * Single source of truth for "which tier buttons are clickable from here."
 * Pulled out of Dashboard.jsx's TierLadder deliberately: before this, the
 * reachability rule lived inline in JSX, and handleTierChange's if/else
 * chain lived a few lines below it as a SEPARATE, hand-maintained list --
 * two things that had to agree with each other but had no mechanism
 * forcing them to. Confirmed empirically (see tierNavigation.test.js)
 * that they'd already drifted: the dashboard-tier button rendered
 * clickable at manual/automated tiers, but handleTierChange had no
 * matching branch, so tapping it silently did nothing. Same shape as
 * every other "two things that must agree, drifted apart, one caller
 * didn't notice" bug this project's patch logs keep finding elsewhere --
 * fixed here the same way those were: one source of truth, not two
 * copies kept in sync by hand.
 */

import { TIERS } from "./tradeGate.js";

export const TIER_ORDER = [TIERS.DASHBOARD, TIERS.MANUAL, TIERS.AUTOMATED];

export function getTierRank(tierKey) {
  return TIER_ORDER.indexOf(tierKey);
}

/**
 * Every tier at or below (current + 1) is reachable -- stepping UP only
 * ever unlocks the next rung, but stepping DOWN is always fully open,
 * from any tier, in one tap. That asymmetry is deliberate (see
 * tradeGate.js's own "de-escalating trust should never be the hard
 * path"), not an oversight -- it's *why* dashboard is clickable from
 * automated, which is exactly the case that had no handler.
 */
export function getClickableTierKeys(currentTierKey) {
  const currentRank = getTierRank(currentTierKey);
  return TIER_ORDER.filter((key, i) => i !== currentRank && i <= currentRank + 1);
}

export function isTierClickable(currentTierKey, targetTierKey) {
  return getClickableTierKeys(currentTierKey).includes(targetTierKey);
}
