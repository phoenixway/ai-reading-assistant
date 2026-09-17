#!/usr/bin/env bash
set -euo pipefail
cat <<'TXT'
Stage 0 hardware sweep (run against YOUR llama.cpp build):

For gpt-oss-20b on 8 GB VRAM, --n-cpu-moe means "first N MoE layers stay on CPU".
Start safe/high and LOWER N until the next value no longer fits comfortably.
Suggested sweep: 22 20 18 16 14 12 ...

Example for one point:
  llama-bench -m /path/model.gguf -fa 1 -c 8192 -b 2048 -ub 2048 -p 2048,4096 -n 128 --n-cpu-moe 22

Also watch VRAM in another terminal:
  watch -n 0.5 nvidia-smi

Record pp/tg + peak VRAM. Pick the LOWEST n-cpu-moe that remains safely inside VRAM.
TXT
