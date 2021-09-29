# Kontsioti, Maskell, Dutta & Pirmohamed, A reference set of clinically relevant 
# adverse drug-drug interactions (2021)
# Script to generate negative controls for DDIs using drug and event concepts 
# from the positive control set.

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

# Functions for PubMed literature search
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


# A function to check if a dde tuple (i.e. drug-drug-event triplet) has a 
# non-zero count in FAERS

# We need to load drug_report_dictionary and pt_report_dictionary from FAERS


def is_in_faers(d1_id, d2_id, pt_id, drug_report_dictionary, pt_report_dictionary):
    n_111 = "zero"
    for report, drugs in drug_report_dictionary.items():
        if report in pt_report_dictionary.keys():
            if (d1_id in drugs) and (d2_id in drugs):
                if pt_id in pt_report_dictionary[report]:
                    n_111 = "non-zero"
                    break
                else:
                    pass
            else:
                pass
        else:
            pass
    return n_111


# Get two dictionaries with drugs and events that will be used to generate 
# negative controls
pos_controls = pd.read_csv("ddi_controls/output/DR1_with_concept_ids.csv")


def create_dicts(dataframe):
    drug_sub_d_1 = dataframe.set_index("drug_1_concept_id")[
        "drug_1_concept_name"
    ].to_dict()
    drug_sub_d_2 = dataframe.set_index("drug_2_concept_id")[
        "drug_2_concept_name"
    ].to_dict()
    drug_d = {**drug_sub_d_1, **drug_sub_d_2}
    PT_d = dataframe.set_index("PT_mapping_x")["PT_name"].to_dict()
    return drug_d, PT_d


drug_dict, AE_dict = create_dicts(pos_controls)

# Find all drug pairs from any of the three DDI compendia (i.e. union of the 
# three resources)
# BNF
cur.execute(
    "select bnf.ordered_drug_list from drug_interaction_compendia.bnf_drug_pairs as bnf;"
)
bnf_drug_pair_list = [tup[0] for tup in cur.fetchall() if tup[0]]
bnf_drug_pair_tuples = [
    (int(i.split("|")[0]), int(i.split("|")[1])) for i in bnf_drug_pair_list
]
# Micromedex
cur.execute(
    "select mi.ordered_drug_list from drug_interaction_compendia.micromedex_drug_pairs as mi;"
)
micromedex_drug_pair_list = [tup[0] for tup in cur.fetchall() if tup[0]]
micromedex_drug_pair_tuples = [
    (int(i.split("|")[0]), int(i.split("|")[1])) for i in micromedex_drug_pair_list
]
# Thesaurus
cur.execute(
    "select thes.ordered_drug_list from drug_interaction_compendia.thesaurus_drug_pairs as thes;"
)
thesaurus_drug_pair_list = [tup[0] for tup in cur.fetchall() if tup[0]]
thesaurus_drug_pair_tuples = [
    (int(i.split("|")[0]), int(i.split("|")[1])) for i in thesaurus_drug_pair_list
]

union_tuples = set(
    bnf_drug_pair_tuples + micromedex_drug_pair_tuples + thesaurus_drug_pair_tuples
)

## Generate negative controls for DDIs
random.seed(30)
# Create a list of all possible drug pairs from the dictionary of the selected drugs
all_drug_pairs = list(set(itertools.combinations(sorted(drug_dict.keys()), 2)))
# Get a list with the selected events
AE_list = list(AE_dict.keys())
i = 0
# Specify number of negative controls for generation
no_of_controls = 10350

with open("ddi_controls/output/negative_controls.csv", "w", newline="") as f:
    writer = csv.writer(f)
    while i < no_of_controls:
        while True:
            try:
                # Randomly select a drug pair
                dd = random.choice(all_drug_pairs)
                # Check if the drug pair can be found in any of the three resources
                if dd not in union_tuples:
                    # Randomly select an event
                    pt = random.choice(AE_list)
                    # Create a customised PubMed query
                    text_query = (
                        "("
                        + drug_dict[dd[0]]
                        + ") AND ("
                        + drug_dict[dd[1]]
                        + ") AND (("
                        + AE_dict[pt]
                        + ") OR (interaction))"
                    )
                    # Submit the query
                    results = search(text_query)
                    # Get PubMed search results
                    id_list = results["IdList"]
                    # If the PubMed query returns no results
                    if len(id_list) == 0:
                        # Check if the candidate negative control (i.e. dde tuple) 
                        # has a non-zero count in FAERS
                        faers_triplet_count = is_in_faers(
                            dd[0], dd[1], pt, drug_report_dict, pt_report_dict
                        )
                        # If it does, then store the negative control
                        if faers_triplet_count == "non-zero":
                            i += 1
                            writer.writerow(
                                [
                                    text_query,
                                    drug_dict[dd[0]],
                                    drug_dict[dd[1]],
                                    AE_dict[pt],
                                ]
                            )
            except IOError:
                continue
            break

## Map negative controls to MedDRA codes
negative_controls = pd.read_csv("ddi_controls/output/negative_controls.csv")
negative_controls.columns = [
    "PubMed_query",
    "DRUG_1_CONCEPT_NAME",
    "DRUG_2_CONCEPT_NAME",
    "EVENT_CONCEPT_NAME",
]

# Event name to MedDRA code dictionary
cur.execute(
    "select c.concept_name, c.concept_code from cdmv5.concept c where \
    c.vocabulary_id = 'MedDRA' and c.concept_class_id = 'PT';"
)
row = cur.fetchall()
event_name_to_code_df = pd.DataFrame(row).astype(str)
event_name_to_code_df.set_index(0, inplace=True)
event_name_to_code_dict = event_name_to_code_df[1].to_dict()

negative_controls["MDR_CODE"] = negative_controls["EVENT_CONCEPT_NAME"].map(
    event_name_to_code_dict
)
negative_controls.drop("PubMed_query", axis=1, inplace=True)

## Export final negative control dataframe as a Data Record
FILE_NAME = "data_records/Data Record 2 - Negative Controls.xslx"
negative_controls.to_excel(FILE_NAME)
