import json
import os
import re
from datetime import date, datetime
from typing import Any

from bedrock_agent import BedrockAgent

SCORING_WEIGHTS = {
    "interest_fit": 0.35,
    "master_fit": 0.25,
    "ects_fit": 0.15,
    "conflict_free": 0.15,
    "material_availability": 0.10,
}

CURRENT_DATE = date(2026, 4, 18)
DEFAULT_RECOMMENDATION_LIMIT = 4


def save_to_vector_db(user_id: str, extracted_data: dict[str, Any]) -> bool:
    """
    Simulated persistence step for the hackathon demo.
    """
    print("--- Simulated profile storage ---")
    print(f"Stored study profile for user: {user_id}")
    print(json.dumps(extracted_data, indent=2))
    print("--------------------------------")
    return True


def load_json_file(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize_text(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def extract_keywords(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        return {token for token in normalize_text(value).split() if len(token) > 2}
    if isinstance(value, list):
        tokens: set[str] = set()
        for item in value:
            tokens.update(extract_keywords(item))
        return tokens
    if isinstance(value, dict):
        tokens: set[str] = set()
        for item in value.values():
            tokens.update(extract_keywords(item))
        return tokens
    return extract_keywords(str(value))


def overlap_ratio(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return round(len(left & right) / len(left), 3)


def parse_time(value: str) -> int:
    hour, minute = value.split(":")
    return int(hour) * 60 + int(minute)


def slots_overlap(left: dict[str, str], right: dict[str, str]) -> bool:
    if left.get("day") != right.get("day"):
        return False
    return parse_time(left["start"]) < parse_time(right["end"]) and parse_time(
        right["start"]
    ) < parse_time(left["end"])


def module_conflicts_with_slots(
    module_schedule: list[dict[str, str]],
    blocked_slots: list[dict[str, str]],
) -> list[dict[str, Any]]:
    conflicts = []
    for blocked in blocked_slots:
        for slot in module_schedule:
            if slots_overlap(slot, blocked):
                conflicts.append(
                    {
                        "day": slot["day"],
                        "module_start": slot["start"],
                        "module_end": slot["end"],
                        "blocked_start": blocked["start"],
                        "blocked_end": blocked["end"],
                        "reason": blocked.get("label", "Blocked time"),
                    }
                )
    return conflicts


def modules_conflict(left_module: dict[str, Any], right_module: dict[str, Any]) -> bool:
    for left_slot in left_module.get("schedule", []):
        for right_slot in right_module.get("schedule", []):
            if slots_overlap(left_slot, right_slot):
                return True
    return False


def completed_module_ids(user_profile: dict[str, Any]) -> set[str]:
    completed = set()
    for item in user_profile.get("study_history", []):
        if item.get("status") == "passed":
            completed.add(item["module_id"])
    return completed


def build_study_profile(raw_user_data: dict[str, Any], user_id: str | None = None) -> dict[str, Any]:
    name = raw_user_data.get("name")
    if not name:
        first_name = raw_user_data.get("firstName", "")
        last_name = raw_user_data.get("lastName", "")
        name = f"{first_name} {last_name}".strip()

    profile = {
        "user_id": user_id or raw_user_data.get("user_id", "user_123"),
        "name": name or "Student",
        "program": raw_user_data.get("program") or raw_user_data.get("studyProgram", "Unknown"),
        "current_semester": raw_user_data.get("current_semester")
        or raw_user_data.get("semester", 1),
        "current_term": raw_user_data.get("current_term", "SS"),
        "total_ects": raw_user_data.get("total_ects", 0),
        "desired_ects": raw_user_data.get("desired_ects", 18),
        "master_goal": raw_user_data.get("master_goal", "Data Engineering"),
        "agent_task": raw_user_data.get(
            "agent_task",
            "Plan the next semester, recommend modules, and prepare enrollment.",
        ),
        "interests": raw_user_data.get("interests", []),
        "study_history": raw_user_data.get("study_history", []),
        "pending_requirements": raw_user_data.get("pending_requirements", {}),
        "blocked_slots": raw_user_data.get("blocked_slots", []),
        "preferred_free_days": raw_user_data.get("preferred_free_days", []),
    }
    profile["completed_module_ids"] = sorted(completed_module_ids(profile))
    return profile


def process_and_store_user_info(
    user_data_json_string: str,
    user_id: str = "user_123",
) -> dict[str, Any] | None:
    """
    Builds a deterministic study profile for the demo and stores it in the simulated DB.
    """
    print("Starting profile extraction workflow...")
    try:
        raw_user_data = json.loads(user_data_json_string)
        extracted_profile = build_study_profile(raw_user_data, user_id=user_id)
        save_to_vector_db(extracted_profile["user_id"], extracted_profile)
        return extracted_profile
    except Exception as exc:
        print(f"Profile extraction failed: {exc}")
        return None


def determine_intent(agent: BedrockAgent, user_profile: dict[str, Any], user_query: str) -> dict[str, Any]:
    """
    Uses a simple deterministic intent for the hackathon MVP and only enriches with LLM later.
    """
    _ = agent
    return {
        "intent": "plan_next_semester_and_enroll",
        "parameters": {
            "user_query": user_query,
            "desired_ects": user_profile.get("desired_ects", 18),
        },
    }


def module_is_offered(module: dict[str, Any], current_term: str) -> bool:
    return normalize_text(module.get("semester", "")) == normalize_text(current_term)


def prerequisites_met(module: dict[str, Any], user_profile: dict[str, Any]) -> bool:
    completed = set(user_profile.get("completed_module_ids", []))
    return all(prerequisite in completed for prerequisite in module.get("prerequisites", []))


def calculate_interest_fit(module: dict[str, Any], user_profile: dict[str, Any]) -> float:
    interest_keywords = extract_keywords(user_profile.get("interests", []))
    module_keywords = extract_keywords(module.get("tags", [])) | extract_keywords(
        module.get("description", "")
    )
    return overlap_ratio(interest_keywords, module_keywords)


def calculate_master_fit(module: dict[str, Any], user_profile: dict[str, Any]) -> float:
    master_goal_keywords = extract_keywords(user_profile.get("master_goal", ""))
    module_goal_keywords = extract_keywords(module.get("master_tracks", [])) | extract_keywords(
        module.get("description", "")
    )
    return overlap_ratio(master_goal_keywords, module_goal_keywords)


def calculate_ects_fit(module: dict[str, Any], user_profile: dict[str, Any]) -> float:
    desired_ects = max(int(user_profile.get("desired_ects", 18)), 1)
    ideal_module_size = max(desired_ects / 3, 5)
    distance = abs(module.get("ects", 0) - ideal_module_size)
    return round(max(0.0, 1 - (distance / ideal_module_size)), 3)


def calculate_conflict_free(module: dict[str, Any], user_profile: dict[str, Any]) -> tuple[float, list[dict[str, Any]]]:
    blocked_slots = user_profile.get("blocked_slots", [])
    conflicts = module_conflicts_with_slots(module.get("schedule", []), blocked_slots)
    if not module.get("schedule"):
        return 1.0, conflicts
    free_ratio = 1 - (len(conflicts) / len(module["schedule"]))
    return round(max(0.0, free_ratio), 3), conflicts


def score_module(module: dict[str, Any], user_profile: dict[str, Any]) -> dict[str, Any]:
    interest_fit = calculate_interest_fit(module, user_profile)
    master_fit = calculate_master_fit(module, user_profile)
    ects_fit = calculate_ects_fit(module, user_profile)
    conflict_free, blocked_conflicts = calculate_conflict_free(module, user_profile)
    material_availability = float(module.get("material_availability", 0.0))

    total_score = round(
        SCORING_WEIGHTS["interest_fit"] * interest_fit
        + SCORING_WEIGHTS["master_fit"] * master_fit
        + SCORING_WEIGHTS["ects_fit"] * ects_fit
        + SCORING_WEIGHTS["conflict_free"] * conflict_free
        + SCORING_WEIGHTS["material_availability"] * material_availability,
        3,
    )

    return {
        "score": total_score,
        "score_breakdown": {
            "interest_fit": interest_fit,
            "master_fit": master_fit,
            "ects_fit": ects_fit,
            "conflict_free": conflict_free,
            "material_availability": material_availability,
        },
        "blocked_conflicts": blocked_conflicts,
    }


def build_reason(module: dict[str, Any], score_breakdown: dict[str, float], user_profile: dict[str, Any]) -> str:
    master_goal = user_profile.get("master_goal", "dein Zielprofil")
    explanation_parts = [
        f"es zu deinem Masterziel {master_goal} passt",
        f"es dir {module['ects']} ECTS bringt",
        f"es in {module.get('semester', 'dem naechsten Semester')} angeboten wird",
    ]

    if score_breakdown["conflict_free"] == 1:
        explanation_parts.append("es keine Ueberschneidung mit deinen blockierten Zeiten hat")
    else:
        explanation_parts.append("es nur geringe Zeitkonflikte hat")

    return f"Ich empfehle {module['name']}, weil {', '.join(explanation_parts)}."


def eligible_modules(
    modules: list[dict[str, Any]],
    user_profile: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    eligible = []
    rejected = []

    for module in modules:
        reasons = []
        if not module_is_offered(module, user_profile.get("current_term", "SS")):
            reasons.append("not_offered_this_term")
        if not prerequisites_met(module, user_profile):
            reasons.append("missing_prerequisites")
        if registration_state(module["registration_deadline"])["status"] == "closed":
            reasons.append("registration_closed")

        if reasons:
            rejected.append(
                {
                    "module_id": module["module_id"],
                    "name": module["name"],
                    "reasons": reasons,
                }
            )
            continue

        scored = score_module(module, user_profile)
        eligible.append({**module, **scored})

    eligible.sort(key=lambda module: module["score"], reverse=True)
    return eligible, rejected


def select_recommendations(
    ranked_modules: list[dict[str, Any]],
    user_profile: dict[str, Any],
    limit: int = DEFAULT_RECOMMENDATION_LIMIT,
) -> list[dict[str, Any]]:
    selected = []
    selected_ects = 0
    desired_ects = user_profile.get("desired_ects", 18)

    for module in ranked_modules:
        pair_conflicts = [
            existing["module_id"]
            for existing in selected
            if modules_conflict(module, existing)
        ]
        projected_ects = selected_ects + module["ects"]

        if pair_conflicts:
            continue
        if projected_ects > desired_ects + 3 and len(selected) >= 3:
            continue

        recommendation = {
            **module,
            "pair_conflicts": pair_conflicts,
            "reason": build_reason(module, module["score_breakdown"], user_profile),
        }
        selected.append(recommendation)
        selected_ects = projected_ects

        if len(selected) == limit:
            break

    if len(selected) < 3:
        selected_ids = {module["module_id"] for module in selected}
        for module in ranked_modules:
            if module["module_id"] in selected_ids:
                continue
            selected.append(
                {
                    **module,
                    "pair_conflicts": [],
                    "reason": build_reason(module, module["score_breakdown"], user_profile),
                }
            )
            if len(selected) == min(limit, len(ranked_modules)):
                break

    return selected


def registration_state(deadline_value: str) -> dict[str, Any]:
    deadline = datetime.strptime(deadline_value, "%Y-%m-%d").date()
    remaining_days = (deadline - CURRENT_DATE).days

    if remaining_days < 0:
        status = "closed"
    elif remaining_days <= 7:
        status = "urgent"
    else:
        status = "open"

    return {
        "deadline": deadline_value,
        "days_remaining": remaining_days,
        "status": status,
    }


def analyze_plan(
    recommendations: list[dict[str, Any]],
    user_profile: dict[str, Any],
    study_plan: dict[str, Any],
) -> dict[str, Any]:
    total_ects = sum(module["ects"] for module in recommendations)
    desired_ects = user_profile.get("desired_ects", 18)
    ects_delta = total_ects - desired_ects

    if ects_delta == 0:
        ects_status = "target_matched"
    elif ects_delta < 0:
        ects_status = "below_target"
    else:
        ects_status = "above_target"

    schedule_conflicts = []
    for index, left_module in enumerate(recommendations):
        for right_module in recommendations[index + 1 :]:
            if modules_conflict(left_module, right_module):
                schedule_conflicts.append(
                    {
                        "type": "module_vs_module",
                        "left_module": left_module["module_id"],
                        "right_module": right_module["module_id"],
                    }
                )

        for conflict in left_module.get("blocked_conflicts", []):
            schedule_conflicts.append(
                {
                    "type": "module_vs_blocked_slot",
                    "module_id": left_module["module_id"],
                    "day": conflict["day"],
                    "reason": conflict["reason"],
                }
            )

    deadline_checks = []
    for module in recommendations:
        deadline_checks.append(
            {
                "module_id": module["module_id"],
                "name": module["name"],
                **registration_state(module["registration_deadline"]),
            }
        )

    return {
        "desired_ects": desired_ects,
        "planned_ects": total_ects,
        "ects_status": ects_status,
        "ects_status_label": {
            "target_matched": "Ziel erreicht",
            "below_target": "unter Zielwert",
            "above_target": "ueber Zielwert",
        }[ects_status],
        "ects_delta": ects_delta,
        "schedule_conflicts": schedule_conflicts,
        "deadline_checks": deadline_checks,
        "target_window": {
            "recommended_ects_per_semester": study_plan.get("recommended_ects_per_semester", 18),
            "max_ects_without_exception": study_plan.get("max_ects_without_exception", 21),
        },
    }


def execute_action(
    intent_data: dict[str, Any],
    recommendations: list[dict[str, Any]],
    plan_checks: dict[str, Any],
    confirm_enrollment: bool = True,
) -> dict[str, Any]:
    if intent_data.get("intent") != "plan_next_semester_and_enroll":
        return {"status": "ignored", "action_performed": intent_data.get("intent", "unknown")}

    if not confirm_enrollment:
        return {
            "status": "pending_confirmation",
            "action_performed": "prepare_tumonline_enrollment",
            "results": [],
        }

    results = []
    overall_status = "success"
    deadline_map = {item["module_id"]: item for item in plan_checks["deadline_checks"]}

    for module in recommendations:
        deadline_info = deadline_map[module["module_id"]]
        if deadline_info["status"] == "closed":
            overall_status = "partial_success"
            results.append(
                {
                    "module_id": module["module_id"],
                    "status": "failed",
                    "message": "Anmeldefrist ist bereits abgelaufen.",
                }
            )
            continue

        if module.get("seats_available", 0) <= 0:
            overall_status = "partial_success"
            results.append(
                {
                    "module_id": module["module_id"],
                    "status": "waitlist",
                    "message": "Keine freien Plaetze mehr. Auf Warteliste gesetzt.",
                }
            )
            continue

        results.append(
            {
                "module_id": module["module_id"],
                "status": "enrolled",
                "message": "Anmeldung wurde vorbereitet und an die TUMonline-Action-Layer uebergeben.",
            }
        )

    return {
        "status": overall_status,
        "action_performed": "tumonline_enrollment",
        "results": results,
    }


def generate_feedback(
    user_profile: dict[str, Any],
    recommendations: list[dict[str, Any]],
    plan_checks: dict[str, Any],
    action_result: dict[str, Any],
) -> str:
    recommendation_lines = [
        f"- {module['module_id']}: {module['reason']}"
        for module in recommendations
    ]

    deadline_lines = [
        f"- {item['module_id']}: {item['status']} ({item['days_remaining']} Tage bis zur Deadline)"
        for item in plan_checks["deadline_checks"]
    ]

    action_lines = [
        f"- {result['module_id']}: {result['status']} - {result['message']}"
        for result in action_result.get("results", [])
    ]

    conflict_summary = "keine Zeitkonflikte"
    if plan_checks["schedule_conflicts"]:
        conflict_summary = f"{len(plan_checks['schedule_conflicts'])} Konfliktwarnungen"

    lines = [
        f"Login erfolgreich fuer {user_profile['name']}.",
        (
            f"Erfasste Eingaben: Semester {user_profile['current_semester']}, "
            f"Interessen {', '.join(user_profile['interests'])}, "
            f"Masterziel {user_profile['master_goal']}, gewuenschte {user_profile['desired_ects']} ECTS."
        ),
        "Empfohlene Module:",
        *recommendation_lines,
        (
            f"Planpruefung: {plan_checks['planned_ects']} ECTS geplant, "
            f"Status {plan_checks['ects_status_label']}, {conflict_summary}."
        ),
        "Deadline-Pruefung:",
        *deadline_lines,
        "TUMonline-Feedback:",
        *action_lines,
        "Naechster Schritt: neue Interessen, geaenderten Studienstand oder eine neue Aufgabe angeben.",
    ]

    return "\n".join(lines)


def run_hero_flow(
    user_profile: dict[str, Any],
    modules: list[dict[str, Any]],
    study_plan: dict[str, Any],
    user_query: str | None = None,
    confirm_enrollment: bool = True,
) -> dict[str, Any]:
    agent = BedrockAgent()
    query = user_query or user_profile.get("agent_task", "")
    intent_data = determine_intent(agent, user_profile, query)

    ranked_modules, rejected_modules = eligible_modules(modules, user_profile)
    recommendations = select_recommendations(ranked_modules, user_profile)
    plan_checks = analyze_plan(recommendations, user_profile, study_plan)
    action_result = execute_action(
        intent_data,
        recommendations,
        plan_checks,
        confirm_enrollment=confirm_enrollment,
    )
    feedback = generate_feedback(user_profile, recommendations, plan_checks, action_result)

    return {
        "hero_flow": [
            "student_login",
            "capture_interests_study_status_and_agent_task",
            "rank_next_modules_with_weighted_score",
            "check_conflicts_ects_and_deadlines",
            "submit_tumonline_action",
            "return_feedback",
            "loop_back_to_step_2",
        ],
        "user_profile": user_profile,
        "intent": intent_data,
        "recommendations": recommendations,
        "rejected_modules": rejected_modules,
        "plan_checks": plan_checks,
        "action_result": action_result,
        "feedback": feedback,
    }


def load_demo_state(base_directory: str | None = None) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    root = base_directory or os.path.join(os.path.dirname(__file__), "TemporaryUserInfoFiles")
    user_data = load_json_file(os.path.join(root, "MockUser.json"))
    modules = load_json_file(os.path.join(root, "MockModules.json"))
    study_plan = load_json_file(os.path.join(root, "MockStudy_plan.json"))
    return user_data, modules, study_plan


def run_agent_interaction(user_id: str, user_query: str, user_profile: dict[str, Any]) -> str:
    """
    Backward-compatible helper used by the demo.
    """
    _, modules, study_plan = load_demo_state()
    full_profile = {**user_profile, "user_id": user_id, "agent_task": user_query}
    result = run_hero_flow(full_profile, modules, study_plan, user_query=user_query)
    return result["feedback"]


if __name__ == "__main__":
    raw_user_data, modules_data, study_plan_data = load_demo_state()
    raw_user_string = json.dumps(raw_user_data)
    profile = process_and_store_user_info(raw_user_string, user_id=raw_user_data["user_id"])

    if profile:
        hero_flow_result = run_hero_flow(profile, modules_data, study_plan_data)
        print("\n--- Hero Flow Result ---")
        print(json.dumps(hero_flow_result, indent=2))
        print("\n--- User Feedback ---")
        print(hero_flow_result["feedback"])
