# Method and evidence boundaries

Completeness/uniqueness index: round(100 × (1 − null cells / cells) × (1 − exact duplicate rows / rows)). It is not a calibrated accuracy or fitness-for-purpose metric. Empty strings read directly into a DataFrame are not universally treated as null; CSV parsing converts conventional empty cells to missing values.

Checks: null counts and affected rows; exact full-row duplicates; duplicate non-null values in explicit ID-like columns; zero values in selected numeric business measures and absolute sample z-score above 3 when at least 21 non-null values are present; explicit SLA flags; exact risky-status matches. Numeric zero and z-score checks are context-sensitive screening rules.

Findings carry source column names, counts, descriptions and business implications. They may overlap, so summing affected-record counts does not produce a count of distinct problematic rows. Quality findings are capped at 15, workflow findings at 8, the combined list at 20 and recommendations at 6. The high-severity finding count applies to the returned list, not unlimited hidden findings.

Context hints count substrings in column headers across several generic business vocabularies. Ties or no matches return Generic / mixed dataset. Counts are not probabilities and header terms do not establish the industry.

Actions sort by illustrative severity, then affected-record count. No effort, impact, confidence or ROI is estimated. Human review determines whether an apparent problem is meaningful and what action is justified.

CSV UTF-8 headers must be unique and nonblank. Spreadsheet readers may normalize duplicate spreadsheet headers; this edition does not certify original XLSX header uniqueness. File size limits are checked before parsing; row/column limits apply after parsing. These are not a comprehensive malicious-file or decompression defense.
