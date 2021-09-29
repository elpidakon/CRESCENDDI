# Kontsioti, Maskell, Dutta & Pirmohamed, A reference set of clinically relevant
# adverse drug-drug interactions (2021)
# Code to extract drug-drug interaction (DDI) data from the Micromedex website

# Replace with the URL of the Micromedex webpage where you put
# your login credentials (e.g., OpenAthens)
URL_MAINPAGE = "micromedex-login-webpage"

# You need to download Chromedriver.

# Replace 'executable/path/to/chromedriver' with the path to the
# chromedriver folder.
chromedriver_path = "executable/path/to/chromedriver"
# Replace 'your-username' and 'your-password' with the credentials
# you use to access Micromedex
micromedex_user = "your-username"
micromedex_pass = "your-pass"

import pandas as pd
import json
from pprint import pprint
import urllib
from urllib.request import urlopen
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import ErrorInResponseException
from selenium.common.exceptions import NoSuchElementException
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup, SoupStrainer
import requests
import html
import time
import collections
import PySimpleGUI as sg
import webbrowser
import csv
import re
from nltk.tokenize import sent_tokenize, word_tokenize
from itertools import chain

# Link to terms of use
url = "https://www.ibm.com/legal"

sg.theme("DarkBlue")
font = ("Courier New", 10, "underline")

# Pop-up window to confirm that the user compliers with Micromedex T&Cs.
layout = [
    [sg.Text("I comfirm that I agree to the terms of use associated with Micromedex:")],
    [[sg.Text(url, tooltip=url, enable_events=True, font=font, key=f"URL {url}")]],
    [sg.Button("No"), sg.Button("Yes")],
]
window = sg.Window("Terms of Use Agreement", layout, size=(520, 150), finalize=True)

window.BringToFront()

while True:
    event, values = window.read()
    if event == sg.WINDOW_CLOSED:
        break
    elif event.startswith("URL "):
        url = event.split(" ")[1]
        webbrowser.open(url)
    elif event == "No":
        sg.popup_cancel("User aborted")
        break
    elif event == "Yes":
        sg.popup("You can continue.")
        window.close()

        # Replace with the URL of the Micromedex webpage where you put
        # your login credentials (e.g., OpenAthens)
        URL_MAINPAGE = "micromedex-login-webpage"

        driver = webdriver.Chrome(executable_path=chromedriver_path)
        driver.get(URL_MAINPAGE)
        # Automated submission of Micromedex credentials
        driver.find_element_by_name("username").send_keys(micromedex_user)
        driver.find_element_by_name("password").send_keys(micromedex_pass)
        driver.find_element_by_css_selector(".btn.btn-primary.btn-block").click()
        # Link to the Drug Classes webpage in Micromedex
        driver.get(
            "http://www.micromedexsolutions.com/micromedex2/librarian/CS/9EE748/ND_PR/evidencexpert/ND_P/evidencexpert/DUPLICATIONSHIELDSYNC/8BB251/ND_PG/evidencexpert/ND_B/evidencexpert/ND_AppProduct/evidencexpert/ND_T/evidencexpert/PFActionId/evidencexpert.DoIntegratedSearch?SearchTerm=drug+class&navitem=DrugClasses"
        )

        # Get URLs related to drug classes
        soup = BeautifulSoup(driver.page_source, "lxml")
        elms = soup.select("div.fullBN a")
        URL_categories = []
        for e in range(len(elms)):
            temp_url = elms[e].attrs["href"]
            temp_text = elms[e].text
            temp = [str(temp_url), str(temp_text)]
            URL_categories.append(temp)

        URL_cat_df = pd.DataFrame(URL_categories, columns=["URL", "Name"])
        # Remove duplicate URLs.
        URL_cat_df = URL_cat_df[~URL_cat_df.duplicated(keep="first")]
        URL_cat_df = URL_cat_df.reset_index(drop=True)

        driver = webdriver.Chrome(executable_path=chromedriver_path)
        driver.get(URL_MAINPAGE)
        # Automated submission of Micromedex credentials
        driver.find_element_by_name("username").send_keys(micromedex_user)
        driver.find_element_by_name("password").send_keys(micromedex_pass)
        driver.find_element_by_css_selector(".btn.btn-primary.btn-block").click()

        # Get URLs related to drugs from each drug class.
        URL_drugs = []
        for w in range(len(URL_cat_df)):
            driver.get(URL_cat_df["URL"][w])
            soup2 = BeautifulSoup(driver.page_source, "lxml")
            elms = soup2.select("div.fullBN a")
            for e in range(len(elms)):
                temp_url = elms[e].attrs["href"]
                temp_text = elms[e].text
                temp = [str(temp_url), str(temp_text), URL_cat_df["Name"][w]]
                URL_drugs.append(temp)

        URL_drugs_df = pd.DataFrame(URL_drugs, columns=["URL", "Drug_Name", "Category"])
        # Export URLs to a csv file.
        URL_drugs_df.to_csv("URL_drugs_and_categories_micromedex.csv")

        # Drop duplicated rows.
        URL_drugs_df = URL_drugs_df.drop_duplicates(subset=["Drug_Name"])
        URL_drugs_df = URL_drugs_df.reset_index(drop=True)
        # Create a dictionary with drug names and corresponding URLs.
        URL_drugs_dict = (
            URL_drugs_df[["URL", "Drug_Name"]].set_index("Drug_Name").to_dict("index")
        )

        driver = webdriver.Chrome(executable_path=chromedriver_path)
        driver.get(URL_MAINPAGE)
        # Automated submission of Micromedex credentials.
        driver.find_element_by_name("username").send_keys(micromedex_user)
        driver.find_element_by_name("password").send_keys(micromedex_pass)
        driver.find_element_by_css_selector(".btn.btn-primary.btn-block").click()
        driver.get(
            "http://www.micromedexsolutions.com/micromedex2/librarian/CS/9EE748/ND_PR/evidencexpert/ND_P/evidencexpert/DUPLICATIONSHIELDSYNC/8BB251/ND_PG/evidencexpert/ND_B/evidencexpert/ND_AppProduct/evidencexpert/ND_T/evidencexpert/PFActionId/evidencexpert.DoIntegratedSearch?SearchTerm=drug+class&navitem=DrugClasses"
        )

        # Access drug URLs to get DDI information.
        output_list = []
        for i in range(len(URL_drugs_df)):
            # print(i)
            while True:
                try:
                    driver.get(URL_drugs_df["URL"][i])
                    break  # you can also check the returned status before breaking the loop
                except ErrorInResponseException as exception:
                    time.sleep(300)  # wait 5 mins before retry
                    driver = webdriver.Chrome(executable_path=chromedriver_path)
                    driver.get(URL_MAINPAGE)
                    driver.find_element_by_name("username").send_keys(micromedex_user)
                    driver.find_element_by_name("password").send_keys(micromedex_pass)
                    driver.find_element_by_css_selector(
                        ".btn.btn-primary.btn-block"
                    ).click()
                    driver.get(
                        "http://www.micromedexsolutions.com/micromedex2/librarian/CS/9EE748/ND_PR/evidencexpert/ND_P/evidencexpert/DUPLICATIONSHIELDSYNC/8BB251/ND_PG/evidencexpert/ND_B/evidencexpert/ND_AppProduct/evidencexpert/ND_T/evidencexpert/PFActionId/evidencexpert.DoIntegratedSearch?SearchTerm=drug+class&navitem=DrugClasses"
                    )

            time.sleep(5)

            try:
                driver.find_element_by_link_text("In-Depth Answers").click()
                time.sleep(10)
                driver.find_element_by_link_text("Drug Interactions (single)").click()
                time.sleep(40)
            # If no DDIs are included:
            except NoSuchElementException as exception:
                continue

            # Extract content related to DDIs.
            soup3 = BeautifulSoup(driver.page_source, "lxml")
            links = soup3.find_all("a", id=lambda x: x and x.endswith("Section"))

            drug_name = URL_drugs_df["Drug_Name"][i]

            for link in links:
                scraped_info = []
                scraped_info.append(drug_name)
                name = link.findNext().text
                scraped_info.append(name)
                text = link.findNext("div", {"class": "item_list"}).text
                scraped_info.append(text)

                output_list.append(scraped_info)

window.close()

# Write extracted information to a dataframe
micromedex_raw = pd.DataFrame(
    output_list, columns=["Drug_Name", "Interactant_Name", "Information"]
)


def descr_separator(raw_info):
    part1 = raw_info.partition("2) Summary: ")
    interaction_effect = part1[0].replace("1) Interaction Effect: ", "")
    part2 = part1[2].partition("3) Severity: ")
    summary = part2[0]
    part3 = part2[2].partition("4) Onset: ")
    severity = part3[0]
    part4 = part3[2].partition("5) Substantiation: ")
    onset = part4[0]
    part5 = part4[2].partition("6) Clinical Management: ")
    substantiation = part5[0]
    part6 = part5[2].partition("7) Probable Mechanism: ")
    clin_mgment = part6[0]
    if "8) Literature Reports" in part6[2]:
        part7 = part6[2].partition("8) Literature Reports")
        prob_mech = part7[0]
    else:
        prob_mech = part6[2]
    return (
        interaction_effect,
        summary,
        severity,
        onset,
        substantiation,
        clin_mgment,
        prob_mech,
    )


# Create an empty dataframe for the processed data
micromedex_data = pd.DataFrame()
# Isolate the interaction effect
info = micromedex_raw["Information"].astype(str).apply(descr_seperator)
# Create a new dataframe containing the seperated info
details_df = pd.DataFrame(
    list(info),
    columns=[
        "Interaction_Effect",
        "Summary",
        "Severity",
        "Onset",
        "Substantiation",
        "Clinical_Management",
        "Probable_Mechanism",
    ],
)
# Append the corresponding columns to the dataframe
micromedex_data["drug_name"] = micromedex_raw["Drug_Name"]
micromedex_data["interactant_name"] = micromedex_raw["Interactant_Name"]
micromedex_data["interaction_effect"] = details_df["Interaction_Effect"]
micromedex_data["severity"] = details_df["Severity"]
micromedex_data["substantiation"] = details_df["substantiation"]
micromedex_data = micromedex_data.reset_index(drop=True)


# Convert all drug name entries to lowercase
micromedex_data["drug_name"] = micromedex_data["drug_name"].str.lower()
micromedex_data["interactant_name"] = micromedex_data["interactant_name"].str.lower()
# Return True if the drug name is alphabetically after the interactant
idx = micromedex_data["drug_name"] > micromedex_data["interactant_name"]
# Place all pairs in alphabetical order (drug name before interactant in all instances)
micromedex_data.loc[idx, ["drug_name", "interactant_name"]] = micromedex_data.loc[
    idx, ["interactant_name", "drug_name"]
].values
# Sort alphabetically
micromedex_data = micromedex_data.sort_values(by=["drug_name", "interactant_name"])

# Remove duplicates and reset index
micromedex_data = micromedex_data.drop_duplicates().reset_index(drop=True)

FILE_NAME = "data_extraction/output/micromedex_ddi_data.csv"

# Write the processed data to a csv file
micromedex_data.to_csv(FILE_NAME, index=False, encoding="utf-8")
