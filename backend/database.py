import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/franky_fitness")

# Seed data for ingredient_normalizations, carried over from the retired
# grocery._INGREDIENT_ALIASES dict (collapsing variants to a purchasable base
# item) plus self-maps for every base item and every "keep as written"
# distinction from the 2026-06-15 alias audit, so those strings are cache
# hits rather than LLM calls.
_NORMALIZATION_SEED_ALIASES: dict[str, str] = {
    "egg yolk": "eggs",
    "egg yolks": "eggs",
    "egg white": "eggs",
    "egg whites": "eggs",
    "egg": "eggs",
    "onions": "onion",
    "tomatoes": "tomato",
    "potatoes": "potato",
    "carrots": "carrot",
    "scallions": "scallion",
    "green onions": "green onion",
    "cucumbers": "cucumber",
    "mushrooms": "mushroom",
    "lemons": "lemon",
    "limes": "lime",
    "extra virgin olive oil": "olive oil",
    "evoo": "olive oil",
    "kosher salt": "salt",
    "sea salt": "salt",
    "table salt": "salt",
    "ground black pepper": "black pepper",
    "ground pepper": "black pepper",
    "all-purpose flour": "flour",
    "all purpose flour": "flour",
    "granulated sugar": "sugar",
    "white sugar": "sugar",
    "garlic clove": "garlic",
    "garlic cloves": "garlic",
    "fresh ginger": "ginger",
    "chicken stock": "chicken broth",
    "vegetable stock": "vegetable broth",
    "beef stock": "beef broth",
    "bell peppers": "bell pepper",
    "red bell peppers": "red bell pepper",
    "green bell peppers": "green bell pepper",
    "yellow bell peppers": "yellow bell pepper",
    "jalapeno": "jalapeño",
    "jalapenos": "jalapeño",
    "jalapeños": "jalapeño",
    "shallots": "shallot",
    "zucchinis": "zucchini",
    "apples": "apple",
    "bananas": "banana",
    "avocados": "avocado",
    "strawberries": "strawberry",
    "blueberries": "blueberry",
    "raspberries": "raspberry",
    "blackberries": "blackberry",
    "sweet potatoes": "sweet potato",
    "fresh basil": "basil",
    "dried basil": "dried basil",
    "fresh cilantro": "cilantro",
    "fresh parsley": "parsley",
    "dried parsley": "dried parsley",
    "fresh thyme": "thyme",
    "dried thyme": "dried thyme",
    "fresh rosemary": "rosemary",
    "dried rosemary": "dried rosemary",
    "fresh oregano": "oregano",
    "dried oregano": "dried oregano",
    "fresh dill": "dill",
    "fresh mint": "mint",
    "fresh chives": "chives",
    "whole milk": "milk",
    "skim milk": "milk",
    "2% milk": "milk",
    "low-fat milk": "milk",
    "plain greek yogurt": "greek yogurt",
    "plain yogurt": "yogurt",
    "heavy whipping cream": "heavy cream",
    "parmesan cheese": "parmesan",
    "cheddar cheese": "cheddar",
    "mozzarella cheese": "mozzarella",
    "chicken breasts": "chicken breast",
    "boneless skinless chicken breasts": "boneless skinless chicken breast",
    "chicken thighs": "chicken thigh",
    "boneless skinless chicken thighs": "boneless skinless chicken thigh",
    "large eggs": "eggs",
    "large egg": "eggs",
    "crushed red pepper": "red pepper flakes",
    "crushed red pepper flakes": "red pepper flakes",
    "cayenne pepper": "cayenne",
    "ground cumin": "cumin",
    "ground cinnamon": "cinnamon",
    "low sodium soy sauce": "soy sauce",
    "reduced sodium soy sauce": "soy sauce",
    "light brown sugar": "brown sugar",
    "dark brown sugar": "brown sugar",
    "confectioners sugar": "powdered sugar",
}

# "Keep as written" distinctions from the audit that aren't reachable as an
# alias *value* above (e.g. nothing maps to "minced garlic") but still need
# to be cache hits, not LLM judgment calls.
_NORMALIZATION_SEED_SELF_MAP_EXTRAS = [
    "minced garlic",
    "shredded cheddar",
    "grated cheddar",
    "salted butter",
    "unsalted butter",
    "ground ginger",
]


def _normalization_seed() -> dict[str, str]:
    """Build the full ingredient_normalizations seed: aliases plus a self-map for every base item."""
    seed = dict(_NORMALIZATION_SEED_ALIASES)
    for base_item in set(_NORMALIZATION_SEED_ALIASES.values()) | set(_NORMALIZATION_SEED_SELF_MAP_EXTRAS):
        seed.setdefault(base_item, base_item)
    return seed


def get_connection():
    return psycopg2.connect(DATABASE_URL)


def setup_tables():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(60) NOT NULL,
                    name VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS profiles (
                    user_id INTEGER PRIMARY KEY REFERENCES users(id),
                    height_inches REAL,
                    weight_lbs REAL,
                    target_weight_lbs REAL,
                    dietary_restrictions JSONB NOT NULL DEFAULT '[]',
                    fitness_goals JSONB NOT NULL DEFAULT '[]',
                    notes TEXT NOT NULL DEFAULT '',
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    token VARCHAR(64) PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS plans (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    type VARCHAR(20) NOT NULL,
                    content JSONB NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS agent_runs (
                    id SERIAL PRIMARY KEY,
                    agent_type VARCHAR(50) NOT NULL,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    latency_ms INTEGER,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            cur.execute("ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS agent_invoked VARCHAR(20)")
            cur.execute("ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS transcript_id VARCHAR(32)")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    plan_id INTEGER REFERENCES plans(id),
                    item_type VARCHAR(20) NOT NULL,
                    item_name VARCHAR(200) NOT NULL,
                    rating VARCHAR(10) NOT NULL,
                    note TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS preference_summaries (
                    user_id INTEGER PRIMARY KEY REFERENCES users(id),
                    summary JSONB NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS saved_recipes (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    content JSONB NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ingredient_normalizations (
                    raw_name VARCHAR(255) PRIMARY KEY,
                    canonical_name VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            for raw_name, canonical_name in _normalization_seed().items():
                cur.execute(
                    """INSERT INTO ingredient_normalizations (raw_name, canonical_name)
                       VALUES (%s, %s) ON CONFLICT (raw_name) DO NOTHING""",
                    (raw_name, canonical_name),
                )
        conn.commit()
