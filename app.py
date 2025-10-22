import streamlit as st
import pandas as pd  # For table
from recommender import recommend_recipes, load_moods

# In-app memory for ratings (no files – persists across clicks)
if 'ratings' not in st.session_state:
    st.session_state.ratings = {}  # {title: rating} – updates live

st.set_page_config(page_title="Mood Munch", layout="wide")
st.title("🍲 Mood Munch: Fridge to Feast with Feels")

# Sidebar
with st.sidebar:
    st.info("Ingredients + mood → Recs with tips! Rate to see your faves below. ✨")

# Inputs
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
        
        # Ratings – stays visible, no disappear
        st.subheader("Rate These Recs (Stays Put – No Reset!)")
        for i, (_, row) in enumerate(recs.iterrows(), 1):
            title_key = row['title']  # Unique key by title
            
            col_rate, col_save = st.columns(2)
            with col_rate:
                # Persistent slider – remembers value across clicks
                default_rating = st.session_state.ratings.get(title_key, 3)
                rating = st.slider(f"Rate {row['title']}", 1, 5, default_rating, key=f"slider_{title_key}")
                st.session_state.ratings[title_key] = rating  # Auto-save on drag
            with col_save:
                if st.button(f"💾 Save {rating}/5", key=f"save_{title_key}"):
                    # Save to in-app memory (no file)
                    st.session_state.ratings[title_key] = rating
                    st.rerun()  # Quick update – no full reload
                    st.balloons()  # Fun feedback!
        
        # Rec details expanders
        for i, (_, row) in enumerate(recs.iterrows(), 1):
            with st.expander(f"#{i} {row['title']} (Score: {row['similarity_score']:.2f})"):
                st.write("**Ingredients:**", row['ingredients_str'])
                st.write("**Instructions:**", row['instructions_str'])
                st.success(row['mood_tip'])
                # Thumbnail with check
                if 'thumbnail_url' in row and pd.notna(row['thumbnail_url']):
                    st.image(row['thumbnail_url'], caption="Yum!", use_column_width=True)

# Dedicated "My Ratings" section – always visible, updates live (no files!)
st.subheader("My Ratings (Saved In-App – No Files!)")
if st.session_state.ratings:
    ratings_df = pd.DataFrame(list(st.session_state.ratings.items()), columns=['Title', 'Rating'])
    st.dataframe(ratings_df, use_container_width=True)
    col_clear, col_export = st.columns(2)
    with col_clear:
        if st.button("Clear All Ratings"):
            st.session_state.ratings = {}
            st.rerun()
    with col_export:
        csv = ratings_df.to_csv(index=False)
        st.download_button("Download My Ratings (CSV)", csv, "my_ratings.csv")
else:
    st.info("Rate some recs above to see them here! 📊")

# Footer
st.markdown("---")
st.caption("All saves in-browser – no folders/DB. Built in a week with Python ❤️")