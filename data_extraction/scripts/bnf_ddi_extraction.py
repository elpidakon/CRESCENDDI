# Kontsioti, Maskell, Dutta & Pirmohamed, A reference set of clinically relevant
# adverse drug-drug interactions (2021)
# Code to extract drug-drug interaction (DDI) data from BNF website

from bs4 import BeautifulSoup
import urllib
import os, csv
import numpy as np
import pandas as pd
from tqdm import tqdm
from nltk import word_tokenize
from nltk.util import ngrams
import string
import re
from nltk.tokenize.treebank import TreebankWordDetokenizer as Detok

detokenizer = Detok()

URL_BEGINNING = "https://bnf.nice.org.uk/interaction/"

print("beginning scrape...")

# Fetch the HTML containing the full list of Active Pharmaceutical Ingredients
# (APIs) with links for the interaction section.
r = urllib.request.urlopen(URL_BEGINNING).read()
soup1 = BeautifulSoup(r, "lxml")

# Extract the full URL list for interactions.
URL_list = []
for s in soup1.find_all("div", {"class": "span11"}):
    # a = soup1.find_all('div', {'class': 'span11'}).ul
    for ai in s(href=True):
        temp = URL_BEGINNING + ai["href"]
        URL_list.append(temp)
print(URL_list)

scraped_API_count = 0
# Create an empty dataframe to store the extracted data for each API.
scraped_API = pd.DataFrame(
    np.nan,
    index=range(0, 160000),
    columns=["API", "Interactant", "Description"],
    dtype=str,
)
row_count = 0

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

    soup2 = BeautifulSoup(l, "lxml")

    # Extract the relevant information to a dataframe.
    for n, m in zip(
        soup2.find_all("h5", {"class": "interactant"}),
        soup2.find_all("div", {"class": "span9 interaction-messages"}),
    ):
        API = (
            soup2.find("h1", {"class": "interaction-heading"})
            .span.getText()
            .lstrip(" ")
        )
        interactant_name = n.getText().strip("\n")
        # To avoid duplicate entries (i.e. same drug pair and related description
        # with reversed positions of API and Interactant), we only extract
        # the interactants that come after each API in alphabetical order.
        if interactant_name > API:
            for i in m.select('div[class*="interaction-message"]'):
                scraped_API.at[row_count, "API"] = API
                scraped_API.at[row_count, "Interactant"] = interactant_name
                description = i.getText().strip("\n").strip()
                scraped_API.at[row_count, "Description"] = description
                row_count += 1

print("BNF interactions succesfully scraped.")

print("begin scraped data postprocessing...")

# Remove empty rows from the dataframe that contains the extracted data.
scraped_API_dropna = scraped_API[~scraped_API.isin(["n"]).any(axis=1)]
# Remove spaces at the beginning and at the end of the text.
scraped_API_dropna["API"] = scraped_API_dropna["API"].str.strip()
scraped_API_dropna["Interactant"] = scraped_API_dropna["Interactant"].str.strip()
scraped_API_dropna["Description"] = scraped_API_dropna["Description"].str.strip()

# Remove severity and evidence information (if available) and put them in separate columns
scraped_API_dropna["Description_short"] = ""
scraped_API_dropna["Severity"] = ""
scraped_API_dropna["Evidence"] = ""
sev = "Severity of interaction"
evid = "Evidence for interaction"

for index, row in scraped_API_dropna.iterrows():
    # Takes the description of the selected row
    descr = row["Description"]
    # Split to tokens
    tokens = word_tokenize(descr)
    # Take trigrams (3 consecutive tokens)
    trigrams = ngrams(tokens, 3)
    # Include all trigrams in a list
    trigram_list = [" ".join(grams) for grams in trigrams]
    # If the severity description is contained in the description
    if sev in descr:
        # Take the position of the trigram that contains the level of severity
        sev_level_index = trigram_list.index(sev) + 2
        # Take the token describing the level of severity
        sev_level = trigram_list[sev_level_index].split()[2]
        # Write the level of severity to the dataframe
        scraped_API_dropna.iloc[index]["Severity"] = sev_level
        # Shorten the description - remove any severity and evidence information
        text = detokenizer.detokenize(tokens[: trigram_list.index(sev)])
        text = re.sub("\s*,\s*", ", ", text)
        text = re.sub("\s*\.\s*", ". ", text)
        text = re.sub("\s*\?\s*", "? ", text)
        row["Description_short"] = text
    else:
        row["Description_short"] = row["Description"]
    # If the evidence description is contained in the description
    if evid in descr:
        # Take the position of the trigram that contains the level of evidence
        evid_level_index = trigram_list.index(evid) + 2
        # Take the token describing the level of evidence
        evid_level = trigram_list[evid_level_index].split()[2]
        # Write the level of evidence to the dataframe
        scraped_API_dropna.iloc[index]["Evidence"] = evid_level

# Drop the original description column
scraped_API_dropna.drop("Description", axis=1, inplace=True)

FILE_NAME = "data_extraction/output/bnf_ddi_data.csv"

print("saving to file...")
# Save the dataset to a csv file.
scraped_API_dropna.to_csv(FILE_NAME, sep=",", index=False, encoding="utf-8")
