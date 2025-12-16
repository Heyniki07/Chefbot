import re, ast

def clean_ingredient_text(ing_text):
    if isinstance(ing_text, str) and ing_text.strip().startswith('['):
        try:
            items = ast.literal_eval(ing_text)
        except Exception:
            items = [ing_text]
    elif isinstance(ing_text, str):
        items = [i.strip() for i in re.split('[,;\n]', ing_text) if i.strip()]
    else:
        items = list(ing_text)

    cleaned = []
    for it in items:
        s = it.lower()
        s = re.sub(r'[\d/]+(\.\d+)?\s*(cups?|cup|tbsp|tsp|tablespoon|teaspoon|grams?|g|kg|ml|l|oz|ounce|pinch|slice|slices|packet|packets)?', '', s)
        s = re.sub(r'[^a-z\s]', ' ', s)
        s = re.sub(r'\s+', ' ', s).strip()
        if s:
            cleaned.append(s)
    return ' '.join(cleaned)
