# Kontsioti, Maskell, Dutta & Pirmohamed, A reference set of clinically relevant adverse drug-drug interactions (2021)
# This script calculates Interaction Signal Score (INtSS) values for the DDI controls.

library(dplyr)    
library(tidyverse)
library(readxl)
library(openEBGM)
library(tictoc)
library(knitr)
library(kableExtra)
library(stringr)

set.seed(483726)

## Drug-Event pair FAERS counts - You need to load the table standard_drug_ingr_outcome_count_tbl from FAERS
single_proc <- data.frame(var1=standard_drug_ingr_outcome_count_tbl$drug_concept_id,
                          var2=standard_drug_ingr_outcome_count_tbl$outcome_concept_id, 
                          N=standard_drug_ingr_outcome_count_tbl$drug_ingr_outcome_pair_count, 
                          E=standard_drug_ingr_outcome_count_tbl$E,
                          RR=standard_drug_ingr_outcome_count_tbl$RR,
                          PRR= "N/A",
                          stringsAsFactors=FALSE)
single_proc$var1 <-as.character(single_proc$var1)
single_proc$var2 <- as.character(single_proc$var2)
single_proc$N <- as.integer(single_proc$N)

## Import DDI controls
pos_counts_datafile = 'faers_screening/data/DR1_FAERS_COUNTS.xlsx'
neg_counts_datafile = 'faers_screening/data/DR2_FAERS_COUNTS.xlsx'
# Positive controls
pos_ctls_tbl <- read_excel(pos_counts_datafile)
pos_ctls_tbl$dde_tuple_copy <- pos_ctls_tbl$dde_tuple
# Remove the first and last character and split concept_ids to separate columns
pos_ctls_tbl$dde_tuple_copy <- substr(pos_ctls_tbl$dde_tuple_copy,2,nchar(pos_ctls_tbl$dde_tuple_copy)-1)
pos_ctls_tbl <- pos_ctls_tbl %>%
          separate(dde_tuple_copy, c("DRUG_1_CONCEPT_ID", "DRUG_2_CONCEPT_ID", "EVENT_CONCEPT_ID"), sep = ", ")
pos_ctls_tbl$indicator <- 1
# Negative controls
neg_ctls_tbl <- read_excel(neg_counts_datafile)
neg_ctls_tbl$dde_tuple_copy <- neg_ctls_tbl$dde_tuple
# Remove the first and last character and split concept_ids to separate columns
neg_ctls_tbl$dde_tuple_copy <- substr(neg_ctls_tbl$dde_tuple_copy,2,nchar(neg_ctls_tbl$dde_tuple_copy)-1)
neg_ctls_tbl <- neg_ctls_tbl %>%
  separate(dde_tuple_copy, c("DRUG_1_CONCEPT_ID", "DRUG_2_CONCEPT_ID", "EVENT_CONCEPT_ID"), sep = ", ")
neg_ctls_tbl$indicator <- 0

# Concatenate positive and negative controls
ctls_tbl <- rbind(pos_ctls_tbl, neg_ctls_tbl)
ctls_tbl$DRUG_1_CONCEPT_ID <- as.character(ctls_tbl$DRUG_1_CONCEPT_ID)
ctls_tbl$DRUG_2_CONCEPT_ID <- as.character(ctls_tbl$DRUG_2_CONCEPT_ID)
ctls_tbl$EVENT_CONCEPT_ID <- as.character(ctls_tbl$EVENT_CONCEPT_ID)

# Generate a df with drug-drug-event triplet counts from FAERS (this will be used as an input for hyperparameter estimation)
pair_proc <- data.frame(var1=character(),
                        var2=character(), 
                        N=integer(), 
                        E=double(),
                        RR=double(),
                        PRR=double(),
                        stringsAsFactors=FALSE) 

for (row in 1:nrow(ctls_tbl)) {
  d1 <- ctls_tbl[row, "DRUG_1_CONCEPT_ID"]
  d2 <- ctls_tbl[row, "DRUG_2_CONCEPT_ID"]
  pt <- ctls_tbl[row, "EVENT_CONCEPT_ID"]
  n_11. <- as.numeric(ctls_tbl[row, "d1_d2_counter"])
  n_111 <- as.numeric(ctls_tbl[row, "n_111"])
  n_1.1 <- as.numeric(ctls_tbl[row, "n_111"] + ctls_tbl[row, "n_101"])
  n_.11 <- as.numeric(ctls_tbl[row, "n_111"] + ctls_tbl[row, "n_011"])
  n_1.. <- as.numeric(ctls_tbl[row, "d1_d2_counter"] + ctls_tbl[row, "d1_not_d2_counter"])
  n_.1. <- as.numeric(ctls_tbl[row, "d1_d2_counter"] + ctls_tbl[row, "not_d1_d2_counter"])
  n_..1 <- as.numeric(n_1.1 + ctls_tbl[row, "n_001"] + ctls_tbl[row, "n_011"])
  n_... <- as.numeric(n_1.. + ctls_tbl[row, "not_d1_d2_counter"] + ctls_tbl[row, "not_d1_not_d2_counter"] ) 
  # Counts for drug pair
  pair_proc[row, ] <- list(paste(d1,d2,sep = "||", collapse = NULL),as.character(pt),n_111,(n_11.*n_..1)/n_...,(n_111*n_...)/(n_11.*n_..1),(n_111*(n_...-n_11.)/(n_11.*(n_..1-n_111))))
}
pair_proc$N <- as.integer(pair_proc$N)

# Concatenate the two dataframes
proc <- rbind(single_proc, pair_proc)
squashed <- squashData(proc)

# Initial theta values
theta_init <- data.frame(alpha1 = c(0.2, 0.1, 0.3, 0.5, 0.2),
                         beta1  = c(0.1, 0.1, 0.5, 0.3, 0.2),
                         alpha2 = c(2,   10,  6,   12,  5),
                         beta2  = c(4,   10,  6,   12,  5),
                         p      = c(1/3, 0.2, 0.5, 0.8, 0.4)
)

# Hyperparameter estimation
hyper_estimate_tbl <- exploreHypers(
  squashed,
  theta_init,
  squashed = TRUE,
  zeroes = TRUE,
  N_star = NULL,
  method = "nlm",
  param_limit = 100,
  max_pts = 3000000,
  std_errors = TRUE
)

# Get hyperparameter estimates
hyper_estimate <- hyper_estimate_tbl$estimates 
hyper_estimate <- as.numeric(hyper_estimate[5, 2:6])

# EBGM scores for drug-event pairs
single_ebout <- ebScores(single_proc, hyper_estimate = list(estimates = hyper_estimate),
                         quantiles = c(5, 95)) #For the 5th and 95th percentiles
# EBGM scores for drug-drug-event triplets 
pair_ebout <- ebScores(pair_proc, hyper_estimate = list(estimates = hyper_estimate),
                  quantiles = c(5, 95)) #For the 5th and 95th percentiles

## Generate a pair_df and use ebScores for single drugs by retrieving values from ebout in order to calculate the final IntSS
single_df <- as.data.frame(single_ebout["data"])
pair_df <- as.data.frame(pair_ebout["data"])

pair_df <- pair_df %>% 
  separate(data.var1, into = c("d1", "d2"), remove = FALSE)

pair_df <- pair_df %>% filter(data.N != 0)

for (row in 1:nrow(pair_df)) {
  d1_quant_95 <- single_df %>% filter(data.var1 == pair_df[row,"d1"]) %>%
    filter(data.var2 == pair_df[row,"data.var2"]) %>% select("data.QUANT_95")
  
  d2_quant_95 <- single_df %>% filter(data.var1 == pair_df[row,"d2"]) %>%
    filter(data.var2 == pair_df[row,"data.var2"]) %>% select("data.QUANT_95")
  pair_df[row, "data.IntSS"] <- pair_df[row, "data.QUANT_05"]/max(d1_quant_95[1,],d2_quant_95[1,]) 
}


new_pair_df <- right_join(pair_df, ctls_tbl[, c("no", "dde_tuple", "DRUG_1_CONCEPT_ID", "DRUG_2_CONCEPT_ID", "EVENT_CONCEPT_ID", "indicator")], 
                          by = c("d1" = "DRUG_1_CONCEPT_ID", "d2" = "DRUG_2_CONCEPT_ID", "data.var2" = "EVENT_CONCEPT_ID"))
new_pair_df <- unique(new_pair_df)

pos_ctls_intss <- new_pair_df %>% filter(indicator == 1) %>% select(no, dde_tuple, data.IntSS) %>% arrange(no)
neg_ctls_intss <- new_pair_df %>% filter(indicator == 0) %>% select(no, dde_tuple, data.IntSS) %>% arrange(no)

# Write dataframes with IntSS values to output files
write.csv(pos_ctls_intss, 'faers_screening/output/DR1_INTSS_VALUES.csv')
write.csv(neg_ctls_intss, 'faers_screening/output/DR2_INTSS_VALUES.csv')
