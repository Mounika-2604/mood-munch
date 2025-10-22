import streamlit as st
from recommender import recommend_recipes, load_moods  # Added load_moods import!
from db import init_db, save_rating, get_top_faves
init_db()
st.set_page_config(page_title="Mood Munch", layout="wide")
st.title("🍲 Mood Munch: Fridge to Feast with Feels")

# Inputs
col1, col2 = st.columns(2)
with col1:
    user_ingredients = st.text_input("Fridge ingredients (comma-separated, e.g., chicken, avocado):")
    ingredients = [ing.strip() for ing in user_ingredients.split(',') if ing.strip()] if user_ingredients else []
with col2:
    moods_dict = load_moods()  # Now accessible!
    mood = st.selectbox("Your mood:", list(moods_dict.keys()))
    diet = st.selectbox("Diet:", ['none', 'vegan', 'low-carb', 'gluten-free'])

if st.button("Get Recipes!"):
    if not ingredients:
        st.warning("No ingredients? Trying pantry defaults: rice, eggs")
        ingredients = ['rice', 'eggs']
    
    with st.spinner("Cooking up recs..."):  # Fun loading!
        recs = recommend_recipes(ingredients, mood, diet)
    
    if recs.empty:
        st.info("No perfect matches—try looser ingredients or fewer filters!")
    else:

        st.success(f"Found {len(recs)} mood-matched recipes!")
                         # Ratings section
        st.subheader("Rate These Recs? (Saves your faves!)")
        for i, (_, row) in enumerate(recs.iterrows(), 1):
           col_rate, col_save = st.columns(2)
           with col_rate:
              rating = st.slider(f"Like #{i} {row['title']}", 1, 5, 3)
           with col_save:
              if st.button(f"Save #{i}", key=f"save_{i}"):
                save_rating(row['title'], rating, mood)
                st.success(f"Saved {row['title']} as {rating}/5 for {mood} moods!")
        for i, (_, row) in enumerate(recs.iterrows(), 1):
            with st.expander(f"#{i} {row['title']} (Score: {row['similarity_score']:.2f})"):
                st.write("**Ingredients:**", row['ingredients_str'])
                st.write("**Instructions:**", row['instructions_str'])
                st.success(row['mood_tip'])

# Sidebar flair
with st.sidebar:
    st.info("Unique: Mood-matched tips + ingredient magic!")
    st.caption("Built in a week with Python ❤️")