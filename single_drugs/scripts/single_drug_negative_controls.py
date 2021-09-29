# Kontsioti, Maskell, Dutta & Pirmohamed, A reference set of clinically relevant
# adverse drug-drug interactions (2021)
# Script to generate negative controls for single drugs.

import pandas as pd
import numpy as np
from itertools import chain, combinations, product
import operator
import random
from collections import Counter
import gc
from itertools import chain
import itertools, random
import csv
import re
import string
import Bio
from Bio import Entrez
import matplotlib.pyplot as plt
import time
import psycopg2
from sqlalchemy import create_engine
import os
import warnings

## Replace with PostgreSQL credentials
engine = create_engine("postgresql://username:password@host:port/database")

conn = psycopg2.connect("dbname=database user=username")
cur = conn.cursor()

## Functions for PubMed literature search
# REPLACE Entrez.email FIELD WITH A VALID E-MAIL ADDRESS
def search(query):
    Entrez.email = "E-MAIL"
    handle = Entrez.esearch(
        db="pubmed", sort="relevance", retmax="20", retmode="xml", term=query
    )
    results = Entrez.read(handle)
    return results


def fetch_details(id_list):
    ids = ",".join(id_list)
    Entrez.email = "E-MAIL"
    handle = Entrez.efetch(db="pubmed", retmode="xml", id=ids)
    results = Entrez.read(handle)
    return results


# Import CSV files with single-drug ADRs (i.e. single-drug positive controls)
cols = [
    "DRUG_CONCEPT_ID",
    "EVENT_CONCEPT_ID",
    "DRUG_CONCEPT_NAME",
    "EVENT_CONCEPT_NAME",
]
single_drug_adr_bnf = pd.read_csv(
    "event_mapping/output/bnf_single_mapped_with_eventnames.csv",
    skiprows=1,
    names=cols,
    dtype=str,
)
single_drug_adr_sider = pd.read_csv(
    "event_mapping/output/sider_adr_table.csv", skiprows=1, names=cols, dtype=str
)
single_drug_adr_bnf["source"] = "BNF"
single_drug_adr_sider["source"] = "SIDER"
single_drug_adr_df = pd.concat([single_drug_adr_bnf, single_drug_adr_sider])

# Get intersection of information between BNF and SIDER for ADRs
pos_ctls_df = (
    single_drug_adr_df[single_drug_adr_df.duplicated(subset=cols, keep=False)]
    .drop_duplicates(subset=cols)[cols]
    .reset_index(drop=True)
)

# Get drug list for candidate negative controls
drug_list = pos_ctls_df.DRUG_CONCEPT_NAME.unique().tolist()
# Get PT list for candidate negative controls
ae_text_df = pos_ctls_df[["EVENT_CONCEPT_NAME", "EVENT_CONCEPT_ID"]].drop_duplicates()
# Check if the AE is reported at the MedDRA PT level
ae_text_df["PT_LEVEL"] = ""
for index, row in ae_text_df.iterrows():
    cur.execute(
        "SELECT * FROM cdmv5.concept WHERE concept_id = (%s) \
        AND vocabulary_id = 'MedDRA' AND concept_class_id = 'PT' ;",
        [row["EVENT_CONCEPT_ID"]],
    )
    res = cur.fetchall()
    if len(res) != 0:
        ae_text_df.at[index, "IS_PT"] = True
    else:
        ae_text_df.at[index, "IS_PT"] = False
# Generate a list with candidate PTs for the negative controls
pt_list = ae_text_df[ae_text_df["IS_PT"] == True].EVENT_CONCEPT_NAME.tolist()

## Negative control generation for single drugs
random.seed(30)
i = 0
no_of_controls = 12500

with open(
    "single_drugs/output/single_drug_negative_controls.csv", "w", newline=""
) as f:
    writer = csv.writer(f)
    while i < no_of_controls:
        while True:
            try:
                # Randomly select a drug and a PT
                d = random.choice(drug_list)
                pt = random.choice(pt_list)
                # Check if the candidate negative control (i.e. drug-event pair)
                # can be found in any of the two resources (i.e. BNF or SIDER)
                # as an ADR
                lookup = single_drug_adr_df.loc[
                    (single_drug_adr_df.DRUG_CONCEPT_NAME == d)
                    & (single_drug_adr_df.EVENT_CONCEPT_NAME == pt)
                ]
                # If not:
                if len(lookup) == 0:
                    # Submit a PubMed query
                    text_query = (
                        "("
                        + d
                        + ") AND ("
                        + pt
                        + ") AND ((adverse event) OR (adverse drug reaction))"
                    )
                    results = search(text_query)
                    id_list = results["IdList"]
                    # If the PubMed query returns no results, store the generated negative control
                    if len(id_list) == 0:
                        i += 1
                        print(i)
                        writer.writerow([text_query, d, pt])
            except IOError:
                continue
            break
