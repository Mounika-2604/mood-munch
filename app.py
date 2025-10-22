import streamlit as st
from recommender import recommend_recipes, load_moods

# Initialize session state for ratings (in-app memory)
if 'ratings' not in st.session_state:
    st.session_state.ratings = {}  # {title: rating} – persists in browser session

st.set_page_config(page_title="Mood Munch", layout="wide")
st.title("🍲 Mood Munch: Fridge to Feast with Feels")

# Sidebar
with st.sidebar:
    st.info("Enter ingredients + mood → Recs with tips! Rate to see your faves below. ✨")

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
        
        # Ratings loop – persistent with session_state
        st.subheader("Rate These (Stays Visible – No Disappearing!)")
        for i, (_, row) in enumerate(recs.iterrows(), 1):
            title_key = row['title']  # Key by title for uniqueness
            if title_key not in st.session_state.ratings:
                st.session_state.ratings[title_key] = 3  # Default 3/5
            
            col_rate, col_msg = st.columns([3,1])  # Wider slider
            with col_rate:
                rating = st.slider(f"Rate {row['title']}", 1, 5, st.session_state.ratings[title_key], key=f"slider_{title_key}")
                st.session_state.ratings[title_key] = rating  # Auto-save on slide
            with col_msg:
                if st.button(f"💾 Save {rating}/5", key=f"save_{title_key}"):
                    st.rerun()  # Quick re-draw – no full reset
                    st.balloons()  # Fun confetti!
        
        # Rec details (expanders)
        for i, (_, row) in enumerate(recs.iterrows(), 1):
            with st.expander(f"#{i} {row['title']} (Score: {row['similarity_score']:.2f})"):
                st.write("**Ingredients:**", row['ingredients_str'])
                st.write("**Instructions:**", row['instructions_str'])
                st.success(row['mood_tip'])
                if 'thumbnail_url' in row and pd.notna(row['thumbnail_url']):
                    st.image(row['thumbnail_url'], caption="Yum!", use_column_width=True)
        
        # Show saved ratings in-app (no file needed!)
        if st.button("Show My Ratings"):
            if st.session_state.ratings:
                ratings_df = pd.DataFrame(list(st.session_state.ratings.items()), columns=['Title', 'Rating'])
                st.subheader("Your Saved Ratings:")
                st.dataframe(ratings_df, use_container_width=True)
            else:
                st.info("Rate a few recs first! 📊")

# Footer
st.markdown("---")
st.caption("Built in a week with Python ❤️ – No local saves, all in-app!")