COVENANT — LICENCE NOT YET CHOSEN
=================================

This file is a placeholder and it is deliberately not a licence.

Under the Berne Convention, code with no licence is **all rights reserved**.
Nobody may copy, modify or redistribute this repository until its author
chooses a licence and replaces this file. That is the current status.

Choosing one is the author's decision and nobody else's, so nothing has been
picked here. Three that fit what this project is:

  Apache-2.0   Permissive, and unlike MIT it grants patent rights explicitly
               and requires changed files to be marked. The usual choice for a
               protocol you would like other people to run.

  MIT          Permissive and short. Simpler than Apache-2.0 and silent on
               patents.

  AGPL-3.0     Copyleft that reaches across a network boundary: anyone running
               a modified node as a service must publish their changes. The
               strongest fit if the point is that every node's ethics gate can
               be read by the people it judges.

Two things worth deciding at the same time:

  * The ethics-gate prompts and the covenant principles are text, not code.
    If they should travel under different terms from the source, say so
    explicitly rather than leaving it to be inferred.

  * `realdata/` contains market data fetched from Kraken's public API. Its
    redistribution is governed by Kraken's terms, not by whatever you choose
    here. If this repository ever becomes public, check that before shipping
    the CSVs — or ship the fetcher and not the data.

To adopt one: replace this file entirely with the licence text, add the
SPDX identifier to the top of the source files, and record the decision in
docs/IMPROVEMENT_LOG.md so the next reader knows when it changed and why.
