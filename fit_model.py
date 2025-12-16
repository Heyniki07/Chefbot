# fit_model.py
import pickle
from chefbot.model import ChefRecommender

MODEL_PATH = "chefbot_model.pkl"

def main():
    r = ChefRecommender()
    print("Loading dataset and fitting model... (this may take a while)")
    r.fit(data_folder='data')   # blocks until done
    print("Saving fitted model to", MODEL_PATH)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(r, f)
    print("Done. You can now run the Flask app (it will load this model).")

if __name__ == "__main__":
    main()
