import streamlit as st
from recommender import recommend_recipes, load_moods
# Assuming db.py for save_rating – import if needed
from db import save_rating  # From Day 4

# Initialize session state for persistence
if 'ratings' not in st.session_state:
    st.session_state.ratings = {}  # Dict: {rec_index: rating}

st.set_page_config(page_title="Mood Munch", layout="wide")
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
        recs = recommend_recipes(ingredients, mood, diet)
    
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
                    save_rating(row['title'], rating, mood)  # From db.py
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