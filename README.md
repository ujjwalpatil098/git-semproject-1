# ⚡ Electricity Consumption Analysis Dashboard

> **A data-driven dashboard for analyzing and visualizing household electricity consumption patterns.**

[![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python)](https://www.python.org/)
[![Pandas](https://img.shields.io/badge/Pandas-Data%20Analysis-150458?logo=pandas)](https://pandas.pydata.org/)
[![NumPy](https://img.shields.io/badge/NumPy-Data%20Processing-013243?logo=numpy)](https://numpy.org/)
[![Matplotlib](https://img.shields.io/badge/Matplotlib-Visualization-orange)](https://matplotlib.org/)
[![Seaborn](https://img.shields.io/badge/Seaborn-Visualization-4C72B0)](https://seaborn.pydata.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?logo=streamlit)](https://streamlit.io/)

---

## 📌 About The Project

**Electricity Consumption Analysis Dashboard** is a data analytics project designed to explore and understand household electricity consumption patterns.

The project uses real-world electricity consumption data and applies **data preprocessing, exploratory data analysis (EDA), statistical analysis, and interactive visualization** to transform raw data into meaningful insights.

The final goal is to provide an easy-to-understand dashboard where users can explore electricity consumption trends through interactive charts and filters.

---

## 🎯 Project Objectives

* 🧹 Clean and preprocess raw electricity consumption data.
* 📊 Analyze electricity usage patterns over time.
* 🔍 Identify important trends and variations in consumption.
* 📈 Create meaningful visualizations from the processed data.
* 🎛️ Develop an interactive dashboard for easier exploration.
* 💡 Present data-driven insights in a simple and understandable way.

---

## 📂 Dataset

The project uses household electricity consumption data containing measurements such as:

* Date
* Time
* Global Active Power
* Global Reactive Power
* Voltage
* Global Intensity
* Sub Metering 1
* Sub Metering 2
* Sub Metering 3

The dataset contains missing values represented by `?`, which are handled during the preprocessing stage.

---

## 🧹 Data Preprocessing

Before performing analysis, the raw dataset is cleaned and prepared for further processing.

### Main preprocessing steps:

1. Load the CSV dataset using **Pandas**.
2. Handle missing values.
3. Check dataset shape and column names.
4. Inspect data types.
5. Convert relevant columns into appropriate formats.
6. Prepare the cleaned data for EDA and visualization.

Example:

```python
import pandas as pd

df = pd.read_csv(
    "household_power_consumption_upto1M.csv",
    sep=";",
    na_values="?"
)

print(df.shape)
print(df.head())
print(df.dtypes)
```

---

## 🔍 Exploratory Data Analysis

After preprocessing, **Exploratory Data Analysis (EDA)** will be performed to understand the dataset and identify useful patterns.

The analysis will focus on:

* 📅 Daily electricity consumption
* ⏰ Consumption according to time
* 📊 Power consumption trends
* ⚡ Voltage and current variations
* 🏠 Sub-metering consumption
* 📈 Peak and low consumption periods
* 🔗 Relationships between different variables

Visualization libraries such as **Matplotlib** and **Seaborn** will be used to represent the findings graphically.

---

## 📊 Dashboard

The final project will provide an interactive **Streamlit dashboard**.

### Planned dashboard features:

* 📌 Overall consumption summary
* 📈 Time-based consumption trends
* 📊 Interactive charts
* 🔎 Date/time filtering
* ⚡ Power and voltage analysis
* 🏠 Sub-metering comparison
* 💡 Key insights from the data

> 🚧 **Dashboard is currently under development.**

---

## 🛠️ Technologies Used

| Technology      | Purpose                           |
| --------------- | --------------------------------- |
| 🐍 Python       | Data processing and analysis      |
| 🐼 Pandas       | Data cleaning and manipulation    |
| 🔢 NumPy        | Numerical operations              |
| 📊 Matplotlib   | Data visualization                |
| 🎨 Seaborn      | Statistical visualization         |
| 🖥️ Streamlit   | Interactive dashboard             |
| 🗄️ SQL         | Data storage/query integration    |
| 🔧 Git & GitHub | Version control and collaboration |

---

## 📁 Project Structure

```text
Electricity-Consumption-Analysis/
│
├── 📂 data/
│   └── household_power_consumption_upto1M.csv
│
├── 📂 preprocessing/
│   └── data_preprocessing.py
│
├── 📂 eda/
│   └── exploratory_data_analysis.py
│
├── 📂 dashboard/
│   └── app.py
│
├── 📄 requirements.txt
├── 📄 README.md
└── 📄 .gitignore
```

> The folder structure may be updated as the project develops.

---

## 🚀 How To Run The Project

### 1️⃣ Clone the repository

```bash
git clone <YOUR-GITHUB-REPOSITORY-LINK>
```

### 2️⃣ Open the project folder

```bash
cd Electricity-Consumption-Analysis
```

### 3️⃣ Install required libraries

```bash
pip install -r requirements.txt
```

### 4️⃣ Run the Streamlit dashboard

```bash
streamlit run dashboard/app.py
```

The dashboard will then open in your browser.

---

## 📈 Project Workflow

```text
Raw Dataset
     ↓
Data Loading
     ↓
Data Cleaning
     ↓
Data Preprocessing
     ↓
Exploratory Data Analysis
     ↓
Data Visualization
     ↓
SQL Integration
     ↓
Streamlit Dashboard
     ↓
Insights & Analysis
```

---

## 💡 Expected Outcomes

The project aims to provide useful insights such as:

* Identifying periods of high electricity consumption.
* Understanding consumption patterns throughout the day.
* Comparing different household sub-metering values.
* Observing changes in power, voltage, and current.
* Making electricity consumption data easier to understand through visualization.

---

## 🔮 Future Scope

Possible future improvements include:

* 🤖 Electricity consumption prediction using Machine Learning.
* 📅 Forecasting future energy requirements.
* 🚨 Detecting unusual consumption patterns.
* 📱 Improving dashboard accessibility.
* ☁️ Deploying the dashboard online.
* 🔄 Connecting the dashboard to live or regularly updated data.

---

## 👥 Team

This project is developed as a collaborative academic project.

| Member         | Role                       |
| -------------- | -------------------------- |
| 👨‍💻 Member 1 | Data Processing & Analysis |
| 👨‍💻 Member 2 | EDA & Visualization        |
| 👨‍💻 Member 3 | SQL & Data Integration     |
| 👨‍💻 Member 4 | Streamlit Dashboard        |

> Team roles may evolve as the project progresses.

---

## 📸 Dashboard Preview

> 🚧 Screenshots will be added after the dashboard is completed.

---

## ⭐ Project Status

**🟡 In Development**

Current progress:

* [x] Dataset collection
* [x] Dataset loading
* [x] Initial data inspection
* [x] Data preprocessing
* [ ] Exploratory Data Analysis
* [ ] Data visualization
* [ ] SQL integration
* [ ] Streamlit dashboard
* [ ] Final testing
* [ ] Deployment

---

## 🤝 Contributing

This project is developed as a collaborative academic project.

Team members can contribute by working on their assigned branches and creating **Pull Requests** for merging completed work into the main branch.

---

## 📜 License

This project is created for **educational and academic purposes**.

---

<p align="center">
  ⚡ <b>Electricity Consumption Analysis Dashboard</b> ⚡
  <br>
  Turning raw electricity data into meaningful insights.
</p>
