# scripts/inspect_nutrition.py
import pandas as pd
from chefbot.nutrition_utils import parse_nutrition_field

df = pd.read_csv("data/RAW_recipes.csv", low_memory=False)
print("Columns:", list(df.columns))
print(df['nutrition'].head(8).to_string())
parsed = df['nutrition'].fillna('').apply(parse_nutrition_field)
print(parsed.head(10).to_string())
