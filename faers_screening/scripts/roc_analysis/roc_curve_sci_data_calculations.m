% Kontsioti, Maskell, Dutta & Pirmohamed, A reference set of clinically
% relevant adverse drug-drug interactions (2021) This script calculates AUC
% scores for the three DDI surveillance signal detection algorithms

rng default;

% A. Omega
pos_tbl = DR1_OMEGA_VALUES(:, {'dde_tuple', 'omega_025'});
pos_tbl = pos_tbl(find(~ isnan(pos_tbl.omega_025)), :);
pos_tbl = unique(pos_tbl, 'rows');
pos_tbl.posnegLabel = ones(size(pos_tbl, 1), 1);
neg_tbl = DR2_OMEGA_VALUES(:, {'dde_tuple', 'omega_025'});
neg_tbl = unique(neg_tbl, 'rows');
neg_tbl.posnegLabel = zeros(size(neg_tbl, 1), 1);
tbl = [pos_tbl; neg_tbl];

pos_median = median(table2array(tbl(tbl.posnegLabel == 1, 2)));
neg_median = median(table2array(tbl(tbl.posnegLabel == 0, 2)));

label = tbl(:, 'posnegLabel');
label_arr = table2array(label);
label_cell = table2cell(label);

scores = table2array(tbl(:, 'omega_025'));
scores_cell = num2cell(scores);
[Omega_X, Omega_Y, Omega_T, Omega_AUC] = perfcurve(label_cell, scores_cell, 1, 'XVals', [0:0.05:1]);

% B. Delta
pos_tbl = DR1_DELTA_VALUES(:, {'dde_tuple', 'Estimate'});
pos_tbl = unique(pos_tbl, 'rows');
pos_tbl.posnegLabel = ones(size(pos_tbl, 1), 1);
neg_tbl = DR2_DELTA_VALUES(:, {'dde_tuple', 'Estimate'});
neg_tbl = unique(neg_tbl, 'rows');
neg_tbl.posnegLabel = zeros(size(neg_tbl, 1), 1);
tbl = [pos_tbl; neg_tbl];

pos_median = median(table2array(tbl(tbl.posnegLabel == 1, 2)));
neg_median = median(table2array(tbl(tbl.posnegLabel == 0, 2)));

label = tbl(:, 'posnegLabel');
label_arr = table2array(label);
label_cell = table2cell(label);

scores = table2array(tbl(:, 'Estimate'));
scores_cell = num2cell(scores);
[Delta_X, Delta_Y, Delta_T, Delta_AUC] = perfcurve(label_cell, scores_cell, 1, 'XVals', [0:0.05:1]);

% C. Interaction Signal Score
pos_tbl = DR1_INTSS_VALUES(:, {'datavar1', 'datavar2', 'dataIntSS', 'indicator'});
pos_tbl = unique(pos_tbl, 'rows');
pos_tbl.posnegLabel = ones(size(pos_tbl, 1), 1);
neg_tbl = DR2_INTSS_VALUES(:, {'datavar1', 'datavar2', 'dataIntSS', 'indicator'});
neg_tbl = unique(neg_tbl, 'rows');
neg_tbl.posnegLabel = zeros(size(neg_tbl, 1), 1);
tbl = [pos_tbl; neg_tbl];

pos_median = median(table2array(tbl(tbl.indicator == 1, 3)));
neg_median = median(table2array(tbl(tbl.indicator == 0, 3)));

label = tbl(:, 'indicator');
label_arr = table2array(label);
label_cell = table2cell(label);

scores = table2array(tbl(:, 'dataIntSS'));
scores_cell = num2cell(scores);
[IntSS_X, IntSS_Y, IntSS_T, IntSS_AUC] = perfcurve(label_cell, scores_cell, 1, 'XVals', [0:0.05:1]);
