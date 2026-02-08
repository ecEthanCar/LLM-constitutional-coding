# Constitutional LLM Analysis

Scalable LLM pipeline for analyzing constitutional text using Q&A-style questioning. Uses topological sorting for dependency scheduling and stateful context injection to handle conditional survey logic.

## Overview

This project automates the extraction of structured legal data from constitutional texts. Given a constitution and a standardized codebook of 147 survey questions, the system uses LLMs to produce machine-readable codings validated against human expert annotations.

The core challenge is that constitutional surveys are **hierarchical**: many questions are only relevant if a parent question was answered a certain way. The pipeline handles this through dependency-aware scheduling and stateful prompting.

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 1: Knowledge Base Construction                               │
│  Questions.docx → [extract] → [dependencies] → [scheduler]          │
│  Output: Questions sorted into levels [L0, L1, L2, L3]              │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 2: Stateful LLM Execution                                    │
│  For each constitution, process level-by-level:                     │
│  • Inject previous answers as context                               │
│  • Query LLM with chain-of-thought prompting                        │
│  • Parse responses: ANALYSIS: [...] FINAL: CODE|ANSWER              │
│  • Update state, proceed to next level                              │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 3: Validation                                                │
│  Compare AI outputs against human-coded ground truth                │
│  Strict vs. Relaxed scoring (96-99 codes as convention differences) │
└─────────────────────────────────────────────────────────────────────┘
```

## File Structure

```
├── 1_question_extraction.ipynb    # Parse codebook → structured JSON
├── 2_extract_dependencies.py      # Map conditional logic
├── 3_dependency_scheduler.py      # Topological sort (Kahn's algorithm)
├── 4_llm_with_reasoning.ipynb     # Stateful LLM inference
├── 5_validation.ipynb             # Evaluation framework
```

## File Descriptions

#### `1_question_extraction.ipynb`
Parses the raw codebook (`.docx`) into a structured JSON database. Handles:
- Extraction of question IDs, codes, and answer options
- Detection of multi-select vs. single-select questions
- Parsing of conditional phrases (e.g., "(Asked only if AMEND is answered 1)") into structured `depends_on` lists and evaluable `condition_expression` strings
- Cleaning of text artifacts (soft hyphens, irregular whitespace)
- Organization into thematic chunks via external config file

**Input**: `Questions.docx`, `question_chunks.yaml`  
**Output**: `organized_constitutional_questions.json`

#### `2_extract_dependencies.py`
Reads the organized JSON and extracts all conditional relationships into a dedicated dependency map. For each conditional question, records:
- Parent variable(s) it depends on
- Raw conditional text
- Normalized condition expression
- Any missing/broken dependency references

**Input**: `organized_constitutional_questions.json`  
**Output**: `question_dependencies_*.json`, `question_dependencies_*.csv`

#### `3_dependency_scheduler.py`
Builds a level-based processing plan using Kahn's algorithm for topological sorting. Questions are grouped into levels where:
- **Level 0**: Root questions (no dependencies)
- **Level 1+**: Questions whose dependencies are all satisfied by previous levels

Also detects cycles in the dependency graph (if any exist).

**Input**: `organized_constitutional_questions.json`, `question_dependencies_*.json`  
**Output**: `dependency_plan_levels_*.json` — a list of lists representing processing order

#### `4_llm_with_reasoning.ipynb`
The core inference engine. For each constitution:
1. Initializes an empty answer state
2. Iterates through levels in order
3. Builds prompts that include: constitutional text, questions at current level, and all previous answers as context
4. Queries the LLM with chain-of-thought instructions requiring `ANALYSIS:` and `FINAL:` format
5. Parses responses via regex, updates state, proceeds to next level
6. Exports results to JSON with full reasoning traces

Also includes post-processing functions to convert JSON outputs into Original, Dummy-coded, and Pivot CSV formats.

**Input**: `organized_constitutional_questions.json`, `dependency_plan_levels_*.json`, constitutions CSV, OpenAI API key  
**Output**: Per-constitution JSON files, aggregated CSVs

#### `5_validation.ipynb`
Compares LLM outputs against human-coded ground truth using a hybrid metrics framework:
- **Strict scoring**: Exact match required
- **Relaxed scoring**: Treats codes 96–99 as equivalent to 0, distinguishing substantive errors from coding convention differences
- **Hierarchical breakdown**: Separate metrics for Root, Conditional-Answer, and Conditional-Skip questions

Generates color-coded Excel reports (Green/Yellow/Red) sorted by dependency level for supervisor review.

**Input**: `subset_validation.csv` (ground truth), LLM output CSVs, `organized_constitutional_questions.json`, `dependency_plan_levels_*.json`  
**Output**: Console metrics summary, `Constitutional_Validation_Level_Sorted.xlsx`

## Current Benchmarks

| Category | Strict | Relaxed |
|----------|--------|---------|
| Root Questions | 71.27% | 74.18% |
| Conditional: Answer | 60.00% | 66.67% |
| Conditional: Skip | 51.58% | 92.63% |
| **Global** | **63.22%** | **73.01%** |

*Strict*: Exact match required  
*Relaxed*: Codes 96–99 (Other, Unable to Determine, Not Specified, Not Applicable) treated as equivalent to 0

## Expected Data Format

**Input**: Codebook (`.docx`), question config (`.yaml`), constitutions (`.csv`)  
**Output**: Per-constitution JSON with reasoning traces, plus CSV exports (Original, Dummy, Pivot)

### Codebook Format (`Questions.docx`)

Questions follow this structure, with conditional logic in parentheses:

```
v70. AMEND
Does the constitution provide for at least one procedure for amending 
the constitution?
1. Yes
2. No
98. Not Specified

v71. AMNDPROP (Select all that apply)
(Asked only if AMEND is answered 1)
Who can propose amendments to the constitution?
1. Head of State
2. Head of Government
3. Cabinet
4. First Chamber of the Legislature
5. Second Chamber of the Legislature
96. Other
97. Unable to Determine
98. Not Specified
99. Not Applicable

v76. AMNDAPPR (Select all that apply)
(Asked only if AMEND is answered 1)
Who approves amendments to the constitution?
1. Head of State
2. Head of Government
3. Cabinet
4. First Chamber of the Legislature
5. Second Chamber of the Legislature
6. Joint session of the Legislature
7. Referendum
96. Other
97. Unable to Determine
98. Not Specified
99. Not Applicable
```

Multi-select questions are expanded into binary dummy variables in the output (e.g., `AMNDAPPR_1`, `AMNDAPPR_2`, etc.).

### Question Chunks (`question_chunks.yaml`)

Groups questions into thematic categories for organized prompting:

```yaml
amendment_process:
  title: "Constitutional Amendment Procedures"
  codes: ["AMEND", "AMNDPROP", "AMNDAPPR", "AMNDAPCT"]
  keywords: ["amend", "amendment", "unamendable"]
  description: "Questions about constitutional amendment procedures"

executive_branch:
  title: "Executive Branch Structure and Powers"
  codes: ["EXECNUM", "HOSHOG", "HOSID"]
  keywords: ["head of state", "head of government", "president", "prime minister", "executive", "cabinet", "minister", "decree", "pardon"]
  description: "Executive leadership, cabinet, selection, powers, and accountability"

```

### Constitutions Input (`constitutions.csv`)

```csv
content,name,country,year
"We the People of the United States, in Order to form a more perfect Union...",United_States_1791.txt,United States,1791,
"The Constituent Assembly affirms the Portuguese people's decision...",Portugal_1976.txt,Portugal,1976
```

## Usage

```bash
# Execute in order:
1_question_extraction.ipynb   # Parse codebook
python 2_extract_dependencies.py
python 3_dependency_scheduler.py
4_llm_with_reasoning.ipynb    # Requires API key in "API Key.txt"
5_validation.ipynb
```

## Requirements

```
python >= 3.9
openai, pandas, numpy, scikit-learn, openpyxl, mammoth, pyyaml
```

## Contact

Ethan Carlson — eac263@cornell.edu
