import streamlit as st
if 'test' not in st.session_state:
    st.session_state.test = 3

rating = st.slider("Test Slider", 1, 5, st.session_state.test)
st.session_state.test = rating
st.write(f"Rating saved: {rating}")  # Stays after drag

if st.button("Test Save"):
    st.rerun()
    st.success("Saved – no disappear!")