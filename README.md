# 🧠 Mansik Santulan Score — Mental Health Signal + MindWell AI

An AI-powered student mental wellness assessment platform that predicts a student's **Mental Health Score (0–10)** using social media usage patterns and lifestyle habits. It provides easy-to-understand score interpretations, personalized recommendations, a 7-day wellness plan, and an interactive AI assistant called **MindWell AI**.

> **Disclaimer:** This is a non-clinical mental wellness screening and awareness tool. Its predictions are estimates based on survey-style data and are not a medical diagnosis or a substitute for professional mental health advice. Students experiencing emotional distress should consider speaking with a trusted person or qualified mental health professional.

🌐 **Live Application:** https://mansik-santulan-score.onrender.com

---

## ✨ Key Features

### 1. Mental Health Score Prediction
- Predicts a student's mental health score on a scale of **0–10**.
- Uses a trained Machine Learning pipeline based on Random Forest Regression.
- Analyzes 12 input features related to demographics, social media usage, academic workload, lifestyle and stress.
- Validates user inputs before generating predictions.

### 2. AI-Powered Score Interpretation
- Converts numerical predictions into understandable explanations.
- Highlights positive lifestyle habits and potential areas for improvement.
- Uses configurable score bands and thresholds.
- Provides what-if estimates using the trained ML model to explore alternative lifestyle inputs.

### 3. Personalized Recommendations
Generates suggestions based on the student's individual responses, including:
- Sleep improvement and healthy sleep routines.
- Social media usage management.
- Reducing excessive phone unlocks.
- Physical activity and exercise.
- Better study schedules and workload management.
- Stress management and relaxation techniques.

### 4. 7-Day Wellness Improvement Plan
- Creates a personalized seven-day wellness plan.
- Provides daily goals for sleep, physical activity, study sessions and screen time.
- Gradually introduces healthier habits.
- Encourages consistency through manageable daily activities.

### 5. MindWell AI – Mental Wellness Assistant
An interactive AI assistant designed to help students understand their assessment results and develop healthier routines.

**Capabilities:**
- Explains predicted mental health scores.
- Answers questions about stress, sleep and social media usage.
- Provides lifestyle and study-related suggestions.
- Helps students understand their personalized recommendations.
- Supports contextual answers using optional reference documents.

**AI Integration:**
- Uses Anthropic Claude when `ANTHROPIC_API_KEY` is configured.
- Automatically falls back to a built-in rule-based assistant when the API key is unavailable.
- Detects crisis-related language and provides supportive responses with relevant helpline information instead of a normal AI response.

### 6. Reference-Based Knowledge Retrieval
- Supports `.md` and `.txt` reference documents.
- Documents stored in the `knowledge/` directory can be retrieved to support AI responses.
- Provides source references when relevant documents are available.
- Clearly distinguishes reference-backed information from general wellness guidance.

### 7. Privacy and Session Management
- Creates a separate server-side session for every assessment.
- Sessions automatically expire after two hours.
- Prevents one student's assessment data from being exposed to another student's session.
- Keeps conversational context associated with the relevant assessment session.

---

## 🛠️ Tech Stack

| Category | Technologies |
|---|---|
| Programming Languages | Python, HTML, CSS, JavaScript |
| Machine Learning | Scikit-learn, Random Forest Regression |
| Data Processing | Pandas, NumPy |
| Model Serialization | Joblib |
| Backend | FastAPI, Uvicorn, Pydantic |
| HTTP Client | HTTPX |
| Generative AI | Anthropic Claude API |
| Knowledge Retrieval | Document-based retrieval from Markdown and text files |
| Frontend | HTML5, CSS3, JavaScript |
| Deployment | Render |
| Version Control | Git, GitHub |

---

## 🤖 Machine Learning Model

The project uses a supervised Machine Learning approach to predict student mental health scores.

**Model:** Random Forest Regression

**Dataset Details:**
- Total Records: 5,000 student records.
- Total Columns: 13.
- Target Variable: `Mental_Health_Score`.
- Input Features: 12.

**Model Performance (Test Dataset):**

| Evaluation Metric | Score |
|---|---:|
| R² Score | 0.878 |
| Mean Absolute Error (MAE) | 0.347 |
| Root Mean Squared Error (RMSE) | 0.464 |

### Model Workflow

1. Load and explore the student survey dataset.
2. Perform data cleaning and preprocessing.
3. Encode categorical variables.
4. Transform and standardize numerical features where applicable.
5. Train the Random Forest Regression model.
6. Evaluate model performance using R², MAE and RMSE.
7. Serialize the trained preprocessing and prediction pipeline using Joblib.
8. Integrate the saved pipeline with the FastAPI backend.

---

## 📂 Project Structure

```text
Mansik-Santulan-Score/
│
├── main.py
│   └── FastAPI application and API endpoints
│
├── wellness.py
│   └── MindWell AI, recommendations, insights,
│       wellness plans, safety and session management
│
├── interpretation_config.json
│   └── Score interpretation bands and thresholds
│
├── knowledge/
│   └── Optional mental wellness reference documents
│
├── Mental_Health_Model.pkl
│   └── Trained Machine Learning pipeline
│
├── ML_Project.ipynb
│   └── Data preprocessing, model training and evaluation
│
├── Student_Social_Media_And_Mental_Health_Impact.csv
│   └── Student survey dataset
│
├── index.html
│   └── Main frontend interface
│
├── script.js
│   └── Frontend logic and API integration
│
├── style.css
│   └── Frontend styling
│
├── ML_Project.html
│   └── Project blueprint and development checklist
│
├── requirements.txt
│   └── Python dependencies
│
└── README.md
    └── Project documentation
```

---

## ⚙️ Installation and Local Setup

### Prerequisites

Make sure you have installed:

- Python 3.10+
- pip
- Git
- VS Code (recommended)

### Step 1: Clone the Repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd Mansik-Santulan-Score
```

### Step 2: Create a Virtual Environment

```bash
python -m venv venv
```

Activate it:

**Windows:**

```bash
venv\Scripts\activate
```

**macOS / Linux:**

```bash
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Start the FastAPI Backend

```bash
uvicorn main:app --port 2200 --reload
```

The backend will be available at:

```text
http://127.0.0.1:2200
```

### Step 5: Launch the Frontend

Open `index.html` using the VS Code Live Server extension.

The frontend communicates with the locally running FastAPI backend.

### Step 6: Access API Documentation

FastAPI automatically generates interactive API documentation.

```text
http://127.0.0.1:2200/docs
```

---

## 🔑 Configure Claude AI (Optional)

MindWell AI supports Anthropic Claude for more contextual and conversational responses.

### Step 1: Generate an Anthropic API Key

Obtain an API key from:

https://console.anthropic.com/

### Step 2: Configure Environment Variables

**Windows PowerShell:**

```powershell
$env:ANTHROPIC_API_KEY="your_api_key_here"
```

Optionally configure the model:

```powershell
$env:WELLNESS_LLM_MODEL="your_supported_claude_model"
```

**macOS / Linux:**

```bash
export ANTHROPIC_API_KEY="your_api_key_here"
export WELLNESS_LLM_MODEL="your_supported_claude_model"
```

Restart the backend after setting the variables.

> If no API key is configured, MindWell AI automatically uses the built-in rule-based assistant.

Never commit API keys or secrets to GitHub.

---

## 🔌 API Documentation

The project provides four primary REST API endpoints.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Checks backend status and AI configuration |
| POST | `/predict` | Predicts the mental health score |
| POST | `/assess` | Generates score, insights, recommendations and wellness plan |
| POST | `/chat` | Provides conversational assistance through MindWell AI |

### 1. Health Check

**Request:**

```http
GET /health
```

Checks whether the model, backend and reference documents are loaded.

### 2. Mental Health Score Prediction

**Request:**

```http
POST /predict
```

**Sample Request Body:**

```json
{
  "age": 21,
  "gender": "Male",
  "country": "India",
  "academic_level": "Undergraduate",
  "most_used_platform": "Instagram",
  "purpose_of_use": "Entertainment",
  "avg_daily_usage_hours": 4.5,
  "daily_unlocks": 150,
  "study_hours": 3,
  "physical_activity_hours": 1.5,
  "sleep_hours_per_night": 6.5,
  "stress_level": "Medium"
}
```

**Sample Response:**

```json
{
  "predicted_mental_health_score": 6.13
}
```

### 3. Complete Mental Wellness Assessment

**Request:**

```http
POST /assess
```

Returns:
- Predicted mental health score.
- Score interpretation.
- Lifestyle insights.
- Personalized recommendations.
- Seven-day wellness plan.
- Unique assessment session ID.

### 4. MindWell AI Chat

**Request:**

```http
POST /chat
```

**Sample Request Body:**

```json
{
  "session_id": "your_session_id",
  "message": "How can I improve my sleep schedule?"
}
```

**Response Structure:**

```json
{
  "reply": "Your personalized AI-generated response...",
  "mode": "claude",
  "sources": []
}
```

The `mode` field identifies whether the response came from Claude or the rule-based fallback assistant.

---

## 📊 Score Interpretation

The project uses a configurable, non-clinical score interpretation framework.

Current proposed score bands:

| Predicted Score | Interpretation |
|---|---|
| Below 5.1 | Lower score band |
| 5.1 – 7.1 | Middle score band |
| Above 7.1 | Higher score band |

The thresholds are based on the training dataset's quartiles and are not clinically validated.

The interpretation configuration is maintained in:

```text
interpretation_config.json
```

The configuration includes score bands, thresholds, explanatory text and an approval flag.

The current configuration uses:

```json
{
  "approved": false
}
```

The bands should undergo appropriate review before being presented as validated interpretations. Their meaning should also be checked against the dataset's actual target-score definition.

---

## 🚀 Deployment on Render

The backend can be deployed using Render.

### Step 1: Push the Project to GitHub

```bash
git add .
git commit -m "Add MindWell AI mental wellness assistant"
git push origin main
```

### Step 2: Create a Render Web Service

1. Visit https://render.com/
2. Create a new Web Service.
3. Connect your GitHub repository.
4. Select the project repository.

### Step 3: Configure Deployment

**Build Command:**

```bash
pip install -r requirements.txt
```

**Start Command:**

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Step 4: Configure Environment Variables

Add the following environment variables if required:

```text
ANTHROPIC_API_KEY=your_api_key
WELLNESS_LLM_MODEL=your_supported_claude_model
```

### Step 5: Deploy

Click Deploy and wait for the build to complete.

**Live Backend:**

https://mansik-santulan-score.onrender.com

---

## ⚠️ Limitations and Future Improvements

### Current Limitations

- Predictions are learned from survey-style data and may not generalize to every student population.
- Model performance metrics reflect the available test dataset, not clinical accuracy.
- What-if predictions represent model associations, not causal effects.
- Score interpretation bands are proposed and require review.
- AI recommendations are general wellness guidance and cannot replace professional care.
- The built-in crisis helpline information supports only selected countries; other users are directed to Find A Helpline.
- Server-side sessions are stored in memory and are lost when the backend restarts.
- The first request on Render's free tier may take longer because the service can sleep when inactive.

### Future Enhancements

- Integration with more validated mental wellness assessment frameworks.
- Long-term student wellness progress tracking.
- Improved AI personalization using assessment history with user consent.
- Multilingual support for Indian students.
- More comprehensive, country-specific crisis support resources.
- Secure persistent session storage.
- Model explainability using SHAP or other feature-attribution techniques.
- Improved accessibility and mobile responsiveness.
- Integration of additional evidence-based mental wellness resources.

---

## 🔐 Privacy and Responsible AI

MindWell is designed with privacy and responsible AI principles in mind.

- Assessment sessions are isolated and automatically expire after two hours.
- Student assessment information should not be exposed across sessions.
- API keys are maintained through environment variables.
- AI-generated responses are intended for educational and wellness-support purposes.
- Predictions must not be treated as medical diagnoses.
- Crisis-related messages receive a dedicated safety response.

---

## 👨‍💻 Author

**Ramji Gupta**

B.Tech – Computer Science and Engineering

Maharaja Surajmal Institute of Technology

**Project:** Mansik Santulan Score – Mental Health Signal + MindWell AI

---

## 📜 License

This project is developed for academic and educational purposes. Add an appropriate open-source license before permitting external reuse or redistribution.

---

⭐ If you find this project interesting, consider giving the repository a star!
