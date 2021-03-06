-- Kontsioti, Maskell, Dutta & Pirmohamed, A reference set of clinically relevant adverse drug-drug interactions (2021)
-- USAGI event name mapping table for Micromedex
-----------------------------------------------------------------------------------------------
set search_path = drug_interaction_compendia;
drop table if exists micromedex_event_usagi_mapping
;

CREATE TABLE micromedex_event_usagi_mapping
    (
        source_code             character varying
      , source_concept_id       character varying
      , source_vocabulary_id    character varying
      , source_code_description character varying
      , target_concept_id       integer
      , target_vocabulary_id    character varying
      , valid_start_date        character varying
      , valid_end_date          character varying
      , invalid_reason          character varying
    )