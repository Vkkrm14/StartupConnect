# Statistical Test Requirement Validation

## Dataset sanity checks (before inferential tests)
- Rows: 25200
- Missing values total: 0
- Duplicate run_id count: 0
- Binary fields valid (0/1): True
- Continuous fields non-negative: True
- Balanced rows per variant: {'V0': 5040, 'V1': 5040, 'V2': 5040, 'V3': 5040, 'V4': 5040}

## Executed inferential tests
- Tests observed in hypothesis table: ['Chi-square', 'Fisher exact', 'Mann-Whitney U']
- FDR q-value column present: True
- Effect size columns present: True
- Confidence interval columns present: True

## Notes on z-test and t-test necessity
- Proportion z-test is not mandatory here because Chi-square/Fisher exact already covers binary outcome comparisons.
- Welch t-test is implemented in the analysis template but not selected in this run; Mann-Whitney U was selected by the normality gate.