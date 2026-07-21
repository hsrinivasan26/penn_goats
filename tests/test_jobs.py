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
    assert max(j["gross"] for j in offs) == 4800      # matches config.PATHS["B"] start


def test_experience_unlocks_higher_tiers_for_non_grad():
    assert jobs.available_tier("A", 11) == 0
    assert jobs.available_tier("A", 12) == 1          # skilled unlocks at 12 months
    assert jobs.available_tier("A", 30) == 2          # professional at 30 months


def test_grad_reaches_professional_faster():
    assert jobs.available_tier("B", 12) == 2          # floor 1 + 1 tenure tier
    assert max(j["gross"] for j in jobs.offerings("B", 12)) == 6300


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


def test_experience_is_earned_months_not_elapsed_time():
    """The quiz IS the job: only months of passed quizzes count toward tier unlocks, so a
    player who never engages stays at their education floor forever."""
    assert jobs.available_tier("A", 0) == 0            # 60 elapsed months, 0 worked -> still Entry
    assert jobs.available_tier("A", 12) == 1           # 12 months of real work -> Skilled
    assert not hasattr(jobs, "total_experience")       # the old free-credit path is gone
    assert not hasattr(jobs, "QUIZ_CREDIT_CAP")


def test_quiet_month_renders_no_event_banner():
    import render
    payload = {"bill": {"shortfall": False}, "tax": None,
               "event": {"key": "quiet", "label": "quiet", "cash_delta": 0,
                         "happiness_delta": 0, "gross_mult": None, "layoff": False}}
    assert render.event_html(payload) == ""


def test_ages_track_birthdays_and_goal():
    assert jobs.age_at("A", 1) == 18 and jobs.age_at("B", 1) == 22
    assert jobs.age_at("A", 12) == 18                 # still 18 through the first year
    assert jobs.age_at("A", 13) == 19                 # birthday at the year mark
    assert jobs.age_at("A", 60) == 22
    assert jobs.goal_age("A") == 23 and jobs.goal_age("B") == 27


def test_city_mascots_tease_then_fill_in():
    import citybg
    locked = citybg.city_html(seed=3)
    assert "mascot-win-sil.png" in locked                   # silhouettes always loom
    assert "mascot-alltitles-sil.png" in locked
    won = citybg.city_html(seed=3, show_win=True)
    assert "mascot-win.png" in won                          # first win fills the right duck
    assert "mascot-alltitles-sil.png" in won                # left still a silhouette
    both = citybg.city_html(seed=3, show_win=True, show_titles=True)
    assert "mascot-win.png" in both and "mascot-alltitles.png" in both
    assert "sil" not in both


def test_city_variants_for_quiz_backdrop():
    import citybg
    plain = citybg.city_html(seed=3, mascots=False, tall=True)
    assert "cityduck" not in plain and "citybg tall" in plain    # skyline only, taller
    assert "citybg tall" not in citybg.city_html(seed=3)         # menu stays standard
