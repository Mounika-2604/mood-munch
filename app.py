import streamlit as st
import pandas as pd
# Import the custom recommendation module
from recommender import recommend_recipes, load_moods

# --- Setup and State Management ---
# In-app memory for ratings (persists across button clicks using Streamlit session_state)
if 'ratings' not in st.session_state:
    # Structure: {title: rating}
    st.session_state.ratings = {}

# New: Store the current recommendation results so they don't disappear on reruns
if 'recs' not in st.session_state:
    st.session_state.recs = pd.DataFrame()

# New: Flag to know if a search has been attempted, to display the "no matches" error correctly
if 'search_attempted' not in st.session_state:
    st.session_state.search_attempted = False

st.set_page_config(page_title="Mood Munch", layout="wide")
st.title("🍲 Mood Munch: Fridge to Feast with Feels")

# --- Sidebar and Info ---
with st.sidebar:
    st.info("Input your ingredients and mood to get personalized, filtered recipe recommendations! Rate your results to track your favorites.")

# --- User Inputs ---
col1, col2, col3 = st.columns(3)

with col1:
    user_ingredients = st.text_input("1. What's in your fridge? (e.g., chicken, avocado):")
    ingredients = [ing.strip() for ing in user_ingredients.split(',') if ing.strip()] if user_ingredients else []

with col2:
    moods_dict = load_moods()
    mood = st.selectbox("2. How do you feel right now?", list(moods_dict.keys()))

with col3:
    diet = st.selectbox("3. Filter by Diet (Optional):", ['none', 'vegan', 'low-carb', 'gluten-free'])

# --- Main Recommendation Button ---
if st.button("Get Recipes!", use_container_width=True, type="primary"):
    if not ingredients:
        st.warning("No ingredients listed. Using default search: 'rice' and 'eggs'.")
        ingredients = ['rice', 'eggs']
    
    with st.spinner(f"Cooking up recipes for your '{mood}' mood..."):
        # Get recommendations from the backend logic
        recs = recommend_recipes(ingredients, mood, diet)
        # Store results in session state
        st.session_state.recs = recs
        st.session_state.search_attempted = True
        
# --- Recommendation Display (Persists across Reruns) ---

if st.session_state.search_attempted:
    
    recs = st.session_state.recs
    
    if recs.empty:
        st.error("😭 No perfect matches found after applying all filters. Try a broader mood or fewer dietary restrictions!")
    else:
        st.success(f"Found {len(recs)} top recipes for you!")
        
        # Display Recommendations and Ratings
        st.markdown("---")
        st.subheader("Your Mood-Matched Recommendations")
        
        for i, (_, row) in enumerate(recs.iterrows(), 1):
            title_key = row['title'] # Unique identifier for session state
            
            with st.container(border=True):
                st.markdown(f"**Recipe #{i}: {row['title']}** (Similarity: `{row['similarity_score']:.2f}`)")
                
                # Rating UI
                col_rate, col_tip = st.columns([1, 2])
                with col_rate:
                    # Retrieve existing rating or default to 3
                    default_rating = st.session_state.ratings.get(title_key, 3)
                    rating = st.slider("Rate this recipe (1-5)", 1, 5, default_rating, key=f"slider_{title_key}")
                    
                    # Update session state immediately (useful for later use if needed)
                    st.session_state.ratings[title_key] = rating 
                    
                with col_tip:
                    st.success(f"**Mood Booster:** {row['mood_tip']}")
                    st.caption(f"Best matched ingredients: {row['ingredients_str'].split(' ')[0:5]}...")

                # --- Instructions (Now visible by default, addressing user query #2) ---
                
                # Display instructions nicely, replacing newlines with list formatting
                steps = [f"- {step.strip()}" for step in row['instructions_str'].split('\n') if step.strip()]
                st.markdown("**Cooking Steps (First 3):**")
                st.markdown('\n'.join(steps[0:3])) # Show first few steps directly
                if len(steps) > 3:
                     st.caption(f"({len(steps) - 3} more steps in the full details section below.)")

                # Recipe Details (Expander now contains full steps and ingredients)
                with st.expander("Show Full Ingredients List & All Steps"):
                    st.markdown("**Ingredients Matched:**")
                    st.code(row['ingredients_str'].replace(' ', ', '))
                    
                    st.markdown("**Full Cooking Steps:**")
                    st.markdown('\n'.join(steps))

# --- Dedicated "My Ratings" Section (Always Visible) ---
st.markdown("---")
st.subheader("📊 My Saved Ratings")

if st.session_state.ratings:
    # Convert session state dictionary to DataFrame for display
    ratings_data = [{'Title': title, 'Rating': rating} for title, rating in st.session_state.ratings.items()]
    ratings_df = pd.DataFrame(ratings_data)
    
    # Sort by rating descending
    ratings_df = ratings_df.sort_values(by='Rating', ascending=False)
    
    st.dataframe(ratings_df, use_container_width=True, hide_index=True)
    
    col_clear, col_export = st.columns(2)
    with col_clear:
        if st.button("Clear All Ratings", key="clear_ratings"):
            st.session_state.ratings = {}
            st.rerun()
    with col_export:
        csv = ratings_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download My Ratings (CSV)",
            data=csv,
            file_name="mood_munch_ratings.csv",
            mime="text/csv",
        )
else:
    st.info("Rate some recipes above to start tracking your favorites here! 🌟")

st.markdown("---")
st.caption("Developed with Python, Streamlit, and a strong craving for good food.")
