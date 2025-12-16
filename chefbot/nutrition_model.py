# chefbot/nutrition_model.py
import os
import pickle
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.multioutput import MultiOutputRegressor
from sklearn.ensemble import RandomForestRegressor
from .preprocessing import clean_ingredient_text
from .nutrition_utils import parse_nutrition_field

class NutritionTrainer:
    def __init__(self):
        self.tfidf = None
        self.model = None
        self.targets = None

    def prepare_dataset(self, csv_path="data/RAW_recipes.csv", sample=None):
        df = pd.read_csv(csv_path, low_memory=False)
        # parse nutrition into columns
        parsed = df['nutrition'].fillna('').apply(parse_nutrition_field)
        nut_df = pd.DataFrame(list(parsed))
        df = pd.concat([df, nut_df], axis=1)
        # require calories
        df['calories'] = pd.to_numeric(df.get('calories', None), errors='coerce')
        df = df.dropna(subset=['calories'])
        # detect available target columns
        targets = ['calories']
        if 'protein' in df.columns and df['protein'].notna().sum() > 100:
            df['protein'] = pd.to_numeric(df['protein'], errors='coerce')
            targets.append('protein')
        if 'fat' in df.columns and df['fat'].notna().sum() > 100:
            df['fat'] = pd.to_numeric(df['fat'], errors='coerce')
            targets.append('fat')
        # optionally sample for faster training
        if sample and sample < len(df):
            df = df.sample(sample, random_state=1)
        # clean text
        df['ingredients_clean'] = df['ingredients'].fillna('').astype(str).apply(clean_ingredient_text)
        df['steps'] = df.get('steps','').astype(str)
        df['title'] = df.get('title', df.get('name','')).astype(str)
        df['search_text'] = (df['ingredients_clean'] + ' ' + df['steps'] + ' ' + df['title']).fillna('')
        X_text = df['search_text'].values.astype('U')
        y = df[targets].fillna(method='ffill').values
        return X_text, y, targets

    def train(self, csv_path="data/RAW_recipes.csv", save_path="chefbot_nutrition.pkl", sample=None):
        print("Preparing nutrition dataset (this can take some minutes)...")
        X_text, y, targets = self.prepare_dataset(csv_path, sample=sample)
        print("TF-IDF vectorizing...")
        self.tfidf = TfidfVectorizer(ngram_range=(1,2), min_df=3, max_df=0.9)
        X = self.tfidf.fit_transform(X_text)
        print("Training regression model...")
        base = RandomForestRegressor(n_estimators=100, n_jobs=-1, random_state=42)
        self.model = MultiOutputRegressor(base)
        self.model.fit(X, y)
        self.targets = targets
        with open(save_path, "wb") as f:
            pickle.dump({'tfidf': self.tfidf, 'model': self.model, 'targets': self.targets}, f)
        print("Saved nutrition model to", save_path)
        return save_path

    def load(self, path="chefbot_nutrition.pkl"):
        with open(path, "rb") as f:
            data = pickle.load(f)
        self.tfidf = data['tfidf']
        self.model = data['model']
        self.targets = data['targets']

    def predict_for_texts(self, texts):
        X = self.tfidf.transform(texts)
        preds = self.model.predict(X)
        return preds  # numpy array shape (n, len(targets))
