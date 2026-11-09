# AquaGuard AI Full Website (VS Code)

Is project mein Login, Signup, Dashboard, New Prediction, History, Analytics, Profile aur Settings pages hain. Frontend HTML/CSS/JavaScript mein hai. Flask sirf login/session/database aur trained `.joblib` model ko API ke through connect karne ke liye use hota hai. Streamlit use nahi hota.

## 1. ZIP extract aur VS Code mein open
ZIP extract karo, phir VS Code > File > Open Folder se `aquaguard_ai_full_website` kholo.

## 2. Model file copy karo
Jupyter mein bani `aquaguard_ai_model.joblib` ko project ke root folder mein copy karo, jahan `app.py` hai. Model file ZIP mein included nahi hai.

## 3. VS Code terminal
`Terminal > New Terminal` kholo. Windows par (project folder ke andar):

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Agar activation block ho, virtual environment activate karna skip karke commands ke liye `.venv\Scripts\python.exe -m pip install -r requirements.txt` aur `.venv\Scripts\python.exe app.py` use kar sakte ho.

## 4. Website run
```powershell
python app.py
```
Browser mein `http://127.0.0.1:5000` kholo. Server chal raha ho tabhi website kaam karegi. Band karne ke liye terminal mein Ctrl+C.

## 5. First use
- Sign up par name, email, aur 8+ character password enter karo.
- Login karo.
- Dashboard par jao; sidebar se New Prediction, History, Analytics, Profile, Settings open kar sakte ho.
- New Prediction mein apne water-test parameters enter karke Run AI Analysis click karo.
- Har successful prediction account-specific SQLite database (`aquaguard.db`) mein save hoti hai.

## 6. Agar model offline ho
- `aquaguard_ai_model.joblib` app.py ke same folder mein hai?
- Terminal error check karo.
- scikit-learn version mismatch ho sakta hai. Jupyter mein `import sklearn; print(sklearn.__version__)` chalao aur compatible version install karo.
- Joblib/pickle file sirf apne trusted model se load karo.

## Important security notes
- Ye local-development starter hai, production-ready auth system nahi. Public deployment se pehle secret key ko environment variable mein set karo, CSRF protection, rate limiting, HTTPS, account recovery, secure production server, and proper database hardening add karo.
- Local development server ko public internet par expose mat karo.
- Model class 0/1 aur probabilities dataset-based estimates hain, drinking-water safety certification nahi. Accredited lab test zaroori hai.
- Training pipeline ki feature names aur order isi API ke FEATURES list se match hone chahiye.
- Probability output tabhi aayega jab trained model `predict_proba` support karta ho.


## Visual refresh (RevenuePulse reference)
Is version mein navy/blue analytics-console look, luminous cards, active sidebar, gradient buttons aur responsive polish add ki gayi hai. Existing login/signup, dashboard, prediction API, history, analytics, profile aur settings templates/routes ko preserve kiya gaya hai. `aquaguard_ai_model.joblib` model file ZIP mein included nahi hai—apni existing model file ko `app.py` ke same folder mein rakhein. Apne current project ko overwrite karne se pehle backup zaroor banayein.
