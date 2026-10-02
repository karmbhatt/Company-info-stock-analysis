# Company-info-stock-analysis
Starting date : 2/10/2026

definetion: This project aims to analyze stock market data of various companies to provide insights into their financial performance, trends, and potential investment opportunities. The analysis will include historical stock prices, financial statements, and key performance indicators (KPIs) to help investors make informed decisions.



## System Architecture

```text
                         USER
                           │
                           ▼
                        FastAPI
                           │
                           ▼
                    Research Agent
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         Stock Tool    Search Tool    RAG Tool
              │            │            │
              ▼            ▼            ▼
       Market Data API   News Sources   TCS Reports
              │            │            │
              └────────────┼────────────┘
                           ▼
                       Evidence
                           │
                           ▼
                          LLM
                           │
                           ▼
              Structured Answer + Sources
```

### Architecture Components

- **User** — Asks questions about TCS, its stock, financial performance, news, industry developments, and other relevant information.
- **FastAPI** — Acts as the backend API layer and handles communication between the user interface and the research system.
- **Research Agent** — Understands the user's question, determines what information is required, and selects the appropriate tools.
- **Stock Tool** — Retrieves historical and live market information through the **Market Data API**.
- **Search Tool** — Searches relevant and recent news and other external sources.
- **RAG Tool** — Retrieves relevant information from TCS annual reports, investor presentations, filings, and other company documents.
- **Market Data API** — Provides structured historical and live stock-market data to the AI system.
- **Evidence** — Combines information retrieved from different sources before the final response is generated.
- **LLM** — Analyzes and synthesizes the retrieved evidence rather than being treated as the primary source of truth.
- **Structured Answer + Sources** — Produces a consistent response containing the answer, supporting information, and source references.