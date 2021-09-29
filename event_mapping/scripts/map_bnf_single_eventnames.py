# Kontsioti, Maskell, Dutta & Pirmohamed, A reference set of clinically relevant
# adverse drug-drug interactions (2021)
# This script maps event names from BNF ADR data to normalised OHDSI concepts
# (MedDRA PTs)

import pandas as pd
import numpy as np
import psycopg2
from sqlalchemy import create_engine
import csv
import os
import warnings

## Replace with PostgreSQL credentials
engine = create_engine("postgresql://username:password@host:port/database")

conn = psycopg2.connect("dbname=database user=username")
cur = conn.cursor()

bnf_side_effects_mapped_df_a = pd.read_csv(
    "drug_mapping/output/bnf_single_with_mapped_drugnames.csv"
)
pos_controls_df = pd.read_csv("ddi_controls/output/DR1_with_concept_ids.csv")

# Create a dictionary with the drugs from the DDI reference set

drug_sub_d_1 = pos_controls_df.set_index("drug_1_concept_id")[
    "drug_1_concept_name"
].to_dict()
drug_sub_d_2 = pos_controls_df.set_index("drug_2_concept_id")[
    "drug_2_concept_name"
].to_dict()
drug_dict = {**drug_sub_d_1, **drug_sub_d_2}

# Only select rows from the BNF side effects dataframe that are related to the
# drugs in our reference set (i.e. the ones in the drug_dict)

bnf_side_effects_mapped_df_b = bnf_side_effects_mapped_df_a[
    bnf_side_effects_mapped_df_a.drug_concept_id.isin(drug_dict.keys())
].reset_index(drop=True)

# Export a .csv file with the text from the 'AE' column that is going to be 
# mapped to MedDRA concepts
bnf_AEs_for_mapping = pd.DataFrame(
    bnf_side_effects_mapped_df_b.AE.unique(), columns=["AE"]
)
bnf_AEs_for_mapping.to_csv(
    "event_mapping/data/bnf_single_events_for_mapping.csv",
    index=False,
    encoding="utf-8",
)

###### MAPPING PROCESS USING USAGI ###########################################

# Import the USAGI drug mapping table:
bnf_event_mappings_df = pd.read_csv(
    "event_mapping/data/bnf_single_eventnames.csv",
    usecols=[1, 5],
    index_col=0,
    skiprows=1,
    names=["event_source_name", "event_concept_id"],
    dtype=str,
)

# Create a dictionary to map MedDRA LLT concepts to their corresponding PT concepts
cur.execute(
    "select c.concept_id, c.concept_name, c.concept_code, ca.ancestor_concept_id from cdmv5.concept c \
            join cdmv5.concept_ancestor ca on c.concept_id = ca.descendant_concept_id \
            where c.vocabulary_id = 'MedDRA' and c.concept_class_id = 'LLT' and ca.min_levels_of_separation = 1 \
            and ca.max_levels_of_separation = 1;"
)
row_2 = cur.fetchall()
LLT_to_PT_df = pd.DataFrame(row_2).astype(str)
LLT_to_PT_df.set_index(0, inplace=True)
LLT_to_PT_dict = LLT_to_PT_df[3].to_dict()

# Map any LLT concepts in the BNF ADR mapping table to their ancestor PT concepts
bnf_event_mappings_df["PT_concept_id"] = bnf_event_mappings_df["event_concept_id"].map(
    LLT_to_PT_dict
)
bnf_event_mappings_df["PT_concept_id"].fillna(
    bnf_event_mappings_df["event_concept_id"], inplace=True
)

# Use the BNF ADR mapping table to map AE-related text in the BNF side effects dataframe
bnf_side_effects_mapped_df_c = pd.merge(
    bnf_side_effects_mapped_df_b, bnf_event_mappings_df, left_on="AE", right_index=True
).reset_index(drop=True)

# Drop rows with unmapped AEs, keep only the concept ID columns into a separate
# dataframe and remove any duplicated rows
bnf_df = bnf_side_effects_mapped_df_c[
    bnf_side_effects_mapped_df_c["PT_concept_id"] != "0"
]
bnf_df = (
    bnf_df[["drug_concept_id", "PT_concept_id"]]
    .drop_duplicates()
    .set_index("drug_concept_id")
)

## Map concept_id values to their corresponding concept_names (Drugs and Events)

# concept_id to concept_name dictionary for Drugs
cur.execute(
    "select c.concept_id, c.concept_name from cdmv5.concept c \
            where c.concept_class_id = 'Ingredient';"
)
row_1 = cur.fetchall()
drug_concept_id_to_name_df = pd.DataFrame(row_1).astype(str)
drug_concept_id_to_name_df.set_index(0, inplace=True)
drug_concept_id_to_name_dict = drug_concept_id_to_name_df[1].to_dict()

# concept_id to concept_name dictionary for Events
cur.execute(
    "select c.concept_id, c.concept_name from cdmv5.concept c \
            where c.vocabulary_id = 'MedDRA';"
)
row_2 = cur.fetchall()
event_concept_id_to_name_df = pd.DataFrame(row_2).astype(str)
event_concept_id_to_name_df.set_index(0, inplace=True)
event_concept_id_to_name_dict = event_concept_id_to_name_df[1].to_dict()

# Create two new columns
bnf_df["DRUG_CONCEPT_NAME"] = bnf_df["drug_concept_id"].map(
    drug_concept_id_to_name_dict
)
bnf_df["EVENT_CONCEPT_NAME"] = bnf_df["PT_concept_id"].map(
    event_concept_id_to_name_dict
)
# Rename columns
bnf_df.columns = [
    "DRUG_CONCEPT_ID",
    "EVENT_CONCEPT_ID",
    "DRUG_CONCEPT_NAME",
    "EVENT_CONCEPT_NAME",
]

# Export to a .csv file
bnf_df.to_csv("event_mapping/output/bnf_single_mapped_with_eventnames.csv")
