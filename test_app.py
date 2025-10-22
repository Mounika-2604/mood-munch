import pytest
from recommender import recommend_recipes, load_moods

def test_load_moods():
    moods = load_moods()
    assert len(moods) >= 4  # At least originals
    assert 'cozy' in moods

def test_basic_rec():
    recs = recommend_recipes(['chicken'], 'cozy', 'none')
    assert not recs.empty  # Has recs
    assert 'mood_tip' in recs.columns

def test_empty_input():
    recs = recommend_recipes([], 'stressed', 'vegan')
    assert not recs.empty  # Fallback works

def test_filter():
    recs = recommend_recipes(['tofu'], 'stressed', 'vegan')
    assert len(recs) > 0  # Vegan filter applies