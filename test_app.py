import pytest
from recommender import recommend_recipes, load_moods

def test_load_moods():
    moods = load_moods()
    assert len(moods) >= 4  # At least 4 moods
    assert 'cozy' in moods  # Cozy mood must exist

def test_basic_rec():
    recs = recommend_recipes(['chicken'], 'cozy', 'none')
    assert not recs.empty  # Output should not be empty
    assert 'mood_tip' in recs.columns  # Must include mood_tip column

def test_empty_input():
    recs = recommend_recipes([], 'stressed', 'none')
    assert not recs.empty  # Should still give fallback recipes

def test_filter():
    recs = recommend_recipes(['tofu'], 'stressed', 'vegan')
    assert len(recs) > 0  # Vegan filter applies correctly
