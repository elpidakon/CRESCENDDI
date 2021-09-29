# Kontsioti, Maskell, Dutta & Pirmohamed, A reference set of clinically relevant 
# adverse drug-drug interactions (2021)
# Script to generate positive controls for DDIs using the intersection table of 
# the three resources together with event mappings for BNF and Micromedex 
# text descriptions

import pandas as pd
import numpy as np
import psycopg2
from itertools import chain, combinations, product
import operator
import random
from collections import Counter
import gc
from sqlalchemy import create_engine
from nltk.tokenize import sent_tokenize, word_tokenize
from itertools import chain
import itertools, random
import csv
import re
import string
import pandas.io.sql as pdsql
import Bio
from Bio import Entrez
import pandas as pd
import matplotlib.pyplot as plt
import time

## Replace with PostgreSQL credentials
engine = create_engine("postgresql://username:password@host:port/database")

conn = psycopg2.connect("dbname=database user=username")
cur = conn.cursor()

## Generate dictionaries to help with MedDRA mappings

# Get LLT to PT mapping dictionary
cur.execute(
    "select c.concept_id, c.concept_name, c.concept_code, \
    ca.ancestor_concept_id from cdmv5.concept c \
    join cdmv5.concept_ancestor ca on c.concept_id = ca.descendant_concept_id \
    where c.vocabulary_id = 'MedDRA' and c.concept_class_id = 'LLT' \
    and ca.min_levels_of_separation = 1 \
    and ca.max_levels_of_separation = 1;"
)
row_2 = cur.fetchall()
LLT_to_PT_df = pd.DataFrame(row_2).astype(str)
LLT_to_PT_df.set_index(0, inplace=True)
LLT_to_PT_dict = LLT_to_PT_df[3].to_dict()

# PT id to PT name dictionary
cur.execute(
    "select c.concept_id, c.concept_name from cdmv5.concept c \
            where c.vocabulary_id = 'MedDRA' and c.concept_class_id = 'PT';"
)
row_3 = cur.fetchall()
PT_id_to_name_df = pd.DataFrame(row_3).astype(str)
PT_id_to_name_df.set_index(0, inplace=True)
PT_id_to_name_dict = PT_id_to_name_df[1].to_dict()

# PT id to MedDRA code dictionary
cur.execute(
    "select c.concept_id, c.concept_code from cdmv5.concept c \
            where c.vocabulary_id = 'MedDRA' and c.concept_class_id = 'PT';"
)
row_4 = cur.fetchall()
PT_id_to_code_df = pd.DataFrame(row_4).astype(str)
PT_id_to_code_df.set_index(0, inplace=True)
PT_id_to_code_dict = PT_id_to_code_df[1].to_dict()

## Normalise all event concepts to the MedDRA PT level

# BNF
cur.execute(
    "select trim(lower(source_code_description)), \
    target_concept_id from drug_interaction_compendia.bnf_event_usagi_mapping"
)
row_5 = cur.fetchall()
bnf_event_usagi_mapping = pd.DataFrame(row_5).astype(str)
bnf_event_usagi_mapping.columns = ["source_code_description", "target_concept_id"]
# Remove invalid characters from text descriptions
bnf_event_usagi_mapping["source_code_description"] = (
    bnf_event_usagi_mapping["source_code_description"]
    .str.encode("ascii", "ignore")
    .str.decode("ascii")
)
# Set description as the dataframe index
bnf_event_usagi_mapping.set_index("source_code_description", inplace=True)
# Convert OHDSI concept id to string
bnf_event_usagi_mapping["target_concept_id"] = bnf_event_usagi_mapping[
    "target_concept_id"
].astype(str)
# Replace any LLT terms to their corresponding PTs
bnf_event_usagi_mapping["bnf_PT_event_concept_id"] = bnf_event_usagi_mapping[
    "target_concept_id"
].map(LLT_to_PT_dict)
bnf_event_usagi_mapping["bnf_PT_event_concept_id"].fillna(
    bnf_event_usagi_mapping["target_concept_id"], inplace=True
)
bnf_event_usagi_mapping.drop("target_concept_id", axis=1, inplace=True)

# Micromedex
cur.execute(
    "select trim(lower(source_code_description)), \
    target_concept_id from drug_interaction_compendia.micromedex_event_usagi_mapping"
)
row_6 = cur.fetchall()
micromedex_event_usagi_mapping = pd.DataFrame(row_6).astype(str)
micromedex_event_usagi_mapping.columns = [
    "source_code_description",
    "target_concept_id",
]
# Set description as the dataframe index
micromedex_event_usagi_mapping.set_index("source_code_description", inplace=True)
# Convert OHDSI concept id to string
micromedex_event_usagi_mapping["target_concept_id"] = micromedex_event_usagi_mapping[
    "target_concept_id"
].astype(str)
# Replace any LLT terms to their corresponding PTs
micromedex_event_usagi_mapping[
    "micromedex_PT_event_concept_id"
] = micromedex_event_usagi_mapping["target_concept_id"].map(LLT_to_PT_dict)
micromedex_event_usagi_mapping["micromedex_PT_event_concept_id"].fillna(
    micromedex_event_usagi_mapping["target_concept_id"], inplace=True
)
micromedex_event_usagi_mapping.drop("target_concept_id", axis=1, inplace=True)

## Generate positive controls

# Load intersection table
cur.execute(
    "SELECT DISTINCT c.ordered_drug_list, c.drug_1_concept_name , \
    c.drug_2_concept_name, trim(lower(c.bnf_description)), \
    trim(lower(c.micromedex_description)), c.bnf_severity AS bnf_sev_level, \
    c.ansm_severity AS thesaurus_sev_level, \
    c.micromedex_severity AS micromedex_sev_level, \
    c.bnf_evidence AS bnf_evid_level, \
    c.micromedex_evidence AS micromedex_evid_level  \
    FROM drug_interaction_compendia.common c;"
)
row_1 = cur.fetchall()
common_df = pd.DataFrame(row_1)
common_df.columns = [
    "ordered_drug_list",
    "drug_1_concept_name",
    "drug_2_concept_name",
    "bnf_description",
    "micromedex_effect",
    "bnf_sev_level",
    "ansm_sev_level",
    "micromedex_sev_level",
    "bnf_evid_level",
    "micromedex_evid_level",
]

# Remove invalid characters from BNF text descriptions
common_df["bnf_description"] = (
    common_df["bnf_description"].str.encode("ascii", "ignore").str.decode("ascii")
)

# Get BNF and Micromedex positive controls by mapping text descriptions to 
# their corresonding MedDRA PT concepts
bnf_controls = common_df.merge(
    bnf_event_usagi_mapping, left_on="bnf_description", right_index=True
)
micromedex_controls = common_df.merge(
    micromedex_event_usagi_mapping, left_on="micromedex_effect", right_index=True
)

# Exclude rows with unmapped text descriptions
bnf_controls = bnf_controls[bnf_controls["bnf_PT_event_concept_id"] != "0"].reset_index(
    drop=True
)
micromedex_controls = micromedex_controls[
    micromedex_controls["micromedex_PT_event_concept_id"] != "0"
].reset_index(drop=True)

# Exclude controls with Serotonin syndrome as the mapped event
bnf_controls = bnf_controls[
    bnf_controls["bnf_PT_event_concept_id"] != "36718458"
].reset_index(drop=True)
micromedex_controls = micromedex_controls[
    micromedex_controls["micromedex_PT_event_concept_id"] != "36718458"
].reset_index(drop=True)

# Create a DDE tuple column 
# (in the format 'drug_1_concept_id|drug_2_concept_id|event_concept_id') for 
# easier handling of the positive controls
bnf_controls["dde_tuple"] = bnf_controls.apply(
    lambda x: str(x["ordered_drug_list"] + "|" + x["bnf_PT_event_concept_id"]), axis=1
)
micromedex_controls["dde_tuple"] = micromedex_controls.apply(
    lambda x: str(x["ordered_drug_list"] + "|" + x["micromedex_PT_event_concept_id"]),
    axis=1,
)

# Sort BNF controls by decreasing severity (in case multiple severity levels are 
# assigned to the same control, the highest will be kept once we remove duplicates)
bnf_sev_level_dict = {"Severe": 0, "Moderate": 1, "Mild": 2, None: 3}
bnf_controls.sort_values(
    by=["bnf_sev_level"], key=lambda x: x.map(bnf_sev_level_dict), inplace=True
)
# Drop columns we don't need
bnf_controls.drop(
    ["ordered_drug_list", "micromedex_effect", "bnf_description"], axis=1, 
    inplace=True
)
micromedex_controls.drop(
    ["ordered_drug_list", "micromedex_effect", "bnf_description"], axis=1, 
    inplace=True
)
# Drop any duplicated controls
bnf_controls.drop_duplicates(subset="dde_tuple", inplace=True)
micromedex_controls.drop_duplicates(subset="dde_tuple", inplace=True)

# Rename event_concept_id columns
bnf_controls.rename(
    columns={"bnf_PT_event_concept_id": "event_concept_id"}, inplace=True
)
micromedex_controls.rename(
    columns={"micromedex_PT_event_concept_id": "event_concept_id"}, inplace=True
)

# Replace None values for severity and evidence level columns with empty strings
bnf_controls.fillna("", inplace=True)
micromedex_controls.fillna("", inplace=True)

## Summarise positive controls in a common dataframe

# Create lists of positive controls for each resource
# BNF
bnf = list(set(bnf_controls["dde_tuple"]))
# Micromedex
mi = list(set(micromedex_controls["dde_tuple"]))
# Common positive controls between BNF and Micromedex
bnf_mi = [dde for dde in bnf if dde in mi]

# Get 'BNF+Micromedex' positive controls
df_1 = bnf_controls[bnf_controls["dde_tuple"].isin(bnf_mi)]
df_1["event_source"] = "BNF+Micromedex"
# Convert OHDSI concept_id to MedDRA code
df_1["event_concept_name"] = df_1["event_concept_id"].map(PT_id_to_name_dict)
# Get MedDRA code
df_1["mdr_code"] = df_1["event_concept_id"].map(PT_id_to_code_dict)

# Get 'BNF' positive controls (i.e. mentioned only in BNF)
df_2 = bnf_controls[~bnf_controls["dde_tuple"].isin(bnf_mi)]
df_2["event_source"] = "BNF"
# Convert OHDSI concept_id to MedDRA code
df_2["event_concept_name"] = df_2["event_concept_id"].map(PT_id_to_name_dict)
# Get MedDRA code
df_2["mdr_code"] = df_2["event_concept_id"].map(PT_id_to_code_dict)

# Get 'Micromedex' positive controls (i.e. mentioned only in Micromedex)
df_3 = micromedex_controls[~micromedex_controls["dde_tuple"].isin(bnf_mi)]
df_3["event_source"] = "Micromedex"
# Convert OHDSI concept_id to MedDRA code
df_3["event_concept_name"] = df_3["event_concept_id"].map(PT_id_to_name_dict)
# Get MedDRA code
df_3["mdr_code"] = df_3["event_concept_id"].map(PT_id_to_code_dict)

# Create a df summarising the total number of positive controls from all 
# sources (i.e. 'BNF', 'Micromedex', 'BNF+Micromedex')
pos_controls = pd.concat([df_1, df_2, df_3]).reset_index(drop=True)

# Drop  ddi_tuple column
pos_controls.drop(["dde_tuple", "event_concept_id"], axis=1, inplace=True)

# Replace severity codes for Thesaurus with names - dictionary
thesaurus_di = {
    1: "Take into consideration",
    2: "Precautions for use",
    3: "Not recommended",
    4: "Contraindicated",
}
pos_controls.replace({"ansm_sev_level": thesaurus_di}, inplace=True)

# Reorder columns
pos_controls = pos_controls[
    [
        "drug_1_concept_name",
        "drug_2_concept_name",
        "event_concept_name",
        "mdr_code",
        "event_source",
        "bnf_sev_level",
        "ansm_sev_level",
        "micromedex_sev_level",
        "bnf_evid_level",
        "micromedex_evid_level",
    ]
]
# Capitalise headers
pos_controls.columns = map(str.upper, pos_controls.columns)

# Final dataframe to be exported as a Data Record
dr_1 = pos_controls.drop(["event_concept_id"], axis=1, inplace=True)

## Export dataframes to data files

FILE_NAME_1 = "ddi_controls/output/DR1_with_concept_ids.csv"
pos_controls.to_csv(FILE_NAME_1, index_col=False)

FILE_NAME_2 = "data_records/Data Record 1 - Positive Controls.xslx"
dr_1.to_excel(FILE_NAME_2, index_col=False)
