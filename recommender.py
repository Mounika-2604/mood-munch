import pandas as pd
import json
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

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

def recommend_recipes(ingredients, mood, diet='none', top_n=3):
    df = pd.read_csv('recipes.csv')
    
    # Parse
    df['ingredients_str'] = df['sections'].apply(parse_ingredients)
    df['instructions_str'] = df['instructions'].apply(parse_instructions)
    df['title'] = df['seo_title'].fillna(df['name'].fillna('Unknown'))
    
    # Drop empty
    df = df[df['ingredients_str'].str.len() > 0].copy()
    print(f"Parsed {len(df)} valid recipes")  # 40!
    
    if df.empty:
        return pd.DataFrame()
    
    moods = load_moods()
    if mood not in moods:
        mood = 'cozy'
    booster = moods[mood]['tip']
    
    filtered = df.copy()
    
    # Diet filter
    if diet != 'none':
        def has_diet(row):
            if pd.isna(row['tags']):
                return False
            try:
                fixed_tags = re.sub(r"'([^']*)'", r'"\1"', str(row['tags']).replace("'", '"'))
                tags = json.loads(fixed_tags)
                tag_names = [t.get('name', '').lower() for t in tags if isinstance(t, dict)]
                return any(diet.lower() in tag for tag in tag_names)
            except:
                return False
        filtered = filtered[filtered.apply(has_diet, axis=1)]
        print(f"After diet '{diet}': {len(filtered)} rows")
    
    # Mood filter
    if 'filter' in moods[mood]:
        filter_word = moods[mood]['filter']
        if filter_word == 'quick':
            filtered = filtered[filtered.get('total_time_minutes', 999).fillna(999) < 30]
        elif filter_word == 'chocolate':
            filtered = filtered[filtered['ingredients_str'].str.contains('chocolate', case=False, na=False)]
        elif filter_word == 'one-pot':
            filtered = filtered[filtered['tags'].str.contains('one-pot', case=False, na=False)] if 'tags' in filtered.columns else filtered
        elif filter_word == 'shareable':
            filtered = filtered[filtered.get('num_servings', 1) > 4]
        else:
            def has_keyword(row):
                kw_check = filter_word.lower() in row['ingredients_str'].lower()
                if pd.isna(row['tags']):
                    return kw_check
                try:
                    fixed_tags = re.sub(r"'([^']*)'", r'"\1"', str(row['tags']).replace("'", '"'))
                    tags = json.loads(fixed_tags)
                    tag_names = ' '.join([t.get('name', '') for t in tags if isinstance(t, dict)])
                    return filter_word.lower() in (row['ingredients_str'] + ' ' + tag_names).lower()
                except:
                    return kw_check
            filtered = filtered[filtered.apply(has_keyword, axis=1)]
        print(f"After mood '{filter_word}': {len(filtered)} rows")
    
    if filtered.empty:
        print("No matches—try broader inputs!")
        return pd.DataFrame()
    
    # Similarity
    def clean_ing(ing_str):
        return ' '.join(re.findall(r'\w+', str(ing_str).lower()))
    
    all_ing = filtered['ingredients_str'].apply(clean_ing)
    user_ing = ' '.join([ing.lower() for ing in ingredients])
    
    vectorizer = TfidfVectorizer(stop_words='english', min_df=1)
    tfidf_matrix = vectorizer.fit_transform(all_ing)
    user_vec = vectorizer.transform([user_ing])
    
    sims = cosine_similarity(user_vec, tfidf_matrix).flatten()
    top_idx = sims.argsort()[-top_n:][::-1]
    
    recs = filtered.iloc[top_idx][['title', 'ingredients_str', 'instructions_str']].copy()
    recs['mood_tip'] = booster
    recs['similarity_score'] = sims[top_idx]
    
    print(f"Top {top_n} scores: {sims[top_idx]}")
    return recs