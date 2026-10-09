import pandas as pd

# 1. LOAD CLEANED DATASET

df = pd.read_csv("cleaned_householddata.csv")

# 2. DATASET OVERVIEW

print("\n========== DATASET OVERVIEW ==========")
print("Dataset shape:", df.shape)
print("Number of rows:", df.shape[0])
print("Number of columns:", df.shape[1])

# 3. COLUMN INFORMATION

print("\n========== COLUMN INFORMATION ==========")
print(df.info())

print("\nColumn names:")
print(df.columns.tolist())

# 4. MISSING VALUES

print("\n========== MISSING VALUES ==========")
print(df.isnull().sum())

print("\nTotal missing values:", df.isnull().sum().sum())

# 5. DUPLICATE RECORDS

print("\n========== DUPLICATE RECORDS ==========")
print("Duplicate rows:", df.duplicated().sum())

# 6. DATE AND TIME INFORMATION

df["DateTime"] = pd.to_datetime(df["DateTime"], errors="coerce")

print("\n========== DATE AND TIME ==========")
print("Earliest timestamp:", df["DateTime"].min())
print("Latest timestamp:", df["DateTime"].max())
print("Invalid timestamps:", df["DateTime"].isnull().sum())

# 7. STATISTICAL SUMMARY

numeric_columns = df.select_dtypes(include="number").columns

print("\n========== STATISTICAL SUMMARY ==========")
print(df[numeric_columns].describe().round(2))

# 8. FINAL CHECK

print("\n========== EDA INITIAL CHECK COMPLETED ==========")

