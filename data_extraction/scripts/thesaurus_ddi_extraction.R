# Kontsioti, Maskell, Dutta & Pirmohamed, A reference set of clinically relevant
# adverse drug-drug interactions (2021)
# This is a script to modify the Thesaurus dataframe (v2019) available by the
# IMthesaurusANSM R package.
# Following consultation with the IMthesaurus ANSM R package developer
# (Cossin S.), the script recodes severity levels from Thesaurus Rdata to
# capture the highest severity level associated with a DDI pair.
# The amended dataframe is extracted to a CSV file.

# get the current development version from github
# install.packages("devtools")
# devtools::install_github("scossin/IMthesaurusANSM")

library(miceadds)
library(dplyr)
library(tidyverse)
library(DBI)

## load thesaurus v2019
load("data_extraction/data/thesaurus/thesaurus092019.rdata")

## replacing all the therapeutic classes by their drug substances
df_decompose <- thesaurus092019$df_decompose
## remove any duplicates
df_decompose <- unique(df_decompose)

# Exclude rows that contain pairs with the same drug
df_decompose <- df_decompose[!(df_decompose$mol1 == df_decompose$mol2), ]

### Method1
## code severity - most severe if several levels associated with a single
## DDI pair
df_decompose$severity <- ifelse(!is.na(df_decompose$CI), 4,
  ifelse(!is.na(df_decompose$AD), 3,
    ifelse(!is.na(df_decompose$PE), 2,
      1
    )
  )
)

### Method2
## double check with DDI description
regex <- "^[A-Za-z]+"
df_decompose$level <- stringr::str_extract(
  df_decompose$description_interaction,
  regex
)
table(df_decompose$level)
## When it starts by - : what it means
# A : A prendre en compte (1)
# ASDEC : Association deconseillee (3)
# Association : Association deconseillee (3)
# CI : Contre indication (4)
# Contre : Contre indication (4)
# Precaution : Precaution d'emploi (2)

## recode
df_decompose$level <- as.factor(df_decompose$level)
levels(df_decompose$level) <- c("1", "3", "3", "4", "4", "2")
df_decompose$level <- as.numeric(as.character(df_decompose$level))

## check that Method1 and Method2 give the same results
all(df_decompose$level == df_decompose$severity) ## TRUE

# Keep the highest severity level
thesaurus_data <- df_decompose %>%
  arrange(desc(level)) %>%
  distinct(mol1, mol2, .keep_all = TRUE)

# Create an additional column by concatenating description_interaction and 
# mecanisme columns
thesaurus_data$description_combined <-
  paste(thesaurus_data$description_interaction, thesaurus_data$mecanisme)

# Keep only columns that we need and rename accordingly
thesaurus_data <- thesaurus_data[c(11, 12, 15, 13)]
colnames(thesaurus_data) <- c("drugname_1_original", "drugname_2_original", 
                              "description_combined", "severity")

# Export dataframe to a .csv file
FILE_NAME <- "data_extraction/output/thesaurus_ddi_data.csv"
write.csv(thesaurus_data, FILE_NAME, row.names = FALSE)
