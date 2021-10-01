# Technical Validation - Text description mapping for AEs
 
# Read file
text = pd.read_excel("data_records/Data Record 5 - Event mappings.xlsx")
# Get unique descriptions
descriptions = pd.Series(list(set(text['EVENT_INITIAL_TEXT'])))
# Random selection of 100 text descriptions
text_sample = descriptions.sample(n=100, random_state=1)
# Export to a .csv file
text_sample.to_csv("technical_validation/validation_files/validation_event_text.csv")
