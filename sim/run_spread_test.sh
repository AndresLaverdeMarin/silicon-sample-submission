# Does a TEMPLATE persona narrow the spread against LLM PROSE?
#
# This is the test that decides v4bio (template) against v10 (prose) for the
# submission. The Tier-1 distribution metrics — variance ratio, OVL, KS and
# Wasserstein-1 — compare the SHAPE of our control-condition answers with the
# humans'. A template is deterministic, so respondents with the same
# attributes read the same words: 71.6 per cent of our 9,000 share a full
# attribute vector. Prose is sampled, so every respondent gets its own text.
#
# 300 control respondents x 44 items = 13,200 generations for each arm.
#
# From the repository root:
#   bash sim/run_spread_test.sh
set -eu
VLLM=/home/jovyan/LLMmegastudy/.venv-vllm/bin/python

echo "### 1/3  stage 2 — prose personas for the 300"
$VLLM sim/02_write_personas.py --limit 300 2>&1 | tail -20

echo "### 2/3  stage 3 — TEMPLATE arm"
$VLLM sim/03_generate_replies.py \
    --conditions control --limit 300 \
    --persona-style template --tag spread_template 2>&1 | tail -18

echo "### 3/3  stage 3 — PROSE arm"
$VLLM sim/03_generate_replies.py \
    --conditions control --limit 300 \
    --persona-style prose \
    --persona-file sim/out/02_persona_text_smoke.csv \
    --tag spread_prose 2>&1 | tail -18

echo "SPREAD TEST DONE $(date -Is)"
