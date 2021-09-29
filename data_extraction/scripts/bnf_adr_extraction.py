# Kontsioti, Maskell, Dutta & Pirmohamed, A reference set of clinically relevant 
# adverse drug-drug interactions (2021)
# Code to extract single-drug side effect data from the BNF website

from bs4 import BeautifulSoup
import urllib
import os, csv
import numpy as np
import pandas as pd
import re
from tqdm import tqdm

URL_BEGINNING = 'https://bnf.nice.org.uk/drug/'

print('beginning scrape for individual drugs...')

# Fetch the HTML containing the full list of APIs.
r = urllib.request.urlopen(URL_BEGINNING).read()
soup1 = BeautifulSoup(r, 'lxml')

# Extract the full URL list.
URL_list = []
for s in soup1.find_all('div', {'class': 'span11'}):
    for ai in s(href=True):
        temp = URL_BEGINNING + ai['href']
        URL_list.append(temp)
print(URL_list)

# Create an empty dataframe for storing the extracted data for APIs.
scraped_API_count = 0
scraped_API = pd.DataFrame(np.nan, index = range(0,160000), columns = ['API', 'AE', 'Frequency'], dtype = str)
row_count = 0

# Empty list to store API mappings to their drug class (if applicable).
API_to_drugclass = []

# Scrape individual drug (API) side effects.
HIGHEST_API_ID = len(URL_list)

for id in tqdm(range(0, HIGHEST_API_ID)):

    # Try to fetch the HTML for each API.  
    try:
        l = urllib.request.urlopen(URL_list[id]).read()
    # If the page returns a 404 error, skip this id.
    except urllib.error.HTTPError as e:
       if e.getcode() == 404:
           continue
       raise
    
    # Add one to the count of succesfully scraped products.
    scraped_API_count += 1
    
    soup2 = BeautifulSoup(l, 'lxml')
    API = soup2.find('h1', id= '').span.getText()
    # Extract the relevant information to a dataframe.
    # In case the API contains a side effect section.
    if soup2.find('section', {'id':'sideEffects'}):
        ae_list = soup2.find_all('span', {'class': 'sideEffect'})
        for a in ae_list:
            adv_event = a.getText()
            scraped_API.at[row_count, 'API'] = API
            scraped_API.at[row_count,'AE'] = adv_event
            freq = a.parent.parent.parent.h4.getText()
            scraped_API.at[row_count, 'Frequency'] = freq
            row_count += 1
        # Check if the drug belongs to a specific drug class. If yes, extract
        # the drug class name and the link to the corresponding webpage.
        if soup2.find('section', {'id':'sideEffects'}).find('a', href = re.compile(r'.*/drug-class/.*')):
            temp = []
            temp.append(API)
            drug_class = soup2.find('a', href = re.compile(r'.*/drug-class/.*')).span.getText()
            temp.append(drug_class)
            li = soup2.find('section', {'id':'sideEffects'}).find('a', href = re.compile(r'.*/drug-class/.*'))['href']
            drug_class_link = 'https://bnf.nice.org.uk' + str(li)
            temp.append(drug_class_link)
            API_to_drugclass.append(temp)
    # In case the API does not contain a side effect section.
    else:
        adv_event = 'NO AEs MENTIONED'
        scraped_API.at[row_count, 'API'] = API
        scraped_API.at[row_count,'AE'] = adv_event
        scraped_API.at[row_count,'Frequency'] = ''
        row_count += 1

# Remove empty rows from the dataframe that contains the extracted data.
scraped_API_dropna = scraped_API[~scraped_API.isin(['n']).any(axis=1)]
# Remove spaces at the beginning and at the end of the text fields.
scraped_API_dropna['API'] = scraped_API_dropna['API'].str.strip()
scraped_API_dropna['AE'] = scraped_API_dropna['AE'].str.strip()
scraped_API_dropna['Frequency'] = scraped_API_dropna['Frequency'].str.strip()

print('BNF individual side effects succesfully scraped.')

print('beginning scrape for drug classes...')

# Create a dataframe with drug names, drug classes and related URLs (where applicable).
API_class_df = pd.DataFrame(API_to_drugclass, columns = ['API','Drug_Class','Link'])

# Create a list with all the links for the drug class webpages.
class_links = API_class_df['Link'].unique().tolist()

# Scrape drug class side effects.

HIGHEST_DRUG_CLASS_ID = len(class_links)

scraped_class_count = 0
# Create an empty dataframe for storing the extracted data for drug classes.
scraped_class = pd.DataFrame(np.nan, index = range(0,160000), columns = ['Drug_Class', 'AE', 'Frequency'], dtype = str)
row_count_2 = 0

for id in tqdm(range(0, HIGHEST_DRUG_CLASS_ID)):
# Try to fetch the HTML for each drug class.  
    try:
        l = urllib.request.urlopen(class_links[id]).read()
    # If the page returns a 404 error, skip this id.
    except urllib.error.HTTPError as e:
       if e.getcode() == 404:
           continue
       raise
    
    # Add one to the count of succesfully scraped drug classes.
    scraped_class_count += 1
    
    soup3 = BeautifulSoup(l, 'lxml')
    # Extract the drug class name.
    class_name = soup3.find('h1', id= '').span.getText()
    # Extract the relevant information to a dataframe.
    class_ae_list = soup3.find_all('span', {'class': 'sideEffect'})
    for a in class_ae_list:
        adv_event = a.getText()
        scraped_class.at[row_count_2, 'Drug_Class'] = class_name
        scraped_class.at[row_count_2,'AE'] = adv_event
        freq = a.parent.parent.parent.h4.getText()
        scraped_class.at[row_count_2, 'Frequency'] = freq
        row_count_2 += 1

# Remove empty rows from the dataframe that contains the extracted data.
scraped_class_dropna = scraped_class[~scraped_class.isin(['n']).any(axis=1)]
# Remove spaces at the beginning and at the end of the text fields.
scraped_class_dropna['Drug_Class'] = scraped_class_dropna['Drug_Class'].str.strip()
scraped_class_dropna['AE'] = scraped_class_dropna['AE'].str.strip()
scraped_class_dropna['Frequency'] = scraped_class_dropna['Frequency'].str.strip()

print('BNF drug class side effects succesfully scraped.')

print('combine extracted data...')

## Combine both tables by adding drug class side effects to the individual 
## ingredients of each drug class.

# Create a dictionary that contains all drug classes as keys and side effects 
# with associated frequencies as values.
AEs_by_class_dict = scraped_class_dropna.groupby('Drug_Class')[['AE', 'Frequency']].apply(lambda g: list(map(tuple, g.values.tolist()))).to_dict()

# Remove URL column
API_class_df.drop(columns = 'Link', inplace = True)
# Create a dataframe with drug class as the index of APIs (if available)
# and add their drug class side effects and associated frequencies.
API_class_df['Drug_Class'] = API_class_df['Drug_Class'].str.strip()
API_class_df.set_index('Drug_Class', inplace = True)
API_class_df['AE_freq_tuple'] = API_class_df.index.to_series().map(AEs_by_class_dict)
API_class_df.reset_index(inplace=True)

# Create a new dataframe to store drug class side effect data for each API.
AEs_from_class_df = API_class_df.explode('AE_freq_tuple').reset_index(drop=True)
AEs_from_class_df[['AE', 'Frequency']] = pd.DataFrame(AEs_from_class_df['AE_freq_tuple'].tolist(), index = AEs_from_class_df.index) 
AEs_from_class_df['from_drug_class'] = 'Yes'
AEs_from_class_df.drop(columns = ['AE_freq_tuple','Drug_Class'], inplace = True)

# Fill NAs in Frequency column if no side effects are mentioned.
scraped_API_dropna.loc[scraped_API_dropna.AE == 'NO AEs MENTIONED', 'Frequency'] = 'N/A'
# Fill NAs in drug class indicator if no side effects are mentioned. Otherwise, put 'No'.
scraped_API_dropna['from_drug_class'] = np.where(scraped_API_dropna['AE'] == 'NO AEs MENTIONED', 'N/A', 'No')

# Concatenate the two dataframes to get a final one.
final_df = pd.concat([scraped_API_dropna, AEs_from_class_df])
# Remove any rows that do not contain side effects.
final_df = final_df[final_df.AE != 'NO AEs MENTIONED']
# Convert dataframe to lowercase.
final_df = final_df.apply(lambda x: x.astype(str).str.lower())
# Sort alphabetically. 
final_df = final_df.sort_values(by=['API', 'from_drug_class'])
# Remove any duplicates.
final_df.drop_duplicates(subset = ['API', 'AE', 'Frequency'], keep = 'first', inplace = True)
# Rename columns.
final_df.columns = ['Drug_name', 'AE', 'Frequency', 'from_drug_class']

FILE_NAME = 'data_extraction/output/bnf_single_data.csv'

print('saving to file...')
# Save the dataset to a csv file.
final_df.to_csv(FILE_NAME, index=False, encoding = "utf-8")
