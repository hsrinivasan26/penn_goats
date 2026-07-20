"""Tests for the tiered job board (education floor + experience gating)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ui"))

import jobs  # noqa: E402


def test_no_degree_starts_at_entry_only():
    offs = jobs.offerings("A", months_worked=0)
    assert jobs.available_tier("A", 0) == 0
    assert {j["tier"] for j in offs} == {0}
    assert max(j["gross"] for j in offs) == 3300      # matches config.PATHS["A"] start


def test_graduate_starts_qualified_for_skilled():
    assert jobs.education_floor("B") == 1
    offs = jobs.offerings("B", months_worked=0)
    assert max(j["tier"] for j in offs) == 1
    assert max(j["gross"] for j in offs) == 5000      # matches config.PATHS["B"] start


def test_experience_unlocks_higher_tiers_for_non_grad():
    assert jobs.available_tier("A", 11) == 0
    assert jobs.available_tier("A", 12) == 1          # skilled unlocks at 12 months
    assert jobs.available_tier("A", 30) == 2          # professional at 30 months


def test_grad_reaches_professional_faster():
    assert jobs.available_tier("B", 12) == 2          # floor 1 + 1 tenure tier
    assert max(j["gross"] for j in jobs.offerings("B", 12)) == 7200


def test_tier_is_capped_at_the_top():
    assert jobs.available_tier("B", 999) == 2
    assert jobs.available_tier("A", 999) == 2


def test_next_unlock_counts_down_then_stops():
    name, rem = jobs.next_unlock("A", 0)
    assert name == "Skilled" and rem == 12
    name, rem = jobs.next_unlock("A", 5)
    assert rem == 7
    assert jobs.next_unlock("A", 30) is None          # nothing left to unlock


def test_graduate_unlock_countdown_respects_the_education_floor():
    # a grad (floor 1) reaches Professional with only +1 experience tier -> 12 months, not 30
    name, rem = jobs.next_unlock("B", 0)
    assert name == "Professional" and rem == 12
    assert jobs.available_tier("B", 12) == 2          # and it actually unlocks then
    assert jobs.next_unlock("B", 12) is None


def test_start_titles_exist_in_catalog():
    titles = {j["title"] for j in jobs.JOBS}
    assert jobs.START_TITLE["A"] in titles
    assert jobs.START_TITLE["B"] in titles


def test_quiz_study_credit_adds_and_caps():
    assert jobs.total_experience(10, 0) == 10
    assert jobs.total_experience(10, 3) == 13
    assert jobs.total_experience(10, 99) == 10 + jobs.QUIZ_CREDIT_CAP   # capped
    assert jobs.total_experience(10, -5) == 10                          # never negative
    # credit can genuinely pull an unlock earlier: 6 worked + 6 credit == the 12-month gate
    assert jobs.available_tier("A", jobs.total_experience(6, 6)) == 1


def test_quiet_month_renders_no_event_banner():
    import render
    payload = {"bill": {"shortfall": False}, "tax": None,
               "event": {"key": "quiet", "label": "quiet", "cash_delta": 0,
                         "happiness_delta": 0, "gross_mult": None, "layoff": False}}
    assert render.event_html(payload) == ""
