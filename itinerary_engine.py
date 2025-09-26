# itinerary_engine.py
import os
import json
from pathlib import Path
from typing import Optional, Any, Dict, List

from dotenv import load_dotenv
from groq import Groq

from schema import Itinerary
from utils import make_budget_allocation

load_dotenv()
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "llama-3.1-70b-versatile")


class ItineraryEngine:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        key = api_key or os.getenv("GROQ_API_KEY")
        if not key:
            raise RuntimeError("GROQ_API_KEY is missing. Put it in your .env")

        self.client = Groq(api_key=key)
        self.model = model or DEFAULT_MODEL

        # prompts folder relative to project root (where app.py is)
        self.base_dir = Path(__file__).resolve().parent
        self.system_prompt_path = self.base_dir / "prompts" / "system_prompt.md"

    # ---------- prompt ----------
    def _build_messages(
        self,
        destination: str,
        budget: float,
        currency: str,
        days: int,
        start_date: Optional[str],
        travelers: int,
        interests: str,
        pace: str,
        dietary: str,
        timezone: str,
    ):
        try:
            system_prompt = self.system_prompt_path.read_text(encoding="utf-8")
        except Exception as e:
            raise RuntimeError(f"Could not read system prompt at {self.system_prompt_path}") from e

        user_lines = [
            f"Destination: {destination}",
            f"Budget: {budget} {currency}",
            f"Days: {days}",
            f"Start date: {start_date or 'unspecified'}",
            f"Travelers: {travelers}",
            f"Interests: {interests or 'general highlights'}",
            f"Pace: {pace or 'balanced'}",
            f"Dietary: {dietary or 'none'}",
            f"Timezone: {timezone}",
        ]

        schema_block = {
            "destination": destination,
            "days": days,
            "start_date": start_date,
            "travelers": travelers,
            "currency": currency,
            "budget": {
                "currency": currency,
                "total_budget": budget,
                **make_budget_allocation(budget),
            },
            "day_plans": [],
            "packing_list": [],
            "safety_notes": [],
            "local_tips": [],
        }

        instructions = (
            "Return ONLY a JSON object strictly matching this Itinerary skeleton (fill with meaningful values). "
            "No markdown, no extra keys, no prose.\n"
            + json.dumps(schema_block, indent=2)
            + "\nIMPORTANT: 'day_plans[i].activities' MUST be an array of objects with "
              "keys [time_block, title, description, neighborhood?, transport?, est_cost?, tips?]. "
              "Include an integer 'day' for each day."
        )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "\n".join(user_lines) + "\n\n" + instructions},
        ]

    # ---------- normalization helpers ----------
    @staticmethod
    def _mk_activity(block: str, val: Any) -> Dict[str, Any]:
        """Convert a string or dict into an Activity dict."""
        if isinstance(val, dict):
            a = dict(val)
            a.setdefault("time_block", a.get("time") or a.get("time_of_day") or block)
            title = a.get("title") or a.get("name") or a.get("headline")
            desc = a.get("description") or a.get("details") or ""
            if not title and desc:
                title = desc[:80]
            a["title"] = title or "Activity"
            a["description"] = desc or a["title"]
            return a

        text = str(val).strip()
        title = text.split("—")[0].split(" - ")[0].split(":")[0][:80] or "Activity"
        return {"time_block": block, "title": title, "description": text}

    def _ensure_list(self, v) -> List[Any]:
        if v is None:
            return []
        if isinstance(v, list):
            return v
        return [v]

    def _extract_day_plans(self, data: Dict[str, Any]) -> List[Any]:
        # Accept alternate keys the model might use
        candidates = [
            "day_plans", "plan", "days", "schedule", "itinerary", "daily_plan"
        ]
        for key in candidates:
            v = data.get(key)
            if isinstance(v, list):
                return v
            if isinstance(v, dict):
                return list(v.values())
        return []

    def _normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # ---- budget ----
        bd = data.get("budget") or {}
        currency = bd.get("currency") or data.get("currency") or "INR"
        total = bd.get("total_budget") or 0
        alloc = make_budget_allocation(float(total or 0))
        data["budget"] = {
            "currency": currency,
            "total_budget": float(total or 0),
            **{k: float(v) for k, v in alloc.items()},
        }

        # ---- basic lists ----
        for k in ("packing_list", "safety_notes", "local_tips"):
            cur = data.get(k)
            if isinstance(cur, list):
                continue
            data[k] = [] if cur is None else [cur]

        # ---- day plans ----
        raw_days = self._extract_day_plans(data)
        fixed_days: List[Dict[str, Any]] = []

        for idx, dp0 in enumerate(raw_days, start=1):
            dp = dict(dp0) if isinstance(dp0, dict) else {"summary": str(dp0)}

            # Ensure integer day
            try:
                dp_day = int(dp.get("day")) if dp.get("day") is not None else idx
            except Exception:
                dp_day = idx
            dp["day"] = dp_day

            # Stringify date if present
            if "date" in dp and dp["date"] is not None:
                dp["date"] = str(dp["date"])

            # Activities
            acts = dp.get("activities")
            if not isinstance(acts, list):
                acts = []

            # Time-of-day keys → activities
            for block in ("morning", "afternoon", "evening", "night"):
                val = dp.pop(block, None)
                if val:
                    for v in self._ensure_list(val):
                        acts.append(self._mk_activity(block, v))

            fixed_acts: List[Dict[str, Any]] = []
            for a in acts:
                if isinstance(a, dict):
                    a.setdefault("time_block", a.get("time") or a.get("time_of_day") or "morning")
                    if not a.get("title"):
                        desc = a.get("description") or a.get("details") or ""
                        a["title"] = desc[:80] if desc else "Activity"
                    if not a.get("description"):
                        a["description"] = a["title"]
                    fixed_acts.append(a)
                else:
                    fixed_acts.append(self._mk_activity("morning", a))

            dp["activities"] = fixed_acts
            fixed_days.append(dp)

        data["day_plans"] = fixed_days
        # Ensure top-level 'days' is consistent
        if not isinstance(data.get("days"), int) or data["days"] <= 0:
            data["days"] = len(fixed_days)

        return data

    # ---------- public API ----------
    def generate(
        self,
        destination: str,
        budget: float,
        currency: str,
        days: int,
        start_date: Optional[str],
        travelers: int,
        interests: str,
        pace: str,
        dietary: str,
        timezone: str,
    ) -> Itinerary:
        messages = self._build_messages(
            destination=destination,
            budget=budget,
            currency=currency,
            days=days,
            start_date=start_date,
            travelers=travelers,
            interests=interests,
            pace=pace,
            dietary=dietary,
            timezone=timezone,
        )

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.6,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )

        content = resp.choices[0].message.content
        raw = json.loads(content)
        norm = self._normalize(raw)
        return Itinerary(**norm)
