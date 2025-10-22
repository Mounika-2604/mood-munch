# recommender.py
import re
import json
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def parse_ingredients(sections_str):
    """Return a space-separated string of ingredient names (lowercased)."""
    if pd.isna(sections_str) or not sections_str:
        return ''
    try:
        # Try to make the string valid JSON (simple heuristic)
        fixed = re.sub(r"'([^']*)'", r'"\1"', str(sections_str).replace("'", '"'))
        sections = json.loads(fixed)
        ingredients = []
        if isinstance(sections, list):
            for section in sections:
                comps = section.get('components', [])
                for comp in comps:
                    ing_obj = comp.get('ingredient') or {}
                    name = ing_obj.get('name', '')
                    if name:
                        ingredients.append(name.lower().strip())
        return ' '.join(sorted(set(ingredients)))
    except Exception:
        # Fallback: crude regex to pull out any 'name': '...'
        names = re.findall(r"'name'\s*:\s*'([^']+)'", str(sections_str), flags=re.IGNORECASE)
        cleaned = [n.lower().strip() for n in names if n.strip()]
        return ' '.join(sorted(set(cleaned)))

def parse_instructions(instructions_str):
    """Return multi-line instructions string."""
    if pd.isna(instructions_str) or not instructions_str:
        return 'No instructions available.'
    try:
        fixed = re.sub(r"'([^']*)'", r'"\1"', str(instructions_str).replace("'", '"'))
        instructions = json.loads(fixed)
        steps = []
        if isinstance(instructions, list):
            for inst in instructions:
                text = inst.get('display_text') or inst.get('raw_text') or ''
                if text:
                    steps.append(text.strip())
        return '\n'.join(steps) if steps else 'No instructions available.'
    except Exception:
        texts = re.findall(r"'display_text'\s*:\s*'([^']+)'|'raw_text'\s*:\s*'([^']+)'",
                           str(instructions_str), flags=re.IGNORECASE)
        steps = [t[0] or t[1] for t in texts]
        return '\n'.join(steps) if steps else 'No instructions available.'

def load_moods():
    return {
        "stressed": {"tip": "Pair with deep breaths: Inhale 4, hold 4, exhale 4.", "filter": "quick"},
        "energized": {"tip": "Blast your hype playlist while cooking!", "filter": "high-protein"},
        "cozy": {"tip": "Light a candle—dinner by feels.", "filter": "warm"},
        "adventurous": {"tip": "Mix cultures—bon appétit explorer!", "filter": "fusion"}
    }

def recommend_recipes(ingredients, mood, diet='none', top_n=3, csv_path='recipes.csv'):
    """
    ingredients: list or iterable of strings (e.g., ['chicken','avocado'])
    mood: string key from load_moods (e.g., 'cozy')
    diet: string like 'vegan' or 'none'
    """
    # Load data
    df = pd.read_csv(csv_path)
    # Parse columns
    df['ingredients_str'] = df['sections'].apply(parse_ingredients)
    df['instructions_str'] = df['instructions'].apply(parse_instructions)
    df['title'] = df.get('seo_title').fillna(df.get('name')).fillna('Unknown')

    # Keep only rows with some ingredients
    df = df[df['ingredients_str'].str.len() > 0].copy()
    print(f"Parsed {len(df)} valid recipes")

    if df.empty:
        return pd.DataFrame()

    # Mood / tip
    moods = load_moods()
    if mood not in moods:
        mood = 'cozy'
    mood_tip = moods[mood]['tip']

    filtered = df.copy()

    # Diet filter
    if diet and diet.lower() != 'none':
        def has_diet(row):
            tags = row.get('tags')
            if pd.isna(tags) or not tags:
                return False
            try:
                fixed = re.sub(r"'([^']*)'", r'"\1"', str(tags).replace("'", '"'))
                tags_json = json.loads(fixed)
                tag_names = [t.get('name', '').lower() for t in tags_json if isinstance(t, dict)]
                return any(diet.lower() in t for t in tag_names)
            except Exception:
                # crude fallback
                return diet.lower() in str(tags).lower()
        filtered = filtered[filtered.apply(has_diet, axis=1)]
        print(f"After diet '{diet}': {len(filtered)} rows")

    # Mood filter
    filter_word = moods[mood].get('filter')
    if filter_word:
        if filter_word == 'quick':
            # use total_time_minutes < 30
            try:
                filtered['total_time_minutes'] = pd.to_numeric(filtered['total_time_minutes'], errors='coerce')
                filtered = filtered[filtered['total_time_minutes'].fillna(999) < 30]
            except Exception:
                # if column not present or invalid, keep as is
                pass
        else:
            def has_keyword(row):
                kw_check = filter_word.lower() in (row.get('ingredients_str', '').lower())
                tags = row.get('tags')
                if pd.isna(tags) or not tags:
                    return kw_check
                try:
                    fixed = re.sub(r"'([^']*)'", r'"\1"', str(tags).replace("'", '"'))
                    tags_json = json.loads(fixed)
                    tag_names = ' '.join([t.get('name', '') for t in tags_json if isinstance(t, dict)])
                    return filter_word.lower() in (row.get('ingredients_str', '') + ' ' + tag_names).lower()
                except Exception:
                    return kw_check
            filtered = filtered[filtered.apply(has_keyword, axis=1)]
        print(f"After mood '{filter_word}': {len(filtered)} rows")

    if filtered.empty:
        print("No matches—try broader inputs or change diet/mood filters.")
        return pd.DataFrame()

    # Prepare text for TF-IDF
    def clean_text(s):
        return ' '.join(re.findall(r'\w+', str(s).lower()))

    corpus = filtered['ingredients_str'].apply(clean_text).tolist()
    user_ing = clean_text(' '.join(ingredients))

    vectorizer = TfidfVectorizer(stop_words='english', min_df=1)
    tfidf_matrix = vectorizer.fit_transform(corpus)
    user_vec = vectorizer.transform([user_ing])

    sims = cosine_similarity(user_vec, tfidf_matrix).flatten()
    top_idx = sims.argsort()[-top_n:][::-1]

    recs = filtered.iloc[top_idx].copy()
    recs = recs[['title', 'ingredients_str', 'instructions_str']]
    recs = recs.reset_index(drop=True)
    recs['mood_tip'] = mood_tip
    recs['similarity_score'] = sims[top_idx]

    return recs
