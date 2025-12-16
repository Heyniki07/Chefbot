

# ChefBot – Intelligent Recipe Recommendation System

ChefBot is an AI-powered recipe recommendation web application that suggests **multiple recipes** based on user-provided **ingredients, time constraints, and nutritional preferences**. The system is designed to help users quickly discover meals that align with their dietary goals and available resources.

---

## 🚀 Project Overview

ChefBot allows users to:

* Enter **available ingredients** (comma-separated)
* Specify **maximum cooking time**
* Optionally define **nutritional targets** such as calories and protein
* Control flexibility using a **tolerance percentage**

Based on these inputs, ChefBot intelligently recommends recipes that best satisfy the constraints using trained machine learning models.

---

## 🧠 Key Features

* Ingredient-based recipe matching
* Time-aware recipe filtering
* Nutrition-aware recommendations (Calories & Protein)
* Adjustable tolerance for flexible nutrition matching
* Multiple recipe suggestions per query
* Clean and user-friendly web interface
* Pre-trained ML models for fast inference

---

## 🏗️ System Architecture

```
User Interface (HTML/CSS)
        ↓
Flask Backend (app.py)
        ↓
ML Models (.pkl files)
        ↓
Recipe & Nutrition Dataset
```

---

##

```
```

---

## 🖥️ User Inputs

| Input               | Description                                |
| ------------------- | ------------------------------------------ |
| Ingredients         | Available items entered by the user        |
| Max Time            | Maximum cooking time (in minutes)          |
| Calories (Optional) | Target calorie intake                      |
| Protein (Optional)  | Target protein intake                      |
| Tolerance           | Acceptable deviation for nutrition targets |

---

## ⚙️ Installation & Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd CHEFBOT_CODE_UI
```

### 2. Create Virtual Environment (Recommended)

```bash
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## ▶️ Running the Application

```bash
python app.py
```

Then open your browser and navigate to:

```
http://127.0.0.1:5000
```

---

## 🧪 Machine Learning Models

* **chefbot_model.pkl**: Trained recommendation model for recipe matching
* **chefbot_nutrition.pkl**: Predicts and validates nutritional constraints

Models are pre-trained to ensure fast response and minimal setup.

---

## 🛠️ Technologies Used

* **Python**
* **Flask** (Backend Web Framework)
* **HTML / CSS / JavaScript** (Frontend)
* **Scikit-learn** (Machine Learning)
* **SQLite** (User & query storage)
* **Pandas / NumPy** (Data processing)

---

## 📈 Future Enhancements

* User authentication & profiles
* Personalized recommendations using user history
* Support for dietary preferences (vegan, keto, etc.)
* Integration with external recipe APIs
* Deployment using Docker / Cloud platforms

---

## 📄 License

This project is intended for **academic and learning purposes**. Licensing can be updated based on deployment or commercialization needs.

---

## 👤 Author

Developed by **NIKITA DESHMUKH** and **SIDDHI GAWADE**
B.Sc. Data Science Student

---

## 📬 Contact

For questions, improvements, or collaboration, feel free to reach out.

---

**ChefBot – Cook smarter, eat better.**
>>>>>>> 881c9902c2e0d3234de0aac50c98e9b7f546405b
