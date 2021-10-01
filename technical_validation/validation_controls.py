# -*- coding: utf-8 -*-
"""
Created on Wed Sep 29 13:24:38 2021

@author: Elpida
"""

# Tachnical validation - Controls

import pandas as pd

# Read .xlsx files
pos_ctls = pd.read_excel("data_records/Data Record 1 - Positive Controls.xlsx")
neg_ctls = pd.read_excel("data_records/Data Record 2 - Negative Controls.xlsx")

# Random control selection
pos_sample = pos_ctls.sample(n=40, random_state=1)
neg_sample = neg_ctls.sample(n=40, random_state=1)

# Export to .csv files
pos_sample.to_csv("validation_positive_contols.csv")
neg_sample.to_csv("validation_negative_contols.csv")