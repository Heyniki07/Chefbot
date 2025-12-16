# chefbot/model.py
import os
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .preprocessing import clean_ingredient_text


class ChefRecommender:
    """
    Robust recommender that finds the recipe CSV in data/, discovers ingredient column,
    builds TF-IDF vectors on ingredients+steps+title, and returns top-k matches.
    """

    def __init__(self):
        self.df = None
        self.tfidf = None
        self.vectors = None
        self.fitted = False

    def load_data(self, data_folder='data'):
        candidates = []
        for root, dirs, files in os.walk(data_folder):
            for f in files:
                if f.lower().endswith('.csv'):
                    candidates.append(os.path.join(root, f))
        if not candidates:
            raise FileNotFoundError("No CSV found in data folder.")
        path = candidates[0]
        print("Loading dataset:", path)
        df = pd.read_csv(path, low_memory=False)

        # Try renaming common columns to canonical names if possible
        colmap = {}
        for c in df.columns:
            lc = c.lower()
            if 'ingredient' in lc and 'ingredients' not in df.columns:
                colmap[c] = 'ingredients'
            if (('title' in lc or 'recipe name' in lc or 'name' in lc) and 'title' not in df.columns):
                # avoid renaming 'author' etc.
                if 'author' not in lc:
                    colmap[c] = 'title'
            if 'instruction' in lc and 'instructions' not in df.columns:
                colmap[c] = 'instructions'
            if 'time' in lc and 'prep_time' not in df.columns:
                colmap[c] = 'prep_time'
            if 'image' in lc and 'image_url' not in df.columns:
                colmap[c] = 'image_url'
            if 'cuisine' in lc and 'cuisine' not in df.columns:
                colmap[c] = 'cuisine'
            if ('veg' in lc or 'vegetarian' in lc) and 'is_veg' not in df.columns:
                colmap[c] = 'is_veg'

        if colmap:
            df = df.rename(columns=colmap)

        self.df = df
        return df

    def fit(self, data_folder='data'):
        """
        Fit TF-IDF on combined search_text field. This method is defensive:
        - ensures the ingredient column is located
        - converts only existing columns to string using .astype(str)
        """
        if self.df is None:
            self.load_data(data_folder)

        df = self.df.copy()

        # 1) detect an ingredients column
        ing_col = None
        for c in df.columns:
            if 'ingredient' in c.lower():
                ing_col = c
                break

        # fallback heuristic: pick a column with many commas (likely ingredient lists)
        if not ing_col:
            for c in df.columns:
                try:
                    sample = df[c].dropna().astype(str).head(200)
                except Exception:
                    continue
                if len(sample) == 0:
                    continue
                comma_rate = sum(1 for s in sample if ',' in s) / len(sample)
                if comma_rate > 0.2:
                    ing_col = c
                    break

        if not ing_col:
            raise ValueError("No ingredients column found in the dataset. "
                             "Please ensure your CSV contains an 'ingredients' column or similar.")

        # Ensure the detected ingredients column is string typed
        df[ing_col] = df[ing_col].astype(str)

        # Clean ingredients
        df['ingredients_clean'] = df[ing_col].apply(clean_ingredient_text)

        # Safely ensure optional columns exist as strings; provide safe fallbacks
        if 'cuisine' in df.columns:
            df['cuisine'] = df['cuisine'].astype(str)
        else:
            df['cuisine'] = ''

        if 'title' in df.columns:
            df['title'] = df['title'].astype(str)
        else:
            # fallback to column 'name' if present, otherwise empty string
            if 'name' in df.columns:
                df['title'] = df['name'].astype(str)
            else:
                df['title'] = ''

        if 'instructions' in df.columns:
            df['instructions'] = df['instructions'].astype(str)
        elif 'steps' in df.columns:
            df['instructions'] = df['steps'].astype(str)
        else:
            df['instructions'] = ''

        # Build search_text using ingredients + instructions/steps + title (helps matching)
        df['search_text'] = (
            df['ingredients_clean'].fillna('') + ' ' +
            df['instructions'].fillna('') + ' ' +
            df['cuisine'].fillna('') + ' ' +
            df['title'].fillna('')
        )

        # Fit TF-IDF (with fallback option)
        try:
            self.tfidf = TfidfVectorizer(ngram_range=(1, 2), min_df=2)
            self.vectors = self.tfidf.fit_transform(df['search_text'].values.astype('U'))
        except Exception:
            # fallback for small/dirty datasets
            self.tfidf = TfidfVectorizer(ngram_range=(1, 1), min_df=1)
            self.vectors = self.tfidf.fit_transform(df['search_text'].values.astype('U'))

        self.df = df
        self.fitted = True
        print('✅ TF-IDF fitted on', self.vectors.shape[0], 'recipes.')

    def recommend(self, user_ingredients, top_k=10, filters=None):
        """
        Recommend top_k recipes for the user's ingredient list.
        """
        if not self.fitted:
            raise RuntimeError('Model not fitted. Call fit() first.')

        query = clean_ingredient_text(user_ingredients)
        q_vec = self.tfidf.transform([query])
        sims = cosine_similarity(q_vec, self.vectors).flatten()

        df = self.df.copy()
        df['score'] = sims
        res = df.sort_values('score', ascending=False)

        # filters (optional)
        if filters:
            if 'is_veg' in filters and 'is_veg' in res.columns:
                res = res[res['is_veg'] == filters['is_veg']]
            if 'max_time' in filters and 'prep_time' in res.columns:
                try:
                    res = res[pd.to_numeric(res['prep_time'], errors='coerce').fillna(9999) <= float(filters['max_time'])]
                except Exception:
                    pass
            if 'cuisine' in filters and filters['cuisine']:
                res = res[res.get('cuisine', '').str.contains(filters['cuisine'], case=False, na=False)]

        # ingredient overlap scoring
        def overlap_score(row):
            recipe_ings = set((row.get('ingredients_clean') or '').split())
            user_ings = set(query.split())
            if not recipe_ings:
                return 0.0
            return len(recipe_ings & user_ings) / len(recipe_ings)

        res['ing_overlap'] = res.apply(overlap_score, axis=1)
        res['final_score'] = 0.6 * res['score'] + 0.4 * res['ing_overlap']

        top = res.sort_values('final_score', ascending=False).head(top_k)
        cols = [c for c in ['title', 'ingredients', 'instructions', 'cuisine', 'prep_time', 'image_url', 'final_score'] if c in top.columns]
        return top[cols].to_dict(orient='records')
