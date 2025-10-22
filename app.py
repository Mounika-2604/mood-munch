import streamlit as st
import time
from recommender import recommend_recipes, load_moods
# Database utilities
from db import save_rating, init_db, get_top_faves, log_event

# Initialize session state for persistence
if 'ratings' not in st.session_state:
    st.session_state.ratings = {}  # Dict: {rec_index: rating}

st.set_page_config(page_title="Mood Munch", layout="wide")
# Ensure DB is ready and log session start once per run
if 'db_initialized' not in st.session_state:
    init_db()
    st.session_state.db_initialized = True
    log_event('session_start', {"source": "app"})
st.title("🍲 Mood Munch: Fridge to Feast with Feels")

# Inputs (unchanged)
col1, col2 = st.columns(2)
with col1:
    user_ingredients = st.text_input("Fridge ingredients (comma-separated, e.g., chicken, avocado):")
    ingredients = [ing.strip() for ing in user_ingredients.split(',') if ing.strip()] if user_ingredients else []
with col2:
    moods_dict = load_moods()
    mood = st.selectbox("Your mood:", list(moods_dict.keys()))
    diet = st.selectbox("Diet:", ['none', 'vegan', 'low-carb', 'gluten-free'])

if st.button("Get Recipes!"):
    if not ingredients:
        st.warning("No ingredients? Using defaults: rice, eggs")
        ingredients = ['rice', 'eggs']
    
    with st.spinner("Cooking up mood-matched recs..."):
        t0 = time.perf_counter()
        recs = recommend_recipes(ingredients, mood, diet)
        duration_ms = int((time.perf_counter() - t0) * 1000)
        log_event('get_recipes', {
            "num_ingredients": len(ingredients),
            "mood": mood,
            "diet": diet,
            "duration_ms": duration_ms,
        })
    
    if recs.empty:
        st.info("No perfect matches—try looser ingredients or fewer filters!")
    else:
        st.success(f"Found {len(recs)} mood-matched recipes!")
        # Ratings loop with persistent state
        for i, (_, row) in enumerate(recs.iterrows(), 1):
            key = f"rate_{i}"  # Unique key for state
            if key not in st.session_state.ratings:
                st.session_state.ratings[key] = 3  # Default 3/5
            
            col_rate, col_save = st.columns(2)
            with col_rate:
                rating = st.slider(f"Rate #{i} {row['title']}", 1, 5, st.session_state.ratings[key], key=key)  # Persistent!
                st.session_state.ratings[key] = rating  # Save on change
            with col_save:
                if st.button(f"Save #{i}", key=f"save_{i}"):
                    save_rating(row['title'], rating, mood)
                    log_event('save_rating', {"title": row['title'], "rating": rating, "mood": mood})
                    st.success(f"Saved {row['title']} ({rating}/5) for {mood} moods!")
            
            # Rec details (unchanged)
            with st.expander(f"View #{i} {row['title']} (Score: {row['similarity_score']:.2f})"):
                st.write("**Ingredients:**", row['ingredients_str'])
                st.write("**Instructions:**", row['instructions_str'])
                st.success(row['mood_tip'])

# Sidebar (unchanged)
with st.sidebar:
    st.info("Unique: Mood-matched tips + ingredient magic!")
    st.caption("Built in a week with Python ❤️")