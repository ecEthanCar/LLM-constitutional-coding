---
output:
  word_document: default
  html_document: default
  pdf_document: default
---
# Constitutional AI Coding Pipeline

**Researcher:** Ethan Carlson

**Supervisors:** Prof. Yun-chien Chang, Prof. Martin Wells, Tejas Ramdas

**Project Date:** December 2025

---

## 1. Executive Summary

This project automates the legal coding of global constitutions by leveraging Large Language Models (LLMs) to transform unstructured text into a machine-readable dataset. The system navigate the highly conditional nature of constitutional surveys, ensuring that data is extracted with legal rigor, hierarchical accuracy, and a clear audit trail for human verification.

## 2. System Architecture & Design Choices

### Level-Based Dependency Scheduling (Topological Sort)

Constitutional surveys are inherently nested. For example, questions regarding the proportion of votes needed for a constitutional amendment (`AMNDAPCT`) are only relevant if a procedure for amending exists (`AMEND`). To process these accurately, I developed a dependency-based scheduler using Kahn's algorithm for topological sorting. By processing questions in "Levels" rather than a flat list, the system ensures the model never encounters a "child" question before its "parent" prerequisite has been answered. This design specifically addresses supervisor concerns regarding accuracy in conditional categories.

### Stateful Context Injection

Because LLMs are typically "stateless" and treat prompts in isolation, I implemented a system to pass answers from previous levels back into the prompt for subsequent levels. As the system completes Level 0 (Root questions), it stores the answers in a "global answer context". When moving to Level 1, these previous answers are injected into the prompt as context. This allows the AI to determine if conditions—such as "Asked only if `AMEND` is answered 1"—are met before attempting to code the text.

### The Inference Engine & Prompt Structure

The system maintains a **Global Answer Context** (State) throughout processing. As each level completes, answers feed into the next prompt as "Previously Answered Questions".

#### Prompt Engineering & Format

The LLM receives a **Reasoning-First (Chain-of-Thought)** prompt designed for machine-parseable extraction:

* **System Role**: Defines the persona as an expert data entry assistant restricted exclusively to the provided text
* **Few-Shot Examples**: Includes specific single-select, multi-select, and "silence" (Not Specified) examples to calibrate LLM behavior
* **Output Format**: Forces a two-line structure for every variable:

```text
ANALYSIS: [One sentence citing specific Article/Section]
FINAL: [CODE]|[OPTION_NUMBER]
```

**Model Configuration**:

* Model: GPT-5.1 (with GPT-4o and GPT-4o-mini as lower token usage options)
* Temperature: 0 (for deterministic outputs)
* Seed: 123 (for reproducibility)

### "Reasoning First" Chain-of-Thought (CoT)

Purely numeric outputs are difficult for legal scholars to verify. To solve this, the prompt instructions explicitly demand a reasoning-first approach, requiring the LLM to provide a one-sentence analysis citing the specific article or section number before providing the final code. This design ensures the AI identifies evidence in the text, reduces "hallucinations," and provides the law team with a transparent audit trail.

---

## 3. Workflow Pipeline & File Functions

### Phase 1: Knowledge Base Construction

* **Question Extraction & Organization (`1_question_extraction.ipynb`)**: Parses the raw `Questions.docx` and `question_chunks.yaml` to create a structured JSON database, handling complex artifacts like soft hyphens and multi-line instructions.
* **Dependency Extraction (`2_extract_dependencies.py`)**: Analyzes question text for conditional phrases (e.g., "(Asked only if...)") and maps conditional questions to their parent variables to create a dependency map.
* **Dependency Scheduling (`3_dependency_scheduler.py`)**: Sorts the entire question set into levels (Level 0, 1, 2, etc.) using a directed acyclic graph (DAG) to facilitate sequential processing.

### Phase 2: AI Execution

* **LLM Processing with State Management (`4_llm_with_reasoning.ipynb`)**: This is the core engine that iterates through each constitution level-by-level. It builds prompts with previous answers as context and parses responses using the `FINAL: CODE|ANSWER` format.
* **Post-Processing**: A function within the notebook "flattens" the AI's reasoning and codes into standardized CSVs in Original, Dummy, and Pivot formats for analysis.

### Phase 3: Evaluation & Reporting

* **Validation & QA (`5_validation.ipynb`)**: Compares AI outputs against human "Truth" data using a Hybrid Unbiased Metrics framework to prevent accuracy inflation from correctly skipped irrelevant questions.

#### Hybrid Unbiased Metrics Framework

**Strict Match**: Requires exact numeric agreement between human coder and AI.

**Relaxed Match**: Treats codes 96–99 (Other, Unable to Determine, Not Specified, Not Applicable) as equivalent to 0 (No), distinguishing fundamental legal errors from coding convention differences.

**Current Benchmarks** (as of December 2025):

| Category | Accuracy (Strict) | Accuracy (Relaxed) |
|----------|------------------|-------------------|
| **Global Metrics** | 54.81% | 63.46% |
| **Root Questions** | 74.29% | 75.92% |
| **Conditional: Answer** | 50.37% | 55.01% |
| **Conditional: Skip** | 35.90% | 66.03% |

> **Note on Conditional: Skip**: The 66.03% Relaxed accuracy indicates that when the LLM is expected to skip a question (Code 99), it often provides a 90-series code (97 or 98) instead. This reflects the system's "Evidence Only" constraint, where the LLM prefers "Not Specified" over a logical "Not Applicable" skip.

The system generates color-coded Excel reports (Green/Yellow/Red) sorted by Level, allowing supervisors to perform horizontal review of AI performance across countries for the same legal concepts.

---

## 4. Technical Implementation Details

### Question Data Structure

The organized JSON database follows a structured format to support both thematic grouping and conditional logic:

```json
{
  "metadata": {
    "total_chunks": 10,
    "total_questions": 147,
    "chunk_summary": {
      ...
      "executive_branch": {
        "title": "Executive Branch Structure and Powers",
        "question_count": 41,
        "sample_codes": [
          "EXECNUM",
          "HOSHOG",
          "HOSID"
        ]
      },
      ...
    }
  }
},
{
  "chunks": {
    "executive_branch": {
      "title": "Executive Branch Structure and Powers",
      "description": "Executive leadership, cabinet, selection, powers",
      "questions": [
        {
          "id": "v121",
          "code": "HOGNAME",
          "question": "What name does the constitution assign the Head of Government?",
          "options": [
            {
              "number": "1",
              "text": "President",
              "code": null
            },
            {
              "number": "2",
              "text": "Prime Minister",
              "code": null
            },
            {
              "number": "3",
              "text": "Chancellor",
              "code": null
            },
            {
              "number": "4",
              "text": "Premier",
              "code": null
            },
            {
              "number": "5",
              "text": "Chief Minister",
              "code": null
            },
            {
              "number": "96",
              "text": "other, please specify in the comments section",
              "code": null
            },
            {
              "number": "97",
              "text": "Unable to Determine",
              "code": null
            },
            {
              "number": "98",
              "text": "Not Specified",
              "code": null
            },
            {
              "number": "99",
              "text": "Not Applicable",
              "code": null
            }
          ],
          "conditional": {
            "raw": "(Asked only if EXECNUM is answered 3, or if HOSHOG is answered 2)",
            "depends_on": [
              "EXECNUM",
              "HOSHOG"
            ],
            "condition_expression": "EXECNUM == 3 or HOSHOG == 2"
          },
          "instructions": "In Ireland, the Head of Government is called the Taoiseach.  Please respond other and put Taoiseach in the comments section for Ireland.  IF THE CONSTITUTION MENTIONS A PRIME MINISTER, the Prime Minister is ALWAYS the Head of Government, no matter how strong or weak this office may appear.",
          "multi_select": false,
          "category": "executive_branch",
          "order_index": 13
        }
      ]
    }
  }
}

```

### Dependency Map & Topological Sort Output

The dependency extraction identifies child-parent relationships, which the scheduler then organizes into ordered levels for the AI to follow:

```json
// Topological Sort Plan
[
  ["HOSHOG", "AMEND", "EXECNUM", "FEDERAL"], // Level 0: Root questions
  ["HOSNAME", "HOGNAME", "FEDSEP"],      // Level 1: Depend only on Level 0
  ["HOSTERM", "HOGTERM"],                // Level 2: Depend on Level 0-1
  ...
]

```

### Replication Pipeline

To replicate results, execute scripts in this sequence:

1. **`1_question_extraction.ipynb`**: Parse raw codebook into structured JSON
2. **`2_extract_dependencies.py`**: Map conditional logic within codebook
3. **`3_dependency_scheduler.py`**: Generate level-based processing plan
4. **`4_llm_with_reasoning.ipynb`**: Execute stateful inference and generate JSON outputs
5. **`5_validation.ipynb`**: Compare AI output against validation subset and generate Level_Sorted_Comparison report

### Prompt Structure & State Management

Each LLM prompt is dynamically constructed to include constitutional text, previous state, and strict output formatting:

```python
# State Management Logic
answer_state = {}  # code -> answer mapping

for level in dependency_plan:
    # Build context from all previous levels
    context = {k: v for k, v in answer_state.items()}
    
    # Generate prompts with context
    prompts = create_prompts_with_context(level, context)
    
    # Query LLM and parse answer using regex
    # Format: ANALYSIS: [reasoning] FINAL: CODE|ANSWER
    new_answers = process_level(prompts)
    
    # Update state for next level
    answer_state.update(new_answers)

```

---

## 5. Addressing Feedback

* **Order of Processing**: By sorting validation reports by "Level," supervisors can confirm prerequisites are processed before dependents.
* **Dummification**: Multi-select variables are correctly expanded into individual binary indicators (0/1) in the Dummy format CSV, ensuring the data is ready for statistical analysis.
* **Instructional Clarity**: Variables like `HOSTERM` and `HOSNAME` were updated to remove legacy options (1/99) and utilize precise open-ended instructions as requested.
* **Validation Transparency**: The framework now distinguishes between fundamental errors and coding convention differences using Strict vs. Relaxed metrics.

---

*Last Updated: December 2025*
