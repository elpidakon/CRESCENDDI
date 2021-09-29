/* Kontsioti, Maskell, Dutta & Pirmohamed, A reference set of clinically relevant adverse drug-drug interactions (2021) */
/* SAS script to calculate delta_add scores for DDI controls.

/* Positive controls */
PROC IMPORT DATAFILE="faers_screening/data/DR1_FAERS_COUNTS_FOR_SAS.xlsx"
     DBMS=XLSX
     OUT=WORK.test REPLACE;
RUN;

DATA test1; 
   SET test;
   KEEP no A B y n;
RUN;

proc sort data=work.test1 out=work.test1_sorted;
   by no;
run;

/* the data set name is 'Output1' */
ods output ParameterEstimates=Output1;        

proc genmod data=work.test1_sorted; 
class A B / param=ref ref=first; 
model y/n= A B A*B / dist=binomial link=identity;
	by no;
	quit;
 
proc print data=Output1 noobs;
run;

proc export 
  data=work.output1 
  dbms=xlsx 
  outfile="faers_screening/output/DR1_DELTA_VALUES.xlsx" 
  replace;
run;

/* Negative controls */
PROC IMPORT DATAFILE="faers_screening/data/DR2_FAERS_COUNTS_FOR_SAS.xlsx"
     DBMS=XLSX
     OUT=WORK.test REPLACE;
RUN;

DATA test2; 
   SET test;
   KEEP no A B y n;
RUN;

proc sort data=work.test2 out=work.test2_sorted;
   by no;
run;

/* the data set name is 'Output2' */
ods output ParameterEstimates=Output2;        

proc genmod data=work.test2_sorted; 
class A B / param=ref ref=first; 
model y/n= A B A*B / dist=binomial link=identity;
	by no;
	quit;
 
proc print data=Output2 noobs;
run;

proc export 
  data=work.output2 
  dbms=xlsx 
  outfile="faers_screening/output/DR2_DELTA_VALUES.xlsx" 
  replace;
run;
