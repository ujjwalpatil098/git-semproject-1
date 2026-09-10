import pandas as pd

# 1. LOAD DATA

df = pd.read_csv(
    "household_power_consumption_upto1M.csv",
    sep=";",
    na_values="?"
)

print("Original shape:")
print(df.shape)

# 2. CHECK THE DATA

print("\nFirst 5 rows:")
print(df.head())

print("\nColumn names:")
print(df.columns)

print("\nData types:")
print(df.dtypes)

print("\nMissing values:")
print(df.isnull().sum())


# 3. REMOVE UNNECESSARY SPACES FROM COLUMNS

df.columns = df.columns.str.strip()

print("\nClean column names:")
print(df.columns)

# 4. CONVERT NUMERIC COLUMNS

numeric_columns = [
    "Global_active_power",
    "Global_reactive_power",
    "Voltage",
    "Global_intensity",
    "Sub_metering_1",
    "Sub_metering_2",
    "Sub_metering_3"
]

for column in numeric_columns:
    df[column] = pd.to_numeric(df[column], errors="coerce")

# 5. CHECK MISSING VALUES AGAIN

print("\nMissing values after conversion:")
print(df.isnull().sum())


# 6. CONVERT DATE AND TIME

df["DateTime"] = pd.to_datetime(
    df["Date"] + " " + df["Time"],
    dayfirst=True,
    errors="coerce"
)

print("\nDateTime column:")
print(df["DateTime"].head())


# 7. CHECK DUPLICATE ROWS

print("\nNumber of duplicate rows:")
print(df.duplicated().sum())

# 8. REMOVE DUPLICATES

df = df.drop_duplicates()

print("\nShape after removing duplicates:")
print(df.shape)

# 9. REMOVE ROWS WITH MISSING VALUES

df = df.dropna()

print("\nShape after removing missing values:")
print(df.shape)

# 10. CHECK FOR INVALID VALUES

print("\nDescriptive statistics:")
print(df[numeric_columns].describe())

# 11. SORT DATA BY DATE

df = df.sort_values("DateTime")

print("\nSorted data:")
print(df.head())

# 12. RESET INDEX

df = df.reset_index(drop=True)

# 13. FINAL CHECK

print("\nFinal shape:")
print(df.shape)

print("\nFinal data types:")
print(df.dtypes)

print("\nFinal missing values:")
print(df.isnull().sum())


# 14. SAVE CLEAN DATA


df.to_csv("cleaned_householddata.csv", index=False)

print("\nData cleaning completed!")
print("Cleaned file saved as: cleaned_householddata.csv")
