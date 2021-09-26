# Kontsioti, Maskell, Dutta & Pirmohamed, A reference set of clinically relevant
# adverse drug-drug interactions (2021)
# This script calculates scores of the signal detection algorithms for single
# drugs.

library(dplyr)
library(tidyverse)
library(readxl)
library(openEBGM)
library(PhViD)
library(tictoc)
library(knitr)
library(kableExtra)
library(stringr)

set.seed(483726)

## You need to load the table standard_drug_ingr_outcome_count_tbl with
## drug-event FAERS counts AND the total no of FAERS reports (n..)

# A. MGPS and PRR

## Drug-Event pair FAERS counts
proc <- data.frame(
  var1 = standard_drug_ingr_outcome_count_tbl$drug_concept_id,
  var2 = standard_drug_ingr_outcome_count_tbl$outcome_concept_id,
  N = standard_drug_ingr_outcome_count_tbl$drug_ingr_outcome_pair_count,
  E = standard_drug_ingr_outcome_count_tbl$E,
  RR = standard_drug_ingr_outcome_count_tbl$RR,
  PRR = standard_drug_ingr_outcome_count_tbl$PRR,
  stringsAsFactors = FALSE
)
proc$var1 <- as.character(proc$var1)
proc$var2 <- as.character(proc$var2)
proc$N <- as.integer(proc$N)

squashed <- squashData(proc)

# Initial theta values
theta_init <- data.frame(
  alpha1 = c(0.2, 0.1, 0.3, 0.5, 0.2),
  beta1 = c(0.1, 0.1, 0.5, 0.3, 0.2),
  alpha2 = c(2, 10, 6, 12, 5),
  beta2 = c(4, 10, 6, 12, 5),
  p = c(1 / 3, 0.2, 0.5, 0.8, 0.4)
)

# Hyperparameter estimation
hyper_estimate_tbl <- exploreHypers(
  squashed,
  theta_init,
  squashed = TRUE,
  zeroes = FALSE,
  N_star = 1,
  method = "nlm",
  param_limit = 100,
  max_pts = 3000000,
  std_errors = TRUE
)

# Get hyperparameter estimates
hyper_estimate <- hyper_estimate_tbl$estimates
hyper_estimate <- as.numeric(hyper_estimate[5, 2:6])

# EBGM scores for drug-event pairs
ebout <- ebScores(proc,
  hyper_estimate = list(estimates = hyper_estimate),
  quantiles = c(5, 95)
) # For the 5th and 95th percentiles

# B. BCPNN
# Data table to be used as import
cont_tbl <- data.frame(
  var1 = standard_drug_ingr_outcome_count_tbl$drug_concept_id,
  var2 = standard_drug_ingr_outcome_count_tbl$outcome_concept_id,
  a = standard_drug_ingr_outcome_count_tbl$drug_ingr_outcome_pair_count,
  b = (standard_drug_ingr_outcome_count_tbl$n_.1 -
    standard_drug_ingr_outcome_count_tbl$drug_ingr_outcome_pair_count),
  c = (standard_drug_ingr_outcome_count_tbl$n_1. -
    standard_drug_ingr_outcome_count_tbl$drug_ingr_outcome_pair_count)
)

cont_tbl$d <- n_.. - cont_tbl$a - cont_tbl$b - cont_tbl$c

DATABASE <- list()
DATABASE$L <- data.frame(
  "Drug lab" = standard_drug_ingr_outcome_count_tbl$drug_concept_id,
  "AE lab" = standard_drug_ingr_outcome_count_tbl$outcome_concept_id
)
DATABASE$data <- matrix(
  nrow = nrow(standard_drug_ingr_outcome_count_tbl),
  ncol = 3
)

rownames(DATABASE$data) <- paste0(
  standard_drug_ingr_outcome_count_tbl$drug_concept_id,
  " ",
  standard_drug_ingr_outcome_count_tbl$outcome_concept_id
)
colnames(DATABASE$data) <- c("n11", "n1.", "n.1")

DATABASE$data[, 1] <- 
  as.numeric(standard_drug_ingr_outcome_count_tbl$drug_ingr_outcome_pair_count)
DATABASE$data[, 2] <- as.numeric(standard_drug_ingr_outcome_count_tbl$n_1.)
DATABASE$data[, 3] <- as.numeric(standard_drug_ingr_outcome_count_tbl$n_.1)
head(DATABASE$data)

DATABASE$N <- n_..

res <- PhViD::BCPNN(DATABASE,
  RR0 = 1, MIN.n11 = 1, DECISION = 1,
  DECISION.THRES = 0.05, RANKSTAT = 1, MC = FALSE,
  NB.MC = 10000
)
res_2 <- PhViD::BCPNN(DATABASE,
  RR0 = 1, MIN.n11 = 1, DECISION = 1,
  DECISION.THRES = 0.05, RANKSTAT = 2, MC = FALSE,
  NB.MC = 10000
)

post_H0 <- res$ALLSIGNALS[, c("drug code", "event effect", "count", "post.H0")]

quant <- res_2$ALLSIGNALS[, c("drug code", "event effect", "Q_0.025(log(IC))")]

############## GET COUNTS #####################################

# Map drug and event names to OHDSI concepts
# Load spreadsheets
drug_mappings <- read_excel("data_records/Data Record 4 - Drug mappings.xlsx")
event_mappings <-
  read_excel("data_records/Data Record 5 - Event mappings v0.1 - PT mappings.xlsx")
# Remove unnecessary columns
drug_mappings[, c("DRUG_INITIAL_NAME", "SOURCE")] <- list(NULL)
event_mappings <- event_mappings[, c("PT_CONCEPT_NAME", "PT_CONCEPT_ID")]
# Convert to lowercase
drug_mappings$DRUG_CONCEPT_NAME <- tolower(drug_mappings$DRUG_CONCEPT_NAME)
event_mappings$PT_CONCEPT_NAME <- tolower(event_mappings$PT_CONCEPT_NAME)
# Drop duplicated rows from mapping tables
drug_mappings <- drug_mappings %>% distinct()
event_mappings <- event_mappings %>% distinct()

single_counts_datafile <-
  "single_drugs/output/Data Record 3 - Single-drug ADRs, indications and negative controls.xlsx"

pos_ctls_tbl <- read_excel(single_counts_datafile, sheet = "Tab1 - Positive")
# Restrict to adverse events
pos_ctls_tbl <- pos_ctls_tbl %>% filter(EVENT_TYPE == "Adverse event")
pos_ctls_tbl$EVENT_TYPE <- NULL

## Negative controls
neg_ctls_tbl <- read_excel(single_counts_datafile, sheet = "Tab2 - Negative")
neg_ctls_tbl$indicator <- 0
neg_ctls_tbl[, "SOURCE"] <- NA
# Convert to lowercase
neg_ctls_tbl$DRUG_CONCEPT_NAME <- tolower(neg_ctls_tbl$DRUG_CONCEPT_NAME)
neg_ctls_tbl$EVENT_CONCEPT_NAME <- tolower(neg_ctls_tbl$EVENT_CONCEPT_NAME)
# Map negative controls
neg_ctls_tbl <- neg_ctls_tbl %>%
  merge(drug_mappings, by = "DRUG_CONCEPT_NAME", all.x = TRUE)
neg_ctls_tbl <- neg_ctls_tbl %>%
  merge(event_mappings,
    by.x = "EVENT_CONCEPT_NAME",
    by.y = "PT_CONCEPT_NAME", all.x = TRUE
  )


## METHOD A: INTERSECTION of resources for positive controls
# Find only common drug-event pairs between the two sources (intersection)
intersect_pos_ctls_tbl <- pos_ctls_tbl[duplicated(pos_ctls_tbl[, 1:2]), ]
intersect_pos_ctls_tbl$SOURCE <- "BNF+SIDER"
intersect_pos_ctls_tbl$indicator <- 1
# Convert to lowercase
intersect_pos_ctls_tbl$DRUG_CONCEPT_NAME <-
  tolower(intersect_pos_ctls_tbl$DRUG_CONCEPT_NAME)
intersect_pos_ctls_tbl$EVENT_CONCEPT_NAME <-
  tolower(intersect_pos_ctls_tbl$EVENT_CONCEPT_NAME)

intersect_pos_ctls_tbl <- intersect_pos_ctls_tbl %>%
  merge(drug_mappings, by = "DRUG_CONCEPT_NAME", all.x = TRUE)
intersect_pos_ctls_tbl <- intersect_pos_ctls_tbl %>%
  merge(event_mappings,
    by.x = "EVENT_CONCEPT_NAME",
    by.y = "PT_CONCEPT_NAME", all.x = TRUE
  )
# Remove rows with HLT/HLGT (unmapped) concepts
intersect_pos_ctls_tbl <- intersect_pos_ctls_tbl %>% filter(!is.na(PT_CONCEPT_ID))

intersect_ctls_tbl <- rbind(intersect_pos_ctls_tbl, neg_ctls_tbl)
intersect_ctls_tbl$`RXNORM_CODE/RXNORM_EXTENSION_CODE (OHDSI)` <-
  as.character(intersect_ctls_tbl$`RXNORM_CODE/RXNORM_EXTENSION_CODE (OHDSI)`)
intersect_ctls_tbl$PT_CONCEPT_ID <- as.character(intersect_ctls_tbl$PT_CONCEPT_ID)

## Retrieve values from ebout for union controls
intersect_ctls_tbl <- intersect_ctls_tbl %>%
  merge(ebout[["data"]],
    by.x = c(
      "RXNORM_CODE/RXNORM_EXTENSION_CODE (OHDSI)",
      "PT_CONCEPT_ID"
    ),
    by.y = c("var1", "var2"), all.x = TRUE
  )

## Retrieve values from post_H0 and Q_0.025(log(IC)) (BCPNN) for union controls
intersect_ctls_tbl <- intersect_ctls_tbl %>%
  merge(post_H0,
    by.x = c(
      "RXNORM_CODE/RXNORM_EXTENSION_CODE (OHDSI)",
      "PT_CONCEPT_ID"
    ),
    by.y = c("drug code", "event effect"), all.x = TRUE
  )

intersect_ctls_tbl <- intersect_ctls_tbl %>%
  merge(quant,
    by.x = c(
      "RXNORM_CODE/RXNORM_EXTENSION_CODE (OHDSI)",
      "PT_CONCEPT_ID"
    ),
    by.y = c("drug code", "event effect"), all.x = TRUE
  )

# Write to a .csv file
write.csv(
  intersect_ctls_tbl,
  "faers_screening/output/single_drug_resource_union_scores.csv"
)

## METHOD B: UNION of resources for positive controls
only_one_pos_ctls_tbl <- anti_join(pos_ctls_tbl, intersect_pos_ctls_tbl,
  by = c("DRUG_CONCEPT_NAME", "EVENT_CONCEPT_NAME")
)
union_pos_ctls_tbl <- rbind(intersect_pos_ctls_tbl, only_one_pos_ctls_tbl)
union_pos_ctls_tbl$indicator <- 1
# Convert to lowercase
union_pos_ctls_tbl$DRUG_CONCEPT_NAME <-
  tolower(union_pos_ctls_tbl$DRUG_CONCEPT_NAME)
union_pos_ctls_tbl$EVENT_CONCEPT_NAME <-
  tolower(union_pos_ctls_tbl$EVENT_CONCEPT_NAME)

union_pos_ctls_tbl <- union_pos_ctls_tbl %>%
  merge(drug_mappings, by = "DRUG_CONCEPT_NAME", all.x = TRUE)
union_pos_ctls_tbl <- union_pos_ctls_tbl %>%
  merge(event_mappings,
    by.x = "EVENT_CONCEPT_NAME",
    by.y = "PT_CONCEPT_NAME", all.x = TRUE
  )
# Remove rows with HLT/HLGT (unmapped) concepts
union_pos_ctls_tbl <- union_pos_ctls_tbl %>% filter(!is.na(PT_CONCEPT_ID))


union_ctls_tbl <- rbind(union_pos_ctls_tbl, neg_ctls_tbl)
union_ctls_tbl$`RXNORM_CODE/RXNORM_EXTENSION_CODE (OHDSI)` <-
  as.character(union_ctls_tbl$`RXNORM_CODE/RXNORM_EXTENSION_CODE (OHDSI)`)
union_ctls_tbl$PT_CONCEPT_ID <- as.character(union_ctls_tbl$PT_CONCEPT_ID)

## Retrieve values from ebout for union controls
union_ctls_tbl <- union_ctls_tbl %>%
  merge(ebout[["data"]],
    by.x = c(
      "RXNORM_CODE/RXNORM_EXTENSION_CODE (OHDSI)",
      "PT_CONCEPT_ID"
    ),
    by.y = c("var1", "var2"), all.x = TRUE
  )

## Retrieve values from post_H0 and Q_0.025(log(IC)) (BCPNN) for union controls
union_ctls_tbl <- union_ctls_tbl %>%
  merge(post_H0,
    by.x = c(
      "RXNORM_CODE/RXNORM_EXTENSION_CODE (OHDSI)",
      "PT_CONCEPT_ID"
    ),
    by.y = c("drug code", "event effect"), all.x = TRUE
  )

union_ctls_tbl <- union_ctls_tbl %>%
  merge(quant,
    by.x = c(
      "RXNORM_CODE/RXNORM_EXTENSION_CODE (OHDSI)",
      "PT_CONCEPT_ID"
    ),
    by.y = c("drug code", "event effect"), all.x = TRUE
  )

# Write to a .csv file
write.csv(
  union_ctls_tbl,
  "faers_screening/output/single_drug_resource_intersection_scores.csv"
)