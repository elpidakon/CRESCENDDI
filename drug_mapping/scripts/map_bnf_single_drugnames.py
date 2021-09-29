# Kontsioti, Maskell, Dutta & Pirmohamed, A reference set of clinically relevant
# adverse drug-drug interactions (2021)
# This script maps drug names from BNF ADR data to normalised OHDSI concepts
# (RxNorm/RxNorm Extension Ingredients)

import pandas as pd
import numpy as np
from itertools import chain, combinations, product
import operator
import random
from collections import Counter
import gc
from nltk.tokenize import sent_tokenize, word_tokenize
from itertools import chain
import itertools, random
import csv
import re
import string
import Bio
from Bio import Entrez
import pandas as pd
import matplotlib.pyplot as plt
import time

# ### i. Data file loading

# Import the extracted .csv file from web scraping
bnf_side_effects_df = pd.read_csv(
    "data_extraction/output/bnf_single_data.csv", dtype=str
)
# Convert to lowercase
bnf_side_effects_df = bnf_side_effects_df.astype(str).apply(lambda x: x.str.lower())

### ii. Drug name mapping

# Import the USAGI drug mapping table:

bnf_drug_mappings_df = pd.read_csv(
    "drug_mapping/data/bnf_single_drugnames.csv",
    usecols=[3, 4],
    index_col=0,
    skiprows=1,
    names=["drug_source_name", "drug_concept_id"],
    dtype=str,
)

# Use the drug mapping table to map drug names in the BNF side effects dataframe
bnf_side_effects_mapped_df_a = pd.merge(
    bnf_side_effects_df, bnf_drug_mappings_df, left_on="Drug_name", right_index=True
)
# Export to a .csv
bnf_side_effects_mapped_df_a.to_csv(
    "drug_mapping/output/bnf_single_with_mapped_drugnames.csv"
)
