# Kontsioti, Maskell, Dutta & Pirmohamed, A reference set of clinically relevant adverse drug-drug interactions (2021)
# This script maps drug names from SIDER ADR and Indication data to normalised OHDSI concepts (RxNorm/RxNorm Extension Ingredients)

import pandas as pd
import numpy as np
import psycopg2
from sqlalchemy import create_engine
import csv
import os
import warnings

# Connect to PostgreSQL
# Replace with your PostgreSQL credentials
engine = create_engine(
        'postgresql://username:password@host:port/database')

conn = psycopg2.connect("dbname=database user=username")
cur = conn.cursor()

### i. Data file loading

# STITCH to drug name mappings
drug_names_df = pd.read_csv('data_extraction/data/SIDER/drug_names.tsv', names=['STITCH_code', 'drug_name'], sep='\t')
drug_names_df['drug_name'] = drug_names_df['drug_name'].str.lower()
drug_names_df.set_index('STITCH_code',inplace=True)
# STITCH to ATC code mappings
drug_atc_df = pd.read_csv('data_extraction/data/SIDER/drug_atc.tsv' , names=['STITCH_code', 'ATC_code'], sep='\t')
drug_atc_df.set_index('STITCH_code',inplace=True)

# Drug side effects
drug_se = pd.read_csv('data_extraction/data/SIDER/meddra_all_se.tsv', names=['STITCH_code_1', 'STITCH_code_2', 'UMLS_code_label', 'MedDRA_type', \
                                                  'UMLS_code_final', 'se_name'], sep='\t')
# Drug indications
drug_indications = pd.read_csv('data_extraction/data/SIDER/meddra_all_indications.tsv', names=['STITCH_code', 'UMLS_code_label', 'detection_method', \
                                                                    'concept_name', 'MedDRA_type', 'UMLS_code_final', \
                                                                    'indication_name'], sep='\t')

### ii. Drug name mapping

# Merge the two drug mappings dataframes by index
drug_df = pd.merge(drug_names_df, drug_atc_df, left_index=True, right_index=True, how = 'outer').reset_index(drop=False)

# a. Exact string matching (Drug names to OHDSI RxNorm/RxNormExtension Ingredient concepts)

# A dictionary for mapping drug names to standardised OHDSI concepts (RxNorm and RxNormExtension)
cur.execute("SELECT concept_id, concept_name, concept_code FROM cdmv5.concept WHERE vocabulary_id in \
            ('RxNorm', 'RxNorm Extension') and concept_class_id = 'Ingredient' and standard_concept = 'S';")
row_2 = cur.fetchall()
cols_2 = ['OHDSI_concept_id', 'concept_name', 'RxNorm/RxNorm_Extension_code']
rxnorm_df = pd.DataFrame(row_2).astype(str)
rxnorm_df.columns = cols_2
rxnorm_dict = dict(zip(rxnorm_df.concept_name.str.lower(), rxnorm_df.OHDSI_concept_id))

# Adding a column with the corresponding OHDSI concept using the above dictionary
drug_df['OHDSI_RxNorm_id_1'] = drug_df['drug_name'].str.lower().map(rxnorm_dict)
# Add a column to indicate if exact string matching was successful
drug_df['exact_string_matching'] = np.where( drug_df['OHDSI_RxNorm_id_1'].isnull(), 'No', 'Yes')
drug_df.head()

# b. ATC names to OHDSI RxNorm/RxNormExtension Ingredient concepts

# Map ATC to RxNorm terms using the relevant PostgreSQL table
# First, map ATC codes to ATC names
drug_df['ATC_name'] =  ''
for index, row in drug_df.iterrows():
    # Ignore if ATC code not available
    if type(row['ATC_code']) != str:
        pass
    else:
        cur.execute("SELECT concept_name FROM cdmv5.concept WHERE concept_code = (%s);", [row['ATC_code']])
        drugname = cur.fetchall()  
        if len(drugname) != 0:
            drug_df.at[index, 'ATC_name'] = str(drugname[0][0]).lower()
# Then, map ATC names to OHDSI RxNorm Ingredient concepts (using exact string matching)
drug_df['OHDSI_RxNorm_id_2'] = drug_df['ATC_name'].str.lower().map(rxnorm_dict)

# c. ATC codes to OHDSI RxNorm concepts (using OHDSI concept_relationship table)

### Mapping of ATC codes to OHDSI (RxNorm) using concept_relationship table
for index, row in drug_df.iterrows():
    # Ignore if ATC code not available
    if type(row['ATC_code']) != str:
        pass
    else:
        cur.execute("SELECT cr.concept_id_2 FROM cdmv5.concept_relationship cr \
                    JOIN cdmv5.concept c ON cr.concept_id_1 = c.concept_id \
                    WHERE c.concept_code = (%s) AND cr.relationship_id = 'ATC - RxNorm';", [row['ATC_code']])
        drugname = cur.fetchall()  
        if len(drugname) != 0:
            drug_df.at[index, 'OHDSI_RxNorm_id_3'] = str(drugname[0][0]).lower()
            
# Rearrange df column order
drug_df = drug_df[['STITCH_code', 'drug_name', 'ATC_name', 'ATC_code', 'exact_string_matching', 'OHDSI_RxNorm_id_1', \
                   'OHDSI_RxNorm_id_2', 'OHDSI_RxNorm_id_3']]
# Set STITCH_code as the df index
drug_df = drug_df.set_index('STITCH_code')

# Convert the above dataframe into a final dictionary for mapping STITCH codes to OHDSI RxNorm/RxNormExtension Ingredient concepts
stitch_to_rxnorm_id = {k: [v['OHDSI_RxNorm_id_1'], v['OHDSI_RxNorm_id_2'], v['OHDSI_RxNorm_id_3']] for k, v in drug_df.iterrows()}
# Remove any NaN values from the dictionary values
stitch_to_rxnorm_id.update({k: [i for i in v if str(i) != 'nan'] for k, v in stitch_to_rxnorm_id.items()})
# Remove any duplicated values for the same key
stitch_to_rxnorm_id.update({k: list(set(v)) for k, v in stitch_to_rxnorm_id.items()})

# iii. Side effects table mapping

drug_se['OHDSI_drug_id'] = drug_se['STITCH_code_1'].map(stitch_to_rxnorm_id)
# Drop rows with unmapped drug names
drug_se = drug_se[drug_se['OHDSI_drug_id'].notnull()].reset_index(drop=True)

# During the drug mapping process, STITCH codes were mapped to one or multiple OHDSI RxNorm/RxNormExtension Ingredient concepts. 
# Thus, 'OHDSI_drug_id' column in the above dataframe contains rows with one or more mapped concepts. 
# We will create a final version of the side effects table by 'exploding' rows with multiple mapped drug concepts into separate rows 
# and only keeping the columns of interest
se_sider_df = drug_se.explode('OHDSI_drug_id')
# Drop rows with unmapped drug names
se_sider_df = se_sider_df[se_sider_df['OHDSI_drug_id'].notnull()].reset_index(drop=True)
# Keep only drug concept ID and side effect name columns
se_sider_df = se_sider_df[['OHDSI_drug_id', 'se_name']]
# Rename columns
se_sider_df.columns = ['drug_concept_id', 'se_name_unmapped']
# Drop any duplicated rows
se_sider_df = se_sider_df.drop_duplicates().set_index('drug_concept_id')
# Export to a CSV
se_sider_df.to_csv('drug_mapping/output/SIDER_side_effects_with_mapped_drugnames.csv')

# iv. Indications table mapping

drug_indications['OHDSI_drug_id'] = drug_indications['STITCH_code'].map(stitch_to_rxnorm_id)
# Similarly to the previous table for side effects, we will 'explode' rows with multiple mapped drug concepts into separate rows 
# and keep only the columns of interest
indications_sider_df = drug_indications.explode('OHDSI_drug_id')
# Drop rows with unmapped drug names
indications_sider_df = indications_sider_df[indications_sider_df['OHDSI_drug_id'].notnull()].reset_index(drop=True)
# Keep only drug concept ID and indication name columns
indications_sider_df = indications_sider_df[['OHDSI_drug_id', 'indication_name']]
# Rename columns
indications_sider_df.columns = ['drug_concept_id', 'indication_name']
# Drop any duplicated rows
indications_sider_df = indications_sider_df.drop_duplicates().set_index('drug_concept_id')
# Export to a CSV
indications_sider_df.to_csv('drug_mapping/output/SIDER_indications_with_mapped_drugnames.csv')
