# chefbot/nutrition_utils.py
import ast
import re

def parse_nutrition_field(nutrition_str):
    """
    Best-effort parse of the RAW_recipes 'nutrition' field.
    Returns dict like {'calories': ..., 'protein': ..., 'fat': ..., 'carbs': ...}
    or None if cannot parse.
    """
    if nutrition_str is None:
        return None
    s = str(nutrition_str).strip()
    # try Python-list style like "[51.5, 0.0, ...]"
    try:
        if s.startswith("[") and s.endswith("]"):
            vals = ast.literal_eval(s)
            mapping = {}
            # Heuristic mapping (common layout in Food datasets)
            if len(vals) >= 1:
                mapping['calories'] = float(vals[0])
            # choose plausible indices for protein/fat/carbs if present
            if len(vals) >= 4:
                mapping['protein'] = float(vals[3])
            if len(vals) >= 5:
                mapping['fat'] = float(vals[4])
            if len(vals) >= 7:
                mapping['carbs'] = float(vals[6])
            return mapping
    except Exception:
        pass

    # fallback: extract numbers from string (take first as calories)
    nums = re.findall(r"[-+]?\d*\.?\d+", s)
    if len(nums) >= 1:
        try:
            return {'calories': float(nums[0])}
        except:
            return None
    return None
