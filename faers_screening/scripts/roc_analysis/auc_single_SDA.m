% Kontsioti, Maskell, Dutta & Pirmohamed, A reference set of clinically
% relevant adverse drug-drug interactions (2021) This script calculates AUC
% scores for the single-drug signal detection algorithms (i.e. PRR, EBGM,
% BCPNN)

rng default;

stats = {'PRR','EBGM','Q_0025logIC'};

% Resource union
union_clt_tbl = singledrugresourceunionscores(:,{'No','SOURCE','PRR', ...
    'EBGM','Q_0025logIC','indicator', 'N'});

union_AUC_vector = zeros(size(stats,1),3);

label = union_clt_tbl(:,'indicator');
label_cell = table2cell(label);

for k=1:length(stats)
    curstat=stats{k};
    scores = table2array(union_clt_tbl(:,curstat));
    scores_cell = num2cell(scores);
    [X,Y,T, AUC] = perfcurve(label_cell,scores_cell,1,'XVals', [0:0.05:1], 'Alpha',0.05, 'BootType', 'student');
    union_AUC_vector(k,:) = AUC;
end

% Resource intersection
intersect_clt_tbl = singledrugresourceintersectscores(:,{'No','SOURCE', ...
    'PRR','EBGM','Q_0025logIC','indicator', 'N'});

intersect_AUC_vector = zeros(size(stats,1),3);

label = intersect_clt_tbl(:,'indicator');
label_cell = table2cell(label);

for k=1:length(stats)
    curstat=stats{k};
    scores = table2array(intersect_clt_tbl(:,curstat));
    scores_cell = num2cell(scores);
    [X,Y,T, AUC] = perfcurve(label_cell,scores_cell,1,'XVals',[0:0.05:1], ...
        'Alpha',0.05, 'BootType', 'student');
    intersect_AUC_vector(k,:) = AUC;
end
