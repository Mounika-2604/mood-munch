import pandas as pd
from recommender import parse_ingredients, parse_instructions

df = pd.read_csv('recipes.csv')
print("Raw rows:", len(df))
if len(df) == 0:
    raise SystemExit("recipes.csv seems empty")

# Parse first 6
results_ing = df['sections'].head(6).apply(parse_ingredients)
results_inst = df['instructions'].head(6).apply(parse_instructions)

# Loop
for i in range(6):
    ing = results_ing.iloc[i]
    inst = results_inst.iloc[i]
    print(f"\nROW {i} Title: {df['seo_title'].iloc[i] if not pd.isna(df['seo_title'].iloc[i]) else 'NaN'}")
    print(f"Ingredients (first 120 chars): {ing[:120] if ing else '<<empty>>'}")
    print(f"Instructions (first 120 chars): {inst[:120] if inst else '<<empty>>'}")

# Counts
parsed_ing = df['sections'].apply(parse_ingredients)
parsed_inst = df['instructions'].apply(parse_instructions)
print(f"\nRows with non-empty ingredients: {(parsed_ing.str.len() > 0).sum()} / {len(df)}")
print(f"Rows with non-empty instructions: {(parsed_inst.str.len() > 0).sum()} / {len(df)}")