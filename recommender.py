import pandas as pd
import json
import re
from functools import lru_cache
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Commented ML (skip for now – uncomment after install)
# from surprise import Dataset, Reader, KNNBasic
# from surprise.model_selection import train_test_split
# from io import StringIO
# import sqlite3  # For get_ratings_df

# def get_ratings_df():
#     conn = sqlite3.connect('faves.db')
#     df = pd.read_sql_query("SELECT title, score, mood FROM ratings", conn)
#     conn.close()
#     return df

# def get_personalized_recs(df, user_mood, top_n=3):
#     ratings_df = get_ratings_df()
#     if ratings_df.empty:
#         return pd.DataFrame()
#     reader = Reader(rating_scale=(1, 5))
#     data = Dataset.load_from_df(ratings_df[['title', 'title', 'score']], reader)
#     trainset = train_test_split(data, test_size=0.25)[0]
#     sim_options = {'name': 'cosine', 'user_based': False}
#     model = KNNBasic(sim_options=sim_options)
#     model.fit(trainset)
#     mood_ratings = ratings_df[ratings_df['mood'] == user_mood]
#     if mood_ratings.empty:
#         return pd.DataFrame()
#     first_title = mood_ratings['title'].iloc[0]
#     predictions = [model.predict(first_title, title) for title in mood_ratings['title'].unique()]
#     top_preds = sorted(predictions, key=lambda x: x.est, reverse=True)[:top_n]
#     rec_titles = [pred.iid for pred in top_preds]
#     recs = df[df['title'].isin(rec_titles)].head(top_n)[['title', 'instructions_str', 'mood_tip']].copy()
#     recs['predicted_rating'] = [p.est for p in top_preds]
#     return recs

def parse_ingredients(sections_str):
    """Extract ingredient names—JSON + regex fallback."""
    if pd.isna(sections_str) or not sections_str:
        return ''
    try:
        # Fix single quotes (recursive for nested)
        fixed = re.sub(r"'([^']*)'", r'"\1"', str(sections_str).replace("'", '"'))
        sections = json.loads(fixed)
        ingredients = []
        if isinstance(sections, list):
            for section in sections:
                if 'components' in section:
                    for comp in section['components']:
                        if 'ingredient' in comp and 'name' in comp['ingredient']:
                            name = comp['ingredient']['name'].lower().strip()
                            if name:
                                ingredients.append(name)
        return ' '.join(set(ingredients))
    except:
        # Fallback regex
        names = re.findall(r"'name'\s*:\s*'([^']+)'", sections_str, re.IGNORECASE)
        return ' '.join(set([n.lower().strip() for n in names if n.strip()]))

def parse_instructions(instructions_str):
    """Extract instructions—JSON + regex fallback."""
    if pd.isna(instructions_str) or not instructions_str:
        return 'No instructions available.'
    try:
        fixed = re.sub(r"'([^']*)'", r'"\1"', str(instructions_str).replace("'", '"'))
        instructions = json.loads(fixed)
        steps = []
        if isinstance(instructions, list):
            for inst in instructions:
                if 'display_text' in inst:
                    steps.append(inst['display_text'].strip())
                elif 'raw_text' in inst:
                    steps.append(inst['raw_text'].strip())
        return '\n'.join(steps)
    except:
        # Fallback regex
        texts = re.findall(r"'display_text'\s*:\s*'([^']+)'|'raw_text'\s*:\s*'([^']+)'", instructions_str, re.IGNORECASE)
        steps = [t[0] or t[1] for t in texts]
        return '\n'.join(steps) if steps else 'No instructions available.'

def load_moods():
    return {
        "stressed": {"tip": "Pair with deep breaths: Inhale 4, hold 4, exhale 4.", "filter": "quick"},
        "energized": {"tip": "Blast your hype playlist while cooking! [Spotify: Upbeat Pop](https://open.spotify.com/playlist/37i9dQZF1DX0XUsuxWHRQd)", "filter": "high-protein"},
        "cozy": {"tip": "Light a candle—dinner by feels. [Lo-fi Chill](https://open.spotify.com/playlist/37i9dQZF1DX4sWSpwq3LiO)", "filter": "warm"},
        "adventurous": {"tip": "Mix cultures—bon appétit explorer! [World Beats](https://open.spotify.com/playlist/37i9dQZF1DX3Ogo9pFvBkY)", "filter": "fusion"},
        "romantic": {"tip": "Dim lights, set the mood. [Jazz Vibes](https://open.spotify.com/playlist/37i9dQZF1DX30L0nE0zvrn)", "filter": "chocolate"},
        "lazy": {"tip": "Minimal effort, max flavor. Netflix & chill approved.", "filter": "one-pot"},
        "party": {"tip": "Crowd-pleaser alert! [Party Hits](https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M)", "filter": "shareable"}
    }

@lru_cache(maxsize=1)
def _load_preprocessed_df():
    """Load CSV and precompute derived columns for faster repeated calls."""
    df = pd.read_csv('recipes.csv')
    df['ingredients_str'] = df['sections'].apply(parse_ingredients)
    df['instructions_str'] = df['instructions'].apply(parse_instructions)
    df['title'] = df['seo_title'].fillna(df['name'].fillna('Unknown'))
    df = df[df['ingredients_str'].str.len() > 0].copy()
    print(f"Parsed {len(df)} valid recipes")
    return df


def recommend_recipes(ingredients, mood, diet='none', top_n=3):
    # Copy to avoid mutating cached DataFrame
    df = _load_preprocessed_df().copy()

    if df.empty:
        return pd.DataFrame()

    moods = load_moods()
    if mood not in moods:
        mood = 'cozy'
    booster = moods[mood]['tip']

    filtered = df.copy()

    # Diet filter with robust fallback (JSON parse -> substring contains)
    if diet != 'none':
        diet_l = diet.lower()

        def has_diet(row):
            tags_val = row.get('tags') if isinstance(row, dict) else row['tags']
            if pd.isna(tags_val):
                return False
            s = str(tags_val)
            # Fast path: substring check
            if diet_l in s.lower():
                return True
            # Try to parse to structured objects and re-check
            try:
                fixed_tags = re.sub(r"'([^']*)'", r'"\1"', s.replace("'", '"'))
                tags = json.loads(fixed_tags)
                tag_names = [t.get('name', '').lower() for t in tags if isinstance(t, dict)]
                return any(diet_l in tag for tag in tag_names)
            except Exception:
                return False

        before = len(filtered)
        diet_filtered = filtered[filtered.apply(has_diet, axis=1)]
        print(f"After diet '{diet}': {len(diet_filtered)} rows (from {before})")
        # Keep diet filter result only if it finds something; otherwise, don't over-prune
        if not diet_filtered.empty:
            filtered = diet_filtered

    # Mood filter with graceful fallback if it over-prunes
    prior = filtered
    if 'filter' in moods.get(mood, {}):
        filter_word = moods[mood]['filter']
        tmp = filtered
        if filter_word == 'quick':
            tmp = tmp[tmp.get('total_time_minutes', 999).fillna(999) < 30]
        elif filter_word == 'chocolate':
            tmp = tmp[tmp['ingredients_str'].str.contains('chocolate', case=False, na=False)]
        elif filter_word == 'one-pot':
            tmp = tmp[tmp['tags'].astype(str).str.contains('one-pot', case=False, na=False)]
        elif filter_word == 'shareable':
            tmp = tmp[tmp.get('num_servings', 1).fillna(1) > 4]
        else:
            f = filter_word.lower()

            def has_keyword(row):
                kw_check = f in str(row['ingredients_str']).lower()
                tags_val = row.get('tags') if isinstance(row, dict) else row['tags']
                s = str(tags_val)
                return kw_check or (f in s.lower())

            tmp = tmp[tmp.apply(has_keyword, axis=1)]

        print(f"After mood '{filter_word}': {len(tmp)} rows")
        # Only apply mood filter if it yields results
        if not tmp.empty:
            filtered = tmp

    if filtered.empty:
        print('No matches—try broader inputs!')
        return pd.DataFrame()

    # Similarity computation; if user provided no ingredients, just take top_n
    def clean_ing(ing_str):
        return ' '.join(re.findall(r'\w+', str(ing_str).lower()))

    all_ing = filtered['ingredients_str'].apply(clean_ing)
    user_ing_list = [ing.lower() for ing in ingredients if str(ing).strip()]
    user_ing = ' '.join(user_ing_list)

    if not user_ing_list:
        recs = filtered.head(top_n)[['title', 'ingredients_str', 'instructions_str']].copy()
        recs['mood_tip'] = booster
        recs['similarity_score'] = 0.0
        return recs

    vectorizer = TfidfVectorizer(stop_words='english', min_df=1)
    tfidf_matrix = vectorizer.fit_transform(all_ing)
    user_vec = vectorizer.transform([user_ing])

    sims = cosine_similarity(user_vec, tfidf_matrix).flatten()
    # Guard against fewer rows than requested
    top_n_eff = min(top_n, len(filtered))
    top_idx = sims.argsort()[-top_n_eff:][::-1]

    recs = filtered.iloc[top_idx][['title', 'ingredients_str', 'instructions_str']].copy()
    recs['mood_tip'] = booster
    recs['similarity_score'] = sims[top_idx]

    print(f"Top {top_n_eff} scores: {sims[top_idx]}")
    return recs