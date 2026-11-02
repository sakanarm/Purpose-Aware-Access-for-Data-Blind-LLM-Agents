"""Step 1 - Data preparation.

Turns seven public healthcare tables into a common format:
  * one row per record, one column per *resource* (an attribute a user can be granted),
  * a hidden patient key used only for computing re-identification ground truth,
  * a data catalog that assigns every resource a HIPAA-style semantic type.

Semantic types (HIPAA Safe Harbor, 45 CFR 164.514(b)):
  direct_id   - identifies a person on its own (name, SSN, MRN, address, ...)
  quasi_id    - externally knowable, identifying in combination (age, sex, race, ZIP, dates)
  clinical    - sensitive health content (diagnosis, medication, lab, procedure)
  financial   - sensitive financial content (billing, payer, cost)
  operational - workflow data that is not externally linkable (room, provider, admission source)

Output: data_clean/<name>.pkl  (DataFrame) and data_clean/catalog.json
"""
import json, os, sys
import numpy as np, pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW, OUT = f"{ROOT}/data_raw", f"{ROOT}/data_clean"
os.makedirs(OUT, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8")


def clean_text(s):
    return s.astype(str).str.strip().str.lower().replace({"nan": np.nan, "?": np.nan, "": np.nan})


# --------------------------------------------------------------------------- Kaggle healthcare (prasad22)
def prep_kaggle():
    df = pd.read_csv(f"{RAW}/kaggle_healthcare/healthcare_dataset.csv")
    df.columns = [c.lower().replace(" ", "_") for c in df.columns]
    for c in ["name", "doctor", "hospital"]:
        df[c] = clean_text(df[c])                       # names have random casing ("Bobby JacksOn")
    df["billing_amount"] = df["billing_amount"].round(2)
    n0 = len(df)
    df = df.drop_duplicates().reset_index(drop=True)   # exact duplicate rows exist in this dataset
    df["_pid"] = np.arange(len(df))                    # one row = one admission of one patient
    types = {
        "name": "direct_id", "age": "quasi_id", "gender": "quasi_id",
        "date_of_admission": "quasi_id", "discharge_date": "quasi_id",
        "blood_type": "clinical", "medical_condition": "clinical", "admission_type": "clinical",
        "medication": "clinical", "test_results": "clinical",
        "insurance_provider": "financial", "billing_amount": "financial",
        "doctor": "operational", "hospital": "operational", "room_number": "operational",
    }
    return df, types, {"rows_raw": n0, "dropped_duplicates": n0 - len(df)}


# --------------------------------------------------------------------------- Diabetes 130-US hospitals
def prep_diabetes():
    df = pd.read_csv(f"{RAW}/diabetes130/diabetic_data.csv", na_values=["?"], low_memory=False)
    n0 = len(df)
    meds = ["metformin", "repaglinide", "nateglinide", "glimepiride", "glipizide", "glyburide",
            "pioglitazone", "rosiglitazone", "acarbose", "insulin", "glyburide-metformin"]
    dropped_const = [c for c in df.columns if df[c].nunique(dropna=True) <= 1]   # examide, citoglipton
    df = df.drop(columns=dropped_const)
    df["_pid"] = df["patient_nbr"]
    types = {
        "encounter_id": "direct_id", "patient_nbr": "direct_id",                  # record / medical record numbers
        "race": "quasi_id", "gender": "quasi_id", "age": "quasi_id", "weight": "quasi_id",
        "payer_code": "financial",
        "admission_type_id": "operational", "discharge_disposition_id": "operational",
        "admission_source_id": "operational", "medical_specialty": "operational",
        "time_in_hospital": "clinical", "num_lab_procedures": "clinical", "num_procedures": "clinical",
        "num_medications": "clinical", "number_outpatient": "clinical", "number_emergency": "clinical",
        "number_inpatient": "clinical", "number_diagnoses": "clinical",
        "diag_1": "clinical", "diag_2": "clinical", "diag_3": "clinical",
        "max_glu_serum": "clinical", "A1Cresult": "clinical", "change": "clinical",
        "diabetesMed": "clinical", "readmitted": "clinical",
        **{m: "clinical" for m in meds},
    }
    df = df[list(types) + ["_pid"]]
    df.columns = [c.lower().replace("-", "_") for c in df.columns]
    types = {k.lower().replace("-", "_"): v for k, v in types.items()}
    return df, types, {"rows_raw": n0, "dropped_constant_cols": dropped_const}


# --------------------------------------------------------------------------- Synthea (encounter level)
def prep_synthea():
    d = f"{RAW}/synthea/csv"
    pat = pd.read_csv(f"{d}/patients.csv")
    enc = pd.read_csv(f"{d}/encounters.csv")
    pay = pd.read_csv(f"{d}/payers.csv")[["Id", "NAME"]].rename(columns={"Id": "PAYER", "NAME": "payer_name"})
    org = pd.read_csv(f"{d}/organizations.csv")[["Id", "NAME"]].rename(columns={"Id": "ORGANIZATION", "NAME": "organization"})
    con = pd.read_csv(f"{d}/conditions.csv").groupby("ENCOUNTER")["DESCRIPTION"].first().rename("condition")
    med = pd.read_csv(f"{d}/medications.csv").groupby("ENCOUNTER")["DESCRIPTION"].first().rename("medication")
    df = (enc.merge(pat, left_on="PATIENT", right_on="Id", suffixes=("", "_p"))
             .merge(pay, on="PAYER", how="left").merge(org, on="ORGANIZATION", how="left")
             .merge(con, left_on="Id", right_index=True, how="left")
             .merge(med, left_on="Id", right_index=True, how="left"))
    df["encounter_date"] = df["START"].str[:10]
    df["birth_year"] = df["BIRTHDATE"].str[:4]
    df["_pid"] = df["PATIENT"]
    keep = {
        "SSN": "direct_id", "DRIVERS": "direct_id", "PASSPORT": "direct_id", "FIRST": "direct_id",
        "LAST": "direct_id", "MAIDEN": "direct_id", "ADDRESS": "direct_id",
        "BIRTHDATE": "quasi_id", "birth_year": "quasi_id", "GENDER": "quasi_id", "RACE": "quasi_id",
        "ETHNICITY": "quasi_id", "MARITAL": "quasi_id", "BIRTHPLACE": "quasi_id", "CITY": "quasi_id",
        "COUNTY": "quasi_id", "ZIP": "quasi_id", "encounter_date": "quasi_id", "DEATHDATE": "quasi_id",
        "ENCOUNTERCLASS": "clinical", "DESCRIPTION": "clinical", "REASONDESCRIPTION": "clinical",
        "condition": "clinical", "medication": "clinical",
        "BASE_ENCOUNTER_COST": "financial", "TOTAL_CLAIM_COST": "financial", "PAYER_COVERAGE": "financial",
        "HEALTHCARE_EXPENSES": "financial", "HEALTHCARE_COVERAGE": "financial", "payer_name": "financial",
        "organization": "operational", "PROVIDER": "operational",
    }
    df = df[list(keep) + ["_pid"]].copy()
    df["ZIP"] = df["ZIP"].astype("Int64").astype(str).str.zfill(5).replace({"<NA>": np.nan, "00<NA>": np.nan})
    df.columns = [c.lower() for c in df.columns]
    keep = {k.lower(): v for k, v in keep.items()}
    return df, keep, {"patients": int(pat.shape[0]), "encounters": int(enc.shape[0])}


# --------------------------------------------------------------------------- Stroke prediction (fedesoriano)
def prep_stroke():
    df = pd.read_csv(f"{RAW}/stroke/healthcare-dataset-stroke-data.csv")
    df.columns = [c.lower() for c in df.columns]
    df["bmi"] = pd.to_numeric(df["bmi"], errors="coerce")
    df["_pid"] = df["id"]                              # one row = one patient
    types = {
        "id": "direct_id",
        "gender": "quasi_id", "age": "quasi_id", "ever_married": "quasi_id", "work_type": "quasi_id",
        "residence_type": "quasi_id",
        "hypertension": "clinical", "heart_disease": "clinical", "avg_glucose_level": "clinical",
        "bmi": "clinical", "smoking_status": "clinical", "stroke": "clinical",
    }
    return df, types, {"rows_raw": len(df)}


# --------------------------------------------------------------------------- Medical cost personal (mirichoi0218)
def prep_insurance():
    df = pd.read_csv(f"{RAW}/insurance/insurance.csv")
    n0 = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    df["_pid"] = np.arange(len(df))                    # no identifier column: risk comes only from quasi-ids
    types = {"age": "quasi_id", "sex": "quasi_id", "children": "quasi_id", "region": "quasi_id",
             "bmi": "clinical", "smoker": "clinical", "charges": "financial"}
    return df, types, {"rows_raw": n0, "dropped_duplicates": n0 - len(df)}


# --------------------------------------------------------------------------- WiDS 2020 ICU patient survival
def prep_icu():
    df = pd.read_csv(f"{RAW}/icu/dataset.csv")
    df["_pid"] = df["patient_id"]
    clinical = ["bmi", "pre_icu_los_days", "apache_2_diagnosis", "apache_3j_diagnosis", "apache_post_operative",
                "arf_apache", "intubated_apache", "ventilated_apache", "heart_rate_apache", "map_apache",
                "temp_apache", "d1_glucose_max", "d1_potassium_max", "aids", "cirrhosis", "diabetes_mellitus",
                "hepatic_failure", "immunosuppression", "leukemia", "lymphoma", "solid_tumor_with_metastasis",
                "apache_3j_bodysystem", "apache_4a_hospital_death_prob", "hospital_death"]
    types = {"encounter_id": "direct_id", "patient_id": "direct_id",
             "age": "quasi_id", "gender": "quasi_id", "ethnicity": "quasi_id", "height": "quasi_id", "weight": "quasi_id",
             "hospital_id": "operational", "icu_id": "operational", "icu_admit_source": "operational",
             "icu_stay_type": "operational", "icu_type": "operational", "elective_surgery": "operational",
             **{c: "clinical" for c in clinical}}
    return df, types, {"rows_raw": len(df), "columns_raw": df.shape[1] - 1, "columns_kept": len(types)}


# --------------------------------------------------------------------------- CDC BRFSS 2015 diabetes indicators
BRFSS_SAMPLE = 5000


def prep_brfss():
    df = pd.read_csv(f"{RAW}/brfss/diabetes_012_health_indicators_BRFSS2015.csv")
    n0 = len(df)
    # 253k respondents make every quasi-id class large (k-anonymous); a 5,000-respondent sample emulates the
    # release of a regional registry, where combinations of coarse demographics become identifying.
    df = df.sample(BRFSS_SAMPLE, random_state=0).reset_index(drop=True)
    df.columns = [c.lower() for c in df.columns]
    df["_pid"] = np.arange(len(df))
    clinical = ["diabetes_012", "highbp", "highchol", "cholcheck", "bmi", "smoker", "stroke", "heartdiseaseorattack",
                "physactivity", "fruits", "veggies", "hvyalcoholconsump", "genhlth", "menthlth", "physhlth", "diffwalk"]
    types = {"sex": "quasi_id", "age": "quasi_id", "education": "quasi_id", "income": "quasi_id",
             "anyhealthcare": "financial", "nodocbccost": "financial", **{c: "clinical" for c in clinical}}
    return df, types, {"rows_raw": n0, "sampled": BRFSS_SAMPLE}


if __name__ == "__main__":
    catalog = {}
    for name, fn in [("kaggle", prep_kaggle), ("diabetes", prep_diabetes), ("synthea", prep_synthea),
                     ("stroke", prep_stroke), ("insurance", prep_insurance), ("icu", prep_icu), ("brfss", prep_brfss)]:
        df, types, info = fn()
        cols = list(types)
        assert all(c in df.columns for c in cols), [c for c in cols if c not in df.columns]
        df.to_pickle(f"{OUT}/{name}.pkl")
        catalog[name] = {"resources": cols, "types": types, "n_rows": int(len(df)),
                         "n_patients": int(df["_pid"].nunique()), "prep": info}
        cnt = pd.Series(types).value_counts().to_dict()
        print(f"[{name}] rows={len(df):,} patients={df['_pid'].nunique():,} resources={len(cols)} types={cnt} info={info}")
    json.dump(catalog, open(f"{OUT}/catalog.json", "w"), indent=2, default=str)
