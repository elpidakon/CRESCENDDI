# Kontsioti, Maskell, Dutta & Pirmohamed, A reference set of clinically relevant adverse drug-drug interactions (2021)
# Creates a single output file for single-drug ADRs, indications and negative controls

## BNF - ADRs
single_drug_adr_bnf = pd.read_csv('event_mapping/output/bnf_single_mapped_with_eventnames.csv')
single_drug_adr_bnf['EVENT_TYPE'] = 'Adverse event'
single_drug_adr_bnf['SOURCE'] = 'BNF'

## SIDER - ADRs
single_drug_adr_sider = pd.read_csv('event_mapping/output/sider_adr_table.csv')
single_drug_adr_sider['EVENT_TYPE'] = 'Adverse event'
single_drug_adr_sider['SOURCE'] = 'SIDER'

## SIDER - Indications
indi_df = pd.read_csv('event_mapping/output/sider_indi_table.csv')
indi_df['EVENT_TYPE'] = 'Indication'
indi_df['SOURCE'] = 'SIDER'

# Concatenate the positive drug-event associations
single_drug_pos_df = pd.concat([single_drug_adr_bnf, single_drug_adr_sider, indi_df])
single_drug_pos_df.drop(['DRUG_CONCEPT_ID', 'EVENT_CONCEPT_ID'], axis=1, inplace=True)

## Negative controls for single drugs
neg_df= pd.read_csv('single_drugs/output/single_drug_negative_controls.csv')
neg_df.columns = ['PubMed_query', 'DRUG_CONCEPT_NAME', 'EVENT_CONCEPT_NAME']
neg_df.drop('PubMed_query', axis=1, inplace=True)

## Get a single output (DR3) as an Excel spreadsheet
# Create a Pandas Excel writer using XlsxWriter as the engine.
writer = pd.ExcelWriter('data_records/Data Record 3 - Single-drug ADRs, indications and negative controls.xlsx', engine='xlsxwriter')
# Write each dataframe to a different worksheet.
single_drug_pos_df.to_excel(writer, sheet_name='Tab1 - Positive')
neg_df.to_excel(writer, sheet_name='Tab2 - Negative')
# Close the Pandas Excel writer and output the Excel file.
writer.save()
