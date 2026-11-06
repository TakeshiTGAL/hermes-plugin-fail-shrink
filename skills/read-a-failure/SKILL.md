---
name: read-a-failure
description: Read a saved test failure when the short block is not enough. Call fail_full with the path and offset from that block.
---

Hermes registers this skill as `fail-shrink:read-a-failure`. It does not copy the file into the profile skills directory.

Before you call fail_full, write the path, the offset, and the limit in the reply. Name the log you are about to read. This tool does not delete that log and it does not change the file. It does not open an approval card.

## When a short block is enough

A failed pytest, jest, vitest, cargo test, go test, tsc, ruff, or eslint run can come back as a short block in the output field when that tool's own summary line was in the text. The exit code stays on the JSON result. The block names the place on that summary line. Pytest, Jest, Vitest, cargo, and Go summary rows often carry no line number. When pytest cuts the message off a wide summary row, the block carries the message from that test's E line and the offset points at that line. tsc, Ruff, and ESLint diagnostic rows include the file and the line. A process_manage result is shrunk when the output Hermes passed contains that summary line and the status is exited with a non-zero exit code. A poll result has output_preview and no output field, so it stays whole. Quote the place, the assert line, and the rerun line when one is present. The rerun line is built by the plugin. Do not invent a different command. A block with no rerun line has the summary place only. Run that place yourself only when the person asks. When the result stayed whole, there is no short block and no saved path. A path in the captured text is a failure location only when the short block cites it.

The short block is the failing part. It does not say the rest of the suite passed.

## When you need the saved log

Call fail_full with the path and the offset from the `full log` line. The default limit is 8000 bytes and the maximum is 32000. Call again with a higher offset to read the next slice. offset equal to the size returns empty text. The call reads one file under this profile's plugin-data/fail-shrink directory and does not write.

## What stays whole

A passing command, a short failure, a failure the plugin does not recognize, and a turn where the person asked to see the whole output stay byte for byte. Do not summarize those yourself as if the plugin had shrunk them.

Phrases that ask for the whole output include `show the full log` and `show me everything`. Fullwidth letters and an ideographic space still count as that request. The same request in Japanese, such as `全部見せて`, is accepted on the same turn.

## Turning it off

Enabling the plugin turns fail_full on for every platform. `hermes tools disable fail-shrink --platform cli` hides fail_full on that platform. Use the platform name you mean, such as `telegram`. The shrink hook still rewrites a classified failure after the tool is hidden. `hermes plugins disable fail-shrink` stops the hook and the tool.

## What this plugin does not do

It does not run the failing command. It does not call a model. It does not send the log off this computer. It does not create a cron job. It does not start a child process.

## When it fails

- bad_argument: Fix the named field. Nothing was written.
- path_refused: Pass the path printed in the short block. Nothing was written.
- not_found: That log is not in this profile. Nothing was written.
- bad_offset: Pass an offset from 0 through the file size. Nothing was written.
- bad_limit: Pass a limit from 1 through 32000. Nothing was written.
- internal: Retry once. If it repeats, say the tool failed.
