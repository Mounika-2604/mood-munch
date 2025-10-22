import pandas as pd
import json
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def parse_ingredients(sections_str):
    """Extract ingredient names—JSON parsing with a regex fallback for robustness."""
    if pd.isna(sections_str) or not sections_str:
        return ''
    try:
        # Fix single quotes and load JSON
        # Aggressive replace to handle typical messy data from Kaggle
        fixed = str(sections_str).replace("'", '"')
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
    except (json.JSONDecodeError, TypeError):
        # Fallback regex search for ingredient names
        names = re.findall(r'"name"\s*:\s*"([^"]*)"', sections_str, re.IGNORECASE)
        return ' '.join(set([n.lower().strip() for n in names if n.strip()]))

def parse_instructions(instructions_str):
    """Extract instructions—JSON parsing with a highly robust regex fallback."""
    if pd.isna(instructions_str) or not instructions_str:
        return 'No instructions available.'
    
    instructions_str = str(instructions_str)
    
    # 1. Attempt structured JSON parsing
    steps = []
    try:
        fixed = instructions_str.replace("'", '"')
        instructions = json.loads(fixed)
        
        if isinstance(instructions, list):
            for inst in instructions:
                # Check for display_text first, then raw_text
                if 'display_text' in inst and inst['display_text']:
                    steps.append(inst['display_text'].strip())
                elif 'raw_text' in inst and inst['raw_text']:
                    steps.append(inst['raw_text'].strip())
        
        if steps:
             return '\n'.join(steps)
        
    except (json.JSONDecodeError, TypeError):
        pass # Failed structured parsing, moving to regex fallbacks

    # 2. Aggressive Regex Fallback - Pattern 1 & 2
    
    # Pattern 1: Find text associated with "display_text" or "raw_text" keys (non-JSON way)
    texts = re.findall(r'"display_text"\s*:\s*"([^"]*)"|"raw_text"\s*:\s*"([^"]*)"', instructions_str, re.IGNORECASE)
    steps.extend([t[0] or t[1] for t in texts if t[0] or t[1]])

    # Pattern 2: Look for patterns that look like sentence steps (1. or 2. followed by text)
    if not steps:
        raw_steps = re.findall(r'\d+\.\s*([^.\n]*[.?!])', instructions_str)
        steps.extend([s.strip() for s in raw_steps])
        
    # 3. ULTIMATE RAW TEXT FALLBACK (New, most aggressive option)
    if not steps:
        # If all else fails, assume the entire instructions string contains raw, comma-separated, or sentence-separated text.
        
        # Strip all JSON remnants (brackets, braces, quotes, keys)
        raw_text = re.sub(r'[{}\[\]"\']|display_text|raw_text|instruction', '', instructions_str, flags=re.IGNORECASE)
        
        # --- CLEANING STEP 1: Remove time/position/id metadata ---
        raw_text = re.sub(r'(end_time|start_time|position|id)\s*:\s*\d+', '', raw_text, flags=re.IGNORECASE)
        
        # --- CLEANING STEP 2: Remove temperature/appliance metadata (targets "temperature: None appliance") ---
        raw_text = re.sub(r'(temperature|appliance)\s*:\s*(None|\w+)', '', raw_text, flags=re.IGNORECASE)

        # Replace any resulting multiple spaces, commas, or colons with a single space
        raw_text = re.sub(r'[,:\s]+', ' ', raw_text).strip()
        
        # Split by periods followed by a space, or by newline characters, or by comma-space,
        # but avoid splitting on common abbreviations like U.S.A.
        raw_split = re.split(r'(?<!\w\.\w)\.\s+|\n|, ', raw_text)
        
        # Only keep steps that are long enough to be meaningful instructions
        steps.extend([s.strip() for s in raw_split if s.strip() and len(s.strip()) > 10])

    # Final cleanup and return
    if steps:
        # Filter out duplicates and remove any lingering garbage characters
        cleaned_steps = list(dict.fromkeys(steps)) # Use dict.fromkeys to preserve order and remove duplicates
        cleaned_steps = [s.replace('"', '').replace('\\', '').strip() for s in cleaned_steps if s]
        
        # Join and return if we found anything
        if cleaned_steps:
            return '\n'.join(cleaned_steps)
            
    # If still no steps were found
    return 'No instructions available. (Parsing Failure)'


def load_moods():
    """Defines the mood-based tips and filtering keywords."""
    return {
        "stressed": {"tip": "Pair with deep breaths: Inhale 4, hold 4, exhale 4.", "filter": "quick"},
        "energized": {"tip": "Blast your hype playlist while cooking! [Spotify: Upbeat Pop]", "filter": "high-protein"},
        "cozy": {"tip": "Light a candle—dinner by feels. [Lo-fi Chill]", "filter": "warm"},
        "adventurous": {"tip": "Mix cultures—bon appétit explorer! [World Beats]", "filter": "fusion"},
        "romantic": {"tip": "Dim lights, set the mood. [Jazz Vibes]", "filter": "chocolate"},
        "lazy": {"tip": "Minimal effort, max flavor. Netflix & chill approved.", "filter": "one-pot"},
        "party": {"tip": "Crowd-pleaser alert! [Party Hits]", "filter": "shareable"}
    }

def recommend_recipes(ingredients, mood, diet='none', top_n=3):
    """
    Recommends recipes based on ingredient similarity (TF-IDF),
    filtered by user mood and diet.
    """
    try:
        df = pd.read_csv('recipes.csv')
    except FileNotFoundError:
        print("Error: recipes.csv not found. Cannot proceed with recommendation.")
        return pd.DataFrame()
    
    # 1. Data Preparation
    df['ingredients_str'] = df['sections'].apply(parse_ingredients)
    df['instructions_str'] = df['instructions'].apply(parse_instructions)
    df['title'] = df['seo_title'].fillna(df['name'].fillna('Unknown Recipe'))
    
    # Drop recipes that couldn't be parsed
    df = df[df['ingredients_str'].str.len() > 0].copy()
    
    if df.empty:
        return pd.DataFrame()
    
    moods = load_moods()
    mood_config = moods.get(mood, moods['cozy'])
    booster = mood_config['tip']
    
    # Start with the full, cleaned DataFrame
    filtered = df.copy()
    
    # Helper for parsing tags string (which is also messy JSON)
    def parse_tags(tags_str):
        if pd.isna(tags_str) or not tags_str:
            return []
        try:
            fixed_tags = str(tags_str).replace("'", '"')
            tags = json.loads(fixed_tags)
            return [t.get('name', '').lower() for t in tags if isinstance(t, dict)]
        except:
            return []

    # 2. Diet Filter (checks for tag match)
    if diet != 'none':
        diet_lower = diet.lower()
        filtered = filtered[filtered['tags'].apply(
            lambda x: diet_lower in parse_tags(x)
        )]

    # Preserve the DataFrame after the Diet Filter, in case Mood Filter fails
    df_after_diet = filtered.copy() 

    # 3. Mood Filter (applies specific logic)
    filter_word = mood_config.get('filter')
    
    # Apply Mood Filter only if we have recipes left after diet filtering
    if not filtered.empty and filter_word:
        temp_filtered = filtered.copy()
        
        if filter_word == 'quick':
            # Quick filter: total time < 30 min
            temp_filtered = temp_filtered[temp_filtered.get('total_time_minutes', np.inf).fillna(np.inf) < 30]
        elif filter_word == 'one-pot':
             # One-pot filter: checks 'tags' for 'one-pot' keyword
            temp_filtered = temp_filtered[temp_filtered['tags'].apply(lambda x: 'one-pot' in str(x).lower() if pd.notna(x) else False)]
        elif filter_word == 'shareable':
            # Shareable filter: num_servings > 4
            temp_filtered = temp_filtered[temp_filtered.get('num_servings', 1) > 4]
        else:
            # Keyword/Ingredient filter (e.g., 'chocolate', 'warm', 'high-protein', 'fusion')
            temp_filtered = temp_filtered[temp_filtered['ingredients_str'].str.contains(filter_word, case=False, na=False)]
        
        # Check if the Mood Filter was too strict
        if not temp_filtered.empty:
            filtered = temp_filtered.copy()
        else:
            # MOOD FILTER FALLBACK: If the mood filter returns nothing, fall back to the diet-filtered results.
            # We skip the mood filtering result and use the dataset filtered only by diet (or everything if diet was 'none').
            print(f"Warning: Mood filter '{mood}' was too strict. Falling back to Diet/All recipes.")
            # 'filtered' remains 'df_after_diet' which is correct. We just skip the mood filtering result.

    if filtered.empty:
        return pd.DataFrame()
    
    # Define the columns needed for output, including time columns
    output_cols = ['title', 'ingredients_str', 'instructions_str', 'total_time_minutes', 'prep_time_minutes', 'cook_time_minutes']
    # Filter this list to include only columns present in the filtered DataFrame
    valid_output_cols = [col for col in output_cols if col in filtered.columns]

    # 4. Ingredient Similarity (TF-IDF)
    
    # Function to clean ingredient string for vectorizer
    def clean_ing(ing_str):
        return ' '.join(re.findall(r'\w+', str(ing_str).lower()))
    
    all_ing = filtered['ingredients_str'].apply(clean_ing)
    user_ing = ' '.join([ing.lower() for ing in ingredients])
    
    # If user has no ingredients, but recipes were mood/diet matched, return top ones
    if not user_ing.strip():
        recs = filtered.head(top_n)[valid_output_cols].copy()
        recs['mood_tip'] = booster
        recs['similarity_score'] = 1.0 # Max score as there's no comparison
        return recs

    # TF-IDF Calculation
    vectorizer = TfidfVectorizer(stop_words='english', min_df=1)
    
    # Include user ingredients in fitting to ensure all words are in vocabulary
    all_text = all_ing.tolist() + [user_ing]
    tfidf_matrix = vectorizer.fit_transform(all_text)
    
    # Separate the recipe matrix and the user vector after fitting
    recipe_matrix = tfidf_matrix[:-1]
    user_vec = tfidf_matrix[-1]
    
    sims = cosine_similarity(user_vec, recipe_matrix).flatten()
    
    # Get top N indices
    top_idx = sims.argsort()[-top_n:][::-1]
    
    # Select the columns using the validated list
    recs = filtered.iloc[top_idx][valid_output_cols].copy()
    recs['mood_tip'] = booster
    recs['similarity_score'] = sims[top_idx]
    
    return recs
