# Kontsioti, Maskell, Dutta & Pirmohamed, A reference set of clinically relevant adverse drug-drug interactions (2021)
# Code to extract drug-drug interaction (DDI) data from the Micromedex website

import pandas as pd
import json
from pprint import pprint
from flatten_json import flatten
import urllib
from urllib.request import urlopen
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import ErrorInResponseException, NoSuchElementException
from urllib.request import Request, urlopen 
from bs4 import BeautifulSoup, SoupStrainer
import requests
import html
import time
import collections
from nltk.tokenize import sent_tokenize, word_tokenize
from itertools import chain
import csv
import re


# To protect the privacy of the format of Micromedex, we have omitted part of 
# the code related to web data extraction using Selenium WebDriver and BeautifulSoup.  
# The available code begins with extracted Micromedex data in the format:
# micromedex_data : drug_name | interactant_name | interaction_effect | severity | substantiation
# where drug_name is the webpage main drug;
#       interactant_name is the drug referred to as interacting with the main drug (drug_name);
#       interaction_effect is the text extracted from the webpage that contains all the information related
#       to the interaction between the main drug and the interactant;
#       severity is the severity label associated with the interaction
#       substantiation is the evidence label associated with the interaction
 
# Load the dataframe micromedex_data (encoding='ISO-8859-1'), which was extracted from Micromedex,
# with columns: drug_name | interactant_name | interaction_effect | severity | substantiation


# Convert all drug name entries to lowercase
micromedex_data['drug_name'] = micromedex_data['drug_name'].str.lower()
micromedex_data['interactant_name'] = micromedex_data['interactant_name'].str.lower()
# Return True if the drug name is alphabetically after the interactant
idx = (micromedex_data['drug_name'] > micromedex_data['interactant_name'])
# Place all pairs in alphabetical order (drug name before interactant in all instances)
micromedex_data.loc[idx, ['drug_name', 'interactant_name']] = micromedex_data.loc[idx, ['interactant_name', 'drug_name']].values
# Sort alphabetically
micromedex_data = micromedex_data.sort_values(by = ['drug_name', 'interactant_name'])

# Remove duplicates and reset index
micromedex_data = micromedex_data.drop_duplicates().reset_index(drop=True)

FILE_NAME = 'data_extraction/output/micromedex_ddi_data.csv'

# Write the processed data to a csv file
micromedex_processed.to_csv(FILE_NAME, index=False, encoding = "utf-8")

