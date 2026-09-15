# PaperAI — Product & Technical Specification

## 1. Product Overview

PaperAI is an AI-powered academic paper reading, translation, and question-answering platform.

The product is designed for students, researchers, engineers, and professionals who frequently read English academic papers and want to understand them more efficiently.

The core workflow is:

```text
Upload PDF
→ Parse paper structure
→ Generate Traditional Chinese translation
→ Read English and Chinese side by side
→ Ask AI questions about the paper
→ Jump directly to cited source paragraphs
→ Highlight and take notes
```

PaperAI is not simply a PDF translation tool.

It should function as an:

```text
AI Academic Reading Workspace
```

The primary product goal is:

> Help users read, understand, analyze, and learn from academic papers faster.

---

# 2. Target Users

Primary users:

- Graduate students
- Undergraduate students
- Researchers
- Engineers
- R&D professionals
- Academic reviewers
- People reading English academic papers

Common use cases:

- Reading unfamiliar research fields
- Understanding paper methodology
- Understanding mathematical models
- Preparing paper presentations
- Writing literature reviews
- Comparing related work
- Reviewing experiments and results
- Learning technical terminology

---

# 3. Core User Experience

The primary user flow:

```text
1. User uploads a PDF paper
2. System parses the document
3. System detects paper structure
4. System translates paragraphs into Traditional Chinese
5. User reads English and Chinese side by side
6. User selects difficult content
7. User asks AI to explain it
8. AI answers using the current paper as context
9. AI provides source citations
10. User clicks citation
11. Reader jumps to the corresponding paragraph
```

---

# 4. Main Interface

The main workspace uses a three-column layout.

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│ PaperAI        Paper Title       Search     Reading Mode     Export     User │
├──────────────┬──────────────────────────────────────────────┬─────────────────┤
│              │                                              │                 │
│ Paper        │                Paper Reader                  │ AI Assistant    │
│ Outline      │                                              │                 │
│              │ ┌────────────────────┬────────────────────┐ │                 │
│ Abstract     │ │ English            │ 中文翻譯            │ │ Ask this paper  │
│ Introduction │ │                    │                    │ │                 │
│ Related Work │ │ Original paragraph │ 對應中文翻譯        │ │                 │
│ Method       │ │                    │                    │ │                 │
│ Experiment   │ │                    │                    │ │                 │
│ Results      │ │                    │                    │ │                 │
│ Conclusion   │ │                    │                    │ │                 │
│ References   │ │                    │                    │ │                 │
│              │ └────────────────────┴────────────────────┘ │                 │
│ Figures      │                                              │                 │
│ Tables       │                                              │ [Ask AI...]     │
│ Notes        │                                              │                 │
└──────────────┴──────────────────────────────────────────────┴─────────────────┘
```

---

# 5. Technology Stack

## Frontend

Use:

```text
Next.js
React
TypeScript
Tailwind CSS
shadcn/ui
```

Requirements:

- Responsive design
- Desktop-first
- Dark mode support
- Reusable components
- Strong TypeScript typing

---

## Backend

Use:

```text
Python
FastAPI
```

Responsibilities:

- PDF processing
- Text extraction
- Document parsing
- Translation
- Embeddings
- RAG
- AI chat
- Search
- Summary generation

---

## Database

Use:

```text
PostgreSQL
```

Vector search:

```text
pgvector
```

---

## File Storage

Development:

```text
Local storage
```

Production:

```text
S3-compatible object storage
```

Possible providers:

- AWS S3
- Cloudflare R2
- Supabase Storage

Storage implementation should use an abstraction layer.

---

# 6. PDF Upload

Users must be able to:

- Drag and drop PDF
- Select PDF from computer

Initial supported format:

```text
.pdf
```

Upload screen:

```text
Drop your research paper here

or

Choose PDF
```

Show basic document information after upload:

- Filename
- File size
- Number of pages

---

# 7. PDF Processing Pipeline

After upload:

```text
PDF Upload
    ↓
Text Extraction
    ↓
Layout Detection
    ↓
Document Structure Detection
    ↓
Paragraph Segmentation
    ↓
Figure / Table Detection
    ↓
Translation
    ↓
Embedding Generation
    ↓
Vector Database
    ↓
Ready
```

Display progress to the user.

Example:

```text
Uploading PDF                 ✓
Extracting text               ✓
Detecting document structure  ✓
Parsing paragraphs            ✓
Translating paper             68%
Creating AI index
```

---

# 8. Document Structure Detection

The system should attempt to detect:

```text
Title
Authors
Affiliations
Abstract
Keywords
Introduction
Related Work
Background
Methodology
System Model
Problem Formulation
Algorithm
Experiment
Results
Discussion
Conclusion
Acknowledgements
References
```

Do not assume every paper uses the same section names.

Use heading detection and semantic classification.

---

# 9. Document Data Structure

Suggested hierarchy:

```text
Document
 ├── Section
 │     ├── Paragraph
 │     ├── Paragraph
 │     ├── Figure
 │     └── Table
 │
 ├── Section
 │     ├── Paragraph
 │     └── Paragraph
```

---

# 10. Document Model

Example:

```typescript
interface Document {
  id: string
  title: string
  authors: string[]
  fileName: string
  pageCount: number
  status: DocumentStatus
  createdAt: string
}
```

---

# 11. Section Model

```typescript
interface Section {
  id: string
  documentId: string
  title: string
  sectionNumber?: string
  order: number
  startPage: number
  endPage?: number
}
```

---

# 12. Paragraph Model

Every paragraph should have a stable identifier.

Example:

```typescript
interface Paragraph {
  id: string
  documentId: string
  sectionId: string

  pageNumber: number

  originalText: string
  translatedText?: string

  order: number

  boundingBox?: {
    x: number
    y: number
    width: number
    height: number
  }

  embeddingId?: string
}
```

Example ID:

```text
paragraph_0001
paragraph_0002
paragraph_0003
```

---

# 13. Bilingual Reading Mode

Support three reading modes:

```text
English
中文
中英對照
```

Default:

```text
中英對照
```

Bilingual mode layout:

```text
English                       中文

Edge computing allows...      邊緣運算能夠...

The proposed framework...     本研究提出的框架...
```

---

# 14. Paragraph Synchronization

English and Chinese paragraphs must be linked.

Example:

```text
paragraph_015

English:
The proposed framework uses reinforcement learning...

Chinese:
所提出的框架使用強化學習...
```

When hovering over either paragraph:

Highlight both paragraphs.

Example:

```text
English paragraph
██████████████████

Chinese paragraph
██████████████████
```

---

# 15. Scroll Synchronization

When a user scrolls English content:

The Chinese translation should remain approximately aligned.

Avoid strict pixel-level synchronization.

Synchronization should be based on paragraph position.

---

# 16. Translation System

Translation language:

```text
English
→
Traditional Chinese
```

Translation goals:

- Accurate
- Academic
- Natural
- Consistent terminology
- Preserve original meaning

Avoid excessive rewriting.

---

# 17. Translation Rules

Do not translate:

- Equations
- Mathematical symbols
- Variable names
- Model names
- Algorithm names
- Dataset names
- Citations
- URLs
- DOI
- Code

Example:

```text
Deep Q-Network (DQN)
```

Can be translated as:

```text
Deep Q-Network（DQN，深度 Q 網路）
```

But keep:

```text
DQN
```

unchanged.

---

# 18. Terminology Memory

Create a terminology dictionary.

Example:

```json
{
  "Mobile Edge Computing": "行動邊緣運算",
  "Reinforcement Learning": "強化學習",
  "Markov Decision Process": "馬可夫決策過程",
  "Multi-Agent Reinforcement Learning": "多代理強化學習"
}
```

The same terminology should use the same translation across the entire paper.

Future versions should allow user overrides.

---

# 19. Formula Handling

Mathematical formulas should remain unchanged.

Example:

```text
R(s, a) = αT - βE
```

should not be translated.

Support formula rendering using:

```text
KaTeX
```

or:

```text
MathJax
```

---

# 20. Figures

Figures should remain near their original context.

Each figure should store:

```text
figure_id
page_number
image
caption
section_id
```

AI should be able to understand figure captions.

Future versions may add visual understanding.

---

# 21. Tables

Tables should preserve:

- Rows
- Columns
- Caption
- Table number

Table contents should ideally be parsed into structured data.

---

# 22. AI Assistant

The right panel contains the AI assistant.

Panel width:

```text
350px – 420px
```

The AI assistant should answer questions about the currently opened paper.

---

# 23. AI Context Modes

Support:

```text
Entire Paper
Current Section
Current Page
Selected Text
```

Example UI:

```text
Context

[ Current Section ▼ ]

Section 4
Experimental Results
```

---

# 24. AI Chat Example

User:

```text
這篇論文主要解決什麼問題？
```

AI:

```text
這篇論文主要研究在 Mobile Edge Computing 環境中，
如何同時最佳化計算卸載、延遲與能源消耗。

作者將這個問題建模為 Markov Decision Process，
並使用 Deep Reinforcement Learning 進行求解。

來源：
Section 3 — Problem Formulation
Page 5
```

---

# 25. RAG Architecture

Use Retrieval-Augmented Generation.

Architecture:

```text
Paper
 ↓
Paragraph Segmentation
 ↓
Embedding
 ↓
pgvector
 ↓
Semantic Retrieval
 ↓
Relevant Chunks
 ↓
LLM
 ↓
Answer
```

Do not send the entire paper for every question.

---

# 26. Chunk Strategy

Prefer paragraph-based chunks.

Example:

```text
Chunk 1
Section 3.1
Paragraph 45–47

Chunk 2
Section 3.2
Paragraph 48–51
```

Allow slight overlap between chunks.

---

# 27. Chunk Metadata

Store:

```json
{
  "document_id": "...",
  "section_id": "...",
  "section_title": "...",
  "page_number": 7,
  "paragraph_ids": [
    "paragraph_45",
    "paragraph_46"
  ]
}
```

---

# 28. AI Citation

Every factual AI answer about the paper should contain citations.

Example:

```text
作者使用 PPO 作為主要的強化學習演算法。

Source:
Page 8
Section 4.1
Paragraph 72
```

Citation should be clickable.

---

# 29. Citation Navigation

When clicking citation:

```text
1. Scroll reader to source paragraph
2. Highlight paragraph
3. Keep highlight visible for several seconds
```

Example animation:

```text
normal
↓
yellow highlight
↓
fade
```

---

# 30. Hallucination Prevention

The AI must never fabricate paper content.

If evidence cannot be found:

Respond:

```text
目前在這篇論文中找不到足夠資訊回答這個問題。
```

AI should clearly distinguish between:

```text
Paper statement
AI interpretation
General knowledge
```

---

# 31. Selected Text Interaction

When the user selects text:

Display floating toolbar.

```text
┌──────────────────────────────────────────┐
│ Explain | Translate | Summary | Ask AI │
└──────────────────────────────────────────┘
```

Additional option:

```text
Add Note
```

---

# 32. Explain Selected Text

Example selected content:

```text
The optimization problem is formulated as a Markov Decision Process.
```

AI should explain:

```text
這句話代表作者將原本的最佳化問題重新描述成一個
Markov Decision Process（MDP）。

在 MDP 中通常會包含：

State
目前系統狀態

Action
系統可以採取的決策

Reward
希望 AI 最大化的目標

Transition
執行 Action 後系統如何改變
```

AI should preferably connect the explanation to the actual paper.

---

# 33. Quick AI Actions

Display suggested prompts.

Examples:

```text
Summarize this paper

這篇論文解決什麼問題？

主要 Contribution 是什麼？

解釋 Methodology

解釋 System Model

解釋 MDP

State 是什麼？

Action 是什麼？

Reward Function 是什麼？

使用哪些 Baseline？

Experimental Setup 是什麼？

結果證明了什麼？

有哪些 Limitations？

幫我整理成論文簡報
```

---

# 34. Explanation Levels

Provide explanation modes:

```text
Beginner
Undergraduate
Graduate Student
Researcher
```

---

# 35. Beginner Mode

Focus on:

- Intuitive explanations
- Simple language
- Examples
- Analogies

Avoid unnecessary mathematical details.

---

# 36. Graduate Student Mode

Explain:

- Research motivation
- Problem formulation
- Model architecture
- Algorithms
- Experimental setup
- Results

Include necessary formulas.

---

# 37. Researcher Mode

Focus on:

- Assumptions
- Mathematical formulation
- Model limitations
- Experimental validity
- Baseline fairness
- Generalization
- Ablation studies
- Future research directions

---

# 38. Paper Summary

Generate a structured summary.

Sections:

```text
Research Problem

Motivation

Main Contributions

Methodology

System Model

Datasets

Experimental Setup

Baselines

Evaluation Metrics

Results

Limitations

Future Work

Key Takeaways
```

---

# 39. Summary Length

Support:

```text
One Sentence

Short

Detailed
```

---

# 40. Notes

Users can create notes.

Note model:

```typescript
interface Note {
  id: string
  documentId: string
  paragraphId: string
  selectedText?: string
  content: string
  createdAt: string
}
```

---

# 41. Highlights

Users can highlight text.

Store:

```text
document_id
paragraph_id
selected_text
start_offset
end_offset
```

---

# 42. Search

Support two search modes.

## Exact Search

Example:

```text
reward function
```

Search raw document text.

---

## Semantic Search

Example:

```text
作者在哪裡說明如何設計 reward？
```

Use embeddings.

Return:

```text
Section
Page
Paragraph
Preview
```

---

# 43. Paper Metadata

Detect:

```text
Title
Authors
Affiliations
Journal
Conference
Year
DOI
Keywords
```

Allow users to manually edit metadata if detection fails.

---

# 44. Header

Header layout:

```text
PaperAI

Paper Title

Search

Reading Mode

Translation

Export

Settings

User
```

---

# 45. Sidebar

Sidebar sections:

```text
Paper

Abstract
Introduction
Related Work
Methodology
Experiments
Results
Discussion
Conclusion
References

──────────

Figures

Tables

Notes
```

Sidebar should be collapsible.

---

# 46. AI Panel

Suggested structure:

```text
AI Assistant

Context:
Current Section

──────────────

Chat messages

──────────────

Quick Actions

──────────────

Ask this paper...

[ Send ]
```

---

# 47. Visual Design

Style:

```text
Minimal
Professional
Academic
Modern
Premium
```

Design inspiration:

```text
Linear
Notion
ChatGPT
Readwise Reader
Arc Browser
```

Avoid:

- Excessive gradients
- Excessive shadows
- Large rounded cards everywhere
- Bright saturated colors

---

# 48. Typography

UI:

```text
Modern sans-serif
```

Paper text:

```text
Readable serif font
```

Prioritize long-form reading comfort.

---

# 49. Theme

Support:

```text
Light
Dark
System
```

---

# 50. Responsive Behavior

Primary target:

```text
Desktop
```

Tablet:

AI panel can collapse.

Mobile:

Use tabs:

```text
Paper
Translation
AI
```

---

# 51. Backend API

Recommended endpoints.

Upload:

```http
POST /api/documents/upload
```

Document:

```http
GET /api/documents/{document_id}
```

Sections:

```http
GET /api/documents/{document_id}/sections
```

Paragraphs:

```http
GET /api/documents/{document_id}/paragraphs
```

Translation:

```http
POST /api/documents/{document_id}/translate
```

---

# 52. Chat API

```http
POST /api/documents/{document_id}/chat
```

Request:

```json
{
  "message": "What is the reward function?",
  "context": "entire_document"
}
```

Response:

```json
{
  "answer": "...",
  "citations": [
    {
      "page": 7,
      "section": "Problem Formulation",
      "paragraph_id": "paragraph_0048"
    }
  ]
}
```

---

# 53. Search API

```http
POST /api/documents/{document_id}/search
```

Request:

```json
{
  "query": "reward function",
  "type": "semantic"
}
```

---

# 54. Notes API

Create:

```http
POST /api/documents/{document_id}/notes
```

Read:

```http
GET /api/documents/{document_id}/notes
```

Delete:

```http
DELETE /api/notes/{note_id}
```

---

# 55. Summary API

```http
GET /api/documents/{document_id}/summary
```

Optional:

```http
POST /api/documents/{document_id}/summary
```

for regeneration.

---

# 56. Suggested Database Tables

```text
users

documents

document_sections

document_paragraphs

document_figures

document_tables

document_embeddings

translations

terminology

chat_sessions

chat_messages

notes

highlights
```

---

# 57. AI Provider Abstraction

Do not tightly couple the system to one AI provider.

Create:

```typescript
interface LLMProvider {
  chat(): Promise<LLMResponse>
}
```

Possible providers:

```text
OpenAI
Anthropic
Google Gemini
Local Models
```

Initial implementation:

```text
OpenAI
```

---

# 58. Embedding Provider Abstraction

Create:

```text
EmbeddingProvider
```

Initial implementation:

```text
OpenAI Embeddings
```

---

# 59. Translation Provider Abstraction

Create:

```text
TranslationProvider
```

Possible implementations:

```text
OpenAI
DeepL
Gemini
Local LLM
```

Initial implementation may use OpenAI.

---

# 60. Suggested Project Structure

```text
paper-ai/

├── frontend/
│
│   ├── app/
│   ├── components/
│   │
│   │   ├── paper-reader/
│   │   ├── paper-sidebar/
│   │   ├── ai-chat/
│   │   ├── translation/
│   │   ├── notes/
│   │   ├── search/
│   │   └── ui/
│   │
│   ├── hooks/
│   ├── lib/
│   ├── services/
│   └── types/
│
├── backend/
│
│   ├── app/
│   │
│   ├── api/
│   ├── models/
│   ├── schemas/
│   │
│   ├── services/
│   │   ├── pdf/
│   │   ├── parsing/
│   │   ├── translation/
│   │   ├── embeddings/
│   │   ├── rag/
│   │   ├── chat/
│   │   └── search/
│   │
│   └── database/
│
├── docs/
│
├── SPEC.md
│
└── README.md
```

---

# 61. Development Phases

## Phase 1 — UI Prototype

Implement:

```text
Upload page

Main layout

Sidebar

Bilingual reader

AI chat panel

Mock paper data
```

Do not connect AI initially.

---

# 62. Phase 2 — PDF Reader

Implement:

```text
PDF upload

PDF.js

Text extraction

Page rendering
```

---

# 63. Phase 3 — Document Parsing

Implement:

```text
Heading detection

Section extraction

Paragraph extraction

Paragraph IDs

Page mapping
```

---

# 64. Phase 4 — Translation

Implement:

```text
Paragraph translation

Translation caching

Terminology consistency
```

---

# 65. Phase 5 — RAG

Implement:

```text
Embeddings

pgvector

Semantic retrieval

AI answers

Citations
```

---

# 66. Phase 6 — AI Interaction

Implement:

```text
Selected text

Explain

Summarize

Ask AI

Citation navigation
```

---

# 67. Phase 7 — Research Workspace

Implement:

```text
Notes

Highlights

Search

Paper summaries

Chat sessions
```

---

# 68. Phase 8 — Production

Implement:

```text
Authentication

Cloud storage

Usage limits

Error handling

Monitoring

Rate limiting

Security
```

---

# 69. MVP Scope

The first usable MVP must support:

```text
1. Upload PDF

2. Parse PDF text

3. Detect basic sections

4. Separate paragraphs

5. Translate English paragraphs into Traditional Chinese

6. Display English / Chinese side by side

7. Synchronize paragraph highlighting

8. Ask questions about the paper

9. Use RAG for retrieval

10. Display citations

11. Click citation to jump to source

12. Provide polished desktop UI
```

Do NOT over-engineer features outside this list before the MVP works.

---

# 70. MVP Success Criteria

The MVP is considered successful when a user can:

```text
Upload an English academic paper

Read English and Traditional Chinese side by side

Ask:
"What problem does this paper solve?"

Receive an accurate answer based on the paper

See the source page and section

Click the citation

Jump directly to the relevant paragraph
```

---

# 71. AI System Prompt

Suggested AI system prompt:

```text
You are PaperAI, an academic research assistant.

Your primary task is to help the user understand the currently uploaded academic paper.

Always prioritize information contained in the paper.

When answering:

1. Answer the user's question directly.

2. Explain difficult concepts clearly.

3. Use the terminology used by the paper.

4. Cite relevant sections, pages, and paragraphs.

5. Never fabricate experimental results.

6. Never fabricate citations.

7. Clearly state when the paper does not provide enough information.

8. Distinguish between:
   - information explicitly stated in the paper
   - interpretation
   - general background knowledge

If mathematical formulas appear, explain their meaning rather than simply repeating them.

Unless the user requests otherwise, answer in Traditional Chinese.
```

---

# 72. Translation Prompt

```text
You are an expert academic translator.

Translate the provided English academic paper paragraph into Traditional Chinese.

Requirements:

1. Preserve the original technical meaning.

2. Use formal academic Traditional Chinese.

3. Do not unnecessarily rewrite the author's argument.

4. Keep technical terminology consistent.

5. Preserve citations.

6. Preserve equations.

7. Preserve variable names.

8. Preserve model names.

9. Preserve dataset names.

10. Preserve abbreviations.

For important terminology, the first appearance may use:

English Term（中文翻譯）

Example:

Markov Decision Process（馬可夫決策過程）

Later occurrences may use the Chinese translation or abbreviation where appropriate.

Return only the translated paragraph.
```

---

# 73. RAG Prompt

```text
You are answering a question about an academic paper.

Use ONLY the provided retrieved paper context for factual claims about the paper.

If the retrieved context does not contain enough information, say that the paper does not provide enough information.

Do not invent:

- methods
- metrics
- results
- datasets
- experimental settings
- citations

Answer in Traditional Chinese unless requested otherwise.

At the end of relevant statements, provide source citations using the supplied metadata.

Example:

[Page 7 · Section 4.2 · Paragraph 73]
```

---

# 74. Product Principles

All future product decisions should follow these principles.

## Principle 1

Reading comes first.

AI features should enhance the paper reading experience rather than replace it.

## Principle 2

Source traceability is essential.

Every important AI statement should be traceable to the original paper.

## Principle 3

Do not hide the original text.

Users should always be able to compare translation with the English source.

## Principle 4

Academic accuracy is more important than fluent rewriting.

## Principle 5

Reduce cognitive load.

Users should be able to move naturally between:

```text
Read
↓
Translate
↓
Understand
↓
Ask
↓
Verify
↓
Take Notes
```

---

# 75. Development Instruction for AI Coding Agent

When implementing this project:

Do not attempt to build the entire system in one step.

Start with a functional MVP.

Development order:

```text
1. Create frontend application

2. Create main three-column workspace

3. Build upload screen

4. Build mock bilingual reader

5. Build AI chat UI

6. Build FastAPI backend

7. Implement PDF upload

8. Implement PDF text extraction

9. Implement section and paragraph parsing

10. Connect translation API

11. Add PostgreSQL

12. Add pgvector

13. Implement embeddings

14. Implement RAG chat

15. Implement citations

16. Implement citation navigation

17. Add notes and highlights
```

After each major step:

```text
Run the application

Fix build errors

Fix TypeScript errors

Check frontend usability

Check backend endpoints

Then continue
```

Prefer working code over excessive abstraction.

Keep the architecture modular so functionality can be improved later.

---

# 76. Final Product Vision

PaperAI should eventually become a complete AI research reading environment.

The long-term workflow:

```text
Discover Paper
        ↓
Upload
        ↓
Translate
        ↓
Read
        ↓
Ask AI
        ↓
Understand Method
        ↓
Analyze Results
        ↓
Take Notes
        ↓
Compare Papers
        ↓
Generate Literature Review
        ↓
Generate Presentation
```

The first priority remains:

```text
Excellent bilingual paper reading
+
Reliable document-grounded AI Q&A
```