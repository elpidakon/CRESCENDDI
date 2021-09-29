# Kontsioti, Maskell, Dutta & Pirmohamed, A reference set of clinically relevant
# adverse drug-drug interactions (2021)
# This script maps event names (i.e. ADRs and indications) from SIDER data to
# normalised OHDSI concepts (MedDRA concepts)

import pandas as pd
import numpy as np
import psycopg2
from sqlalchemy import create_engine
import csv
import os
import warnings

# Connect to PostgreSQL
# Replace with your PostgreSQL credentials
engine = create_engine("postgresql://username:password@host:port/database")

conn = psycopg2.connect("dbname=database user=username")
cur = conn.cursor()

### Data file loading and dictionary generation

# UMLS to MedDRA mappings
UMLS_to_MedDRA = pd.read_csv(
    "data_extraction/data/SIDER/meddra.tsv",
    names=["UMLS_code", "MedDRA_type", "MedDRA_code", "MedDRA_name"],
    sep="\t",
)
# SIDER side effect and indication tables
# Drug side effects
drug_se = pd.read_csv(
    "drug_mapping/output/SIDER_side_effects_with_mapped_drugnames.csv"
)
# Drug indications
drug_indications = pd.read_csv(
    "drug_mapping/output/SIDER_indications_with_mapped_drugnames.csv"
)

# A dictionary with MedDRA name - MedDRA code mappings
MedDRA_name_to_MedDRA_code_dict = dict(
    zip(UMLS_to_MedDRA.MedDRA_name, UMLS_to_MedDRA.MedDRA_code)
)
# Some codes are the same for the LLT and PT level; this is why the number of
# elements in the created dictionary is less compared to the total number of
# rows in the df.

# A dictionary with all MedDRA codes mapped to their standardised OHDSI concepts
cur.execute(
    "SELECT concept_id, concept_name, concept_code, concept_class_id FROM cdmv5.concept \
WHERE vocabulary_id = 'MedDRA';"
)
row_1 = cur.fetchall()
cols_1 = ["OHDSI_concept_id", "concept_name", "MedDRA_code", "MedDRA_type"]
meddra_df = pd.DataFrame(row_1).astype(str)
meddra_df.columns = cols_1
meddra_dict = dict(zip(meddra_df.MedDRA_code, meddra_df.OHDSI_concept_id))

# A dictionary with concept_id to concept_name values for Drugs
cur.execute(
    "select c.concept_id, c.concept_name from cdmv5.concept c \
            where c.concept_class_id = 'Ingredient';"
)
row_2 = cur.fetchall()
drug_concept_id_to_name_df = pd.DataFrame(row_2).astype(str)
drug_concept_id_to_name_df.set_index(0, inplace=True)
drug_concept_id_to_name_dict = drug_concept_id_to_name_df[1].to_dict()

# A dictionary with concept_id to concept_name values for Events
cur.execute(
    "select c.concept_id, c.concept_name from cdmv5.concept c \
            where c.vocabulary_id = 'MedDRA';"
)
row_3 = cur.fetchall()
event_concept_id_to_name_df = pd.DataFrame(row_3).astype(str)
event_concept_id_to_name_df.set_index(0, inplace=True)
event_concept_id_to_name_dict = event_concept_id_to_name_df[1].to_dict()


### A. SIDE EFFECTS

# Create a dictionary with mappings of events from the side effects table to
# their corresponding OHDSI MedDRA concepts (any level)

# Mapping se_name to its corresponding OHDSI concept id
# Create a dataframe that contains all unique events related to side effects
# from the side effects table
se_names_df = drug_se.drop_duplicates(["se_name", "MedDRA_type"])[
    ["se_name", "MedDRA_type"]
]
# Get the MedDRA code using the event name column
se_names_df["MedDRA_code"] = (
    se_names_df["se_name"].map(MedDRA_name_to_MedDRA_code_dict).astype(str)
)
# Then, map the MedDRA code to its corresponding OHDSI concept
se_names_df["se_concept_id"] = se_names_df["MedDRA_code"].map(meddra_dict).astype(str)
se_names_df = se_names_df.sort_values(
    by=["MedDRA_type"], ascending=False
).drop_duplicates(["se_name", "se_concept_id"])
se_names_df.set_index("se_name", inplace=True)

# Then, map any LLT MedDRA concepts that appear in the side effects table to
# their corresponding PT concepts

# Create a separate dataframe containing only the LLTs from the side effects table
LLTs_from_se = se_names_df[se_names_df["MedDRA_type"] == "LLT"]
# Create two extra empty columns for mapping LLTs to their ancestor concepts (PT level)
LLTs_from_se["PT_se_concept_id"] = ""
LLTs_from_se["PT_se_concept_name"] = ""

warnings.filterwarnings("ignore")

# Map the LLT terms to PT terms using the relevant PostgreSQL table
for index, row in LLTs_from_se.iterrows():
    cur.execute(
        "SELECT ancestor_concept_id FROM cdmv5.concept_ancestor WHERE \
    descendant_concept_id = (%s) AND max_levels_of_separation = 1 AND min_levels_of_separation = 1;",
        [row["se_concept_id"]],
    )
    pt_id = cur.fetchall()
    # If the ancestor (PT) concept is found
    if len(pt_id) != 0:
        LLTs_from_se.at[index, "PT_se_concept_id"] = str(pt_id[0][0])
        cur.execute(
            "SELECT concept_name FROM cdmv5.concept WHERE concept_id = (%s);",
            [pt_id[0]],
        )
        pt_name = cur.fetchall()
        LLTs_from_se.at[index, "PT_se_concept_name"] = pt_name[0][0]
# Replace the rows that were left unmapped with NaN
LLTs_from_se.replace("", np.nan, inplace=True)

# Export LLTs that are currently invalid (i.e. did not get mapped using the above
# process) to a CSV file for manual mapping to valid OHDSI MedDRA PT concepts
LLTs_from_se[LLTs_from_se.PT_se_concept_id.isnull()].sort_values(by="se_name").to_csv(
    "event_mapping/data/invalid_LLT_concepts_SIDER_se_for_mapping.csv"
)

############ MANUAL MAPPING USING USAGI ######################################

# After manual mapping is performed, the updated CSV file is reloaded and the
# invalid LLT terms are mapped to valid OHDSI MedDRA PT concepts
invalid_LLT_se_mappings = pd.read_csv(
    "event_mapping/data/sider_invalid_adr_eventnames.csv", index_col=0, dtype=str
)
LLTs_from_se = LLTs_from_se.fillna(invalid_LLT_se_mappings)
# Convert the LLT - PT mapping table to a dictionary
LLT_to_PT_se_dict = dict(
    zip(LLTs_from_se["se_concept_id"], LLTs_from_se["PT_se_concept_id"])
)

# Map side effects in the SIDER ADR table
# Use the first dictionary for side effects to get OHDSI MedDRA concept mappings (any level)
drug_se["OHDSI_se_id"] = drug_se["se_name"].map(se_dict)
# Use the LLT to PT dictionary for side effects to map any LLTs to their ancestor (PT) concepts
drug_se["OHDSI_PT_se_concept_id"] = drug_se["OHDSI_se_id"].map(LLT_to_PT_se_dict)
# For concepts that were already at the PT level, simply copy the PT code to the new column
drug_se["OHDSI_PT_se_concept_id"].fillna(drug_se["OHDSI_se_id"], inplace=True)

# During the drug mapping process, STITCH codes were mapped to one or multiple
# OHDSI RxNorm/RxNormExtension Ingredient concepts.
# Thus, 'OHDSI_drug_id' column in the above dataframe contains rows with one or
# more mapped concepts. We will create a final version of the side effects table
# by 'exploding' rows with multiple mapped drug concepts into separate rows and
# only keeping the columns of interest

se_sider_df = drug_se.explode("OHDSI_drug_id")
# Drop rows with unmapped drug names
se_sider_df = se_sider_df[se_sider_df["OHDSI_drug_id"].notnull()].reset_index(drop=True)
# Keep only drug and (PT) side effect concept ID columns
se_sider_df = se_sider_df[["OHDSI_drug_id", "OHDSI_PT_se_concept_id"]]
## Map to their corresponding concept names
se_sider_df["DRUG_CONCEPT_NAME"] = se_sider_df["OHDSI_drug_id"].map(
    drug_concept_id_to_name_dict
)
se_sider_df["EVENT_CONCEPT_NAME"] = se_sider_df["OHDSI_PT_se_concept_id"].map(
    event_concept_id_to_name_dict
)
# Rename columns
se_sider_df.columns = [
    "DRUG_CONCEPT_ID",
    "EVENT_CONCEPT_ID",
    "DRUG_CONCEPT_NAME",
    "EVENT_CONCEPT_NAME",
]
# Drop any duplicated rows
se_sider_df = se_sider_df.drop_duplicates().set_index("DRUG_CONCEPT_ID")
# Export to a CSV
se_sider_df.to_csv("event_mapping/output/sider_adr_table.csv")

### B. INDICATIONS

# Create a dictionary with mappings of events from the indications table to
# their corresponding OHDSI MedDRA concepts (any level)
# Mapping indication_name to its corresponding OHDSI concept id
# Create a dataframe that contains all unique events related to indications
# from the indications table
indication_names_df = drug_indications.drop_duplicates(
    ["indication_name", "MedDRA_type"]
)[["indication_name", "MedDRA_type"]]
# Get the MedDRA code using the event name column
indication_names_df["MedDRA_code"] = (
    indication_names_df["indication_name"]
    .map(MedDRA_name_to_MedDRA_code_dict)
    .astype(str)
)
# Then, map the MedDRA code to its corresponding OHDSI concept
indication_names_df["indication_concept_id"] = (
    indication_names_df["MedDRA_code"].map(meddra_dict).astype(str)
)
indication_names_df = indication_names_df.sort_values(
    by=["MedDRA_type"], ascending=False
).drop_duplicates(["indication_name", "indication_concept_id"])
indication_names_df.set_index("indication_name", inplace=True)
# Convert the dataframe into a dictionary
indication_dict = dict(
    zip(indication_names_df.index, indication_names_df.indication_concept_id)
)

# Then, map any LLT MedDRA concepts that appear in the indications table to
# their corresponding PT concepts
# Create a separate dataframe containing only the LLTs from the indications table
LLTs_from_indications = indication_names_df[indication_names_df["MedDRA_type"] == "LLT"]
# Create two extra empty columns for mapping LLTs to their ancestor concepts (PT level)
LLTs_from_indications["PT_indication_concept_id"] = ""
LLTs_from_indications["PT_indication_concept_name"] = ""

warnings.filterwarnings("ignore")

# Map the LLT terms to PT terms using the relevant PostgreSQL table
for index, row in LLTs_from_indications.iterrows():
    cur.execute(
        "SELECT ancestor_concept_id FROM cdmv5_with_read_codes.concept_ancestor \
        WHERE descendant_concept_id = (%s) \
        AND max_levels_of_separation = 1 AND min_levels_of_separation = 1;",
        [row["indication_concept_id"]],
    )
    pt_id = cur.fetchall()
    # If the ancestor (PT) concept is found
    if len(pt_id) != 0:
        LLTs_from_indications.at[index, "PT_indication_concept_id"] = str(pt_id[0][0])
        cur.execute(
            "SELECT concept_name FROM cdmv5_with_read_codes.concept \
            WHERE concept_id = (%s);",
            [pt_id[0]],
        )
        pt_name = cur.fetchall()
        LLTs_from_indications.at[index, "PT_indication_concept_name"] = pt_name[0][0]
# Replace the rows that were left unmapped with NaN
LLTs_from_indications.replace("", np.nan, inplace=True)

# Export LLTs that are currently invalid (i.e. did not get mapped using the
# above process) to a CSV file for manual mapping to valid OHDSI MedDRA PT concepts
LLTs_from_indications[
    LLTs_from_indications.PT_indication_concept_id.isnull()
].sort_values(by="indication_name").to_csv(
    "event_mapping/data/invalid_LLT_concepts_SIDER_indi_for_mapping.csv"
)

################ MANUAL MAPPING USING USAGI ##################################

# After manual mapping is performed, the updated CSV file is reloaded and the
# invalid LLT terms are mapped to valid OHDSI MedDRA PT concepts
invalid_LLT_indication_mappings = pd.read_csv(
    "event_mapping/data/sider_invalid_indi_eventnames.csv", index_col=0, dtype=str
)
LLTs_from_indications = LLTs_from_indications.fillna(invalid_LLT_indication_mappings)
# convert the LLT - PT mapping table to a dictionary
LLT_to_PT_indication_dict = dict(
    zip(
        LLTs_from_indications["indication_concept_id"],
        LLTs_from_indications["PT_indication_concept_id"],
    )
)

# Map indications in the SIDER Indications table
# Use the first dictionary for indications to get OHDSI MedDRA concept mappings (any level)
drug_indications["OHDSI_indication_id"] = drug_indications["indication_name"].map(
    indication_dict
)
# Use the LLT to PT dictionary for indications to map any LLTs to their ancestor (PT) concepts
drug_indications["OHDSI_PT_indication_concept_id"] = drug_indications[
    "OHDSI_indication_id"
].map(LLT_to_PT_indication_dict)
# For concepts that were already at the PT level, simply copy the PT code to the new column
drug_indications["OHDSI_PT_indication_concept_id"].fillna(
    drug_indications["OHDSI_indication_id"], inplace=True
)

# Similarly to the previous table for side effects, we will 'explode' rows with
# multiple mapped drug concepts into separate rows and
# keep only the columns of interest

indications_sider_df = drug_indications.explode("OHDSI_drug_id")
# Drop rows with unmapped drug names
indications_sider_df = indications_sider_df[
    indications_sider_df["OHDSI_drug_id"].notnull()
].reset_index(drop=True)
# Keep only drug and (PT) indication concept ID columns
indications_sider_df = indications_sider_df[
    ["OHDSI_drug_id", "OHDSI_PT_indication_concept_id"]
]
## Map to their corresponding concept names
indications_sider_df["DRUG_CONCEPT_NAME"] = indications_sider_df["OHDSI_drug_id"].map(
    drug_concept_id_to_name_dict
)
indications_sider_df["EVENT_CONCEPT_NAME"] = indications_sider_df[
    "OHDSI_PT_indication_concept_id"
].map(event_concept_id_to_name_dict)
# Rename columns
indications_sider_df.columns = [
    "DRUG_CONCEPT_ID",
    "EVENT_CONCEPT_ID",
    "DRUG_CONCEPT_NAME",
    "EVENT_CONCEPT_NAME",
]
# Drop any duplicated rows
indications_sider_df = indications_sider_df.drop_duplicates().set_index(
    "drug_concept_id"
)
# Export to a CSV
indications_sider_df.to_csv("event_mapping/output/sider_indi_table.csv")
