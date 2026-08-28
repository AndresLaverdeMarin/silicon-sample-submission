#!/bin/bash
# Wait for the v14 run to finish, then run the spread test. Polls the log
# only — matching on a process name also matches this script.
L=/home/jovyan/LLMmegastudy/modelbench/output/runs/2026-08-28_item-mode_v14_opinion-rule/run_v14.log
for i in $(seq 1 480); do          # 480 x 30 s = 4 h ceiling
  grep -qa "GENERATION DONE" "$L" && break
  sleep 30
done
if ! grep -qa "GENERATION DONE" "$L"; then
  echo "v14 did not finish within the ceiling. Spread test NOT started."
  exit 1
fi
echo "v14 finished at $(date -Is); starting the spread test"
cd ~/silicon-sample-submission && exec bash sim/run_spread_test.sh
