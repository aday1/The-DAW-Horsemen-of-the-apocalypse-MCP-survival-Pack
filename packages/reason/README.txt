REASON (Propellerhead / Reason Studios)
=======================================

There is no separate Reason MCP server in this pack.

TLDR: Load Reason as Reason Rack Plugin inside REAPER on an instrument track, then use
packages/reaper-mcp/ to drive the session (tracks, MIDI, FX outside the rack, etc.).

Inside the rack, use Reason's own sequencer or mouse; REAPER MCP does not remote-control
Reason's internal rack UI the way Bitwig OSC does for Bitwig.
