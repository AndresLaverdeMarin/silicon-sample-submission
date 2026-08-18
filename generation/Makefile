# Tier-2 generation pipeline. Run from the repository root:
#     make -C generation <target>
#
# The repository's own Makefile belongs to the organizers and stays as shipped.
# This one drives our pipeline only.

PY      := python3
SCRIPTS := scripts
WAVE    ?= 1
LIMIT   ?=
RULE    ?= mean
DRYDIR  ?= ../.dryrun

.PHONY: help probe materials cells plan wave next collect aggregate diagnose \
        dryrun dryclean clean_build

help:
	@echo "make -C generation probe        step 0: prove the session runs Fable"
	@echo "make -C generation materials    extract stimuli + items from survey/"
	@echo "make -C generation cells        build the 28 group descriptions"
	@echo "make -C generation plan         task and value counts, writes nothing"
	@echo "make -C generation wave WAVE=1 [LIMIT=40]   write a wave of tasks"
	@echo "make -C generation next LIMIT=12            list pending subagent prompts"
	@echo "make -C generation collect      validate the answers -> build/draws.csv"
	@echo "make -C generation aggregate [RULE=mean]    write predictions/"
	@echo "make -C generation diagnose     direction agreement, spread, J.1 facts"
	@echo "make -C generation dryrun       fake answers end to end, outside predictions/"
	@echo "make -C generation dryclean     remove every fake answer"

probe:
	$(PY) $(SCRIPTS)/00_model_probe.py --prompt

materials:
	$(PY) $(SCRIPTS)/01_extract_materials.py

cells:
	$(PY) $(SCRIPTS)/02_cell_profiles.py

plan: materials cells
	$(PY) $(SCRIPTS)/03_prepare_wave.py --plan

wave:
	$(PY) $(SCRIPTS)/03_prepare_wave.py --wave $(WAVE) $(if $(LIMIT),--limit $(LIMIT),)

next:
	$(PY) $(SCRIPTS)/07_next_tasks.py --limit $(if $(LIMIT),$(LIMIT),10)

collect:
	$(PY) $(SCRIPTS)/04_collect.py

aggregate:
	$(PY) $(SCRIPTS)/05_aggregate.py --rule $(RULE)

diagnose:
	$(PY) $(SCRIPTS)/06_diagnostics.py

# End-to-end rehearsal with deterministic fake numbers. Never touches
# predictions/: 05_aggregate.py refuses, and the output goes to $(DRYDIR).
dryrun: materials cells
	$(PY) $(SCRIPTS)/03_prepare_wave.py --wave 0 --skip-probe
	$(PY) $(SCRIPTS)/99_mock_answers.py
	$(PY) $(SCRIPTS)/04_collect.py --allow-model MOCK
	$(PY) $(SCRIPTS)/05_aggregate.py --out-dir $(DRYDIR) --allow-model MOCK
	$(PY) $(SCRIPTS)/06_diagnostics.py
	@echo
	@echo "dry-run files in $(DRYDIR) — expect 221 and 5,967 data rows"
	@wc -l $(DRYDIR)/*.csv

dryclean:
	$(PY) $(SCRIPTS)/99_mock_answers.py --clean
	rm -rf $(DRYDIR) build/draws.csv build/draws_provenance.json \
	       build/aggregate_report.txt build/diagnostics_report.txt \
	       build/registration_facts.md build/draw_spread.csv \
	       runs/waves/wave00.json

clean_build:
	rm -rf build
