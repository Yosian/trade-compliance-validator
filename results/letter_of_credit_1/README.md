# 📄 Document Report – `test-letter-of-credit_1.png`

This file represents another realistic example of a **Letter of Credit (Irrevocable, Confirmed)** and was used to validate the extraction reliability of the **Trade Document Validator (TDV)** pipeline across variations in layout and content depth.

---

## 🔍 Document Summary

| Field              | Value |
|--------------------|-------|
| **Document Type**  | Letter of Credit |
| **Classification Confidence** | 96% |
| **Source**         | Synthetic scan (PNG) |
| **Document Quality** | Excellent, machine-readable layout |
| **Image Dimensions** | 857 × 768 px |

---

## 🧠 Classification Results

| Metric        | Value |
|---------------|-------|
| **Predicted Type** | `LetterOfCredit` |
| **LLM Confidence Score** | 96% |
| **Prompt Used** | See [`../prompts/classification_prompt_template.txt`](../prompts/classification_prompt_template.txt) |

**Notes:**  
Classification was confidently accurate. The structured headings, field labels, and terminology ("Irrevocable, Confirmed", "Advising Bank", "Place of Expiry") helped reinforce this result.

---

## 🧾 Extraction Results

```json
{
  "issuing_bank": "Bank of London",
  "advising_bank": "Deutsche Bank AG",
  "beneficiary": "Jinzhou Electronics Co., Ltd.",
  "applicant": "TechNova Imports Ltd.",
  "letter_of_credit_number": "LC20250806-001",
  "date_of_issue": "August 6, 2025",
  "expiry_date": "November 6, 2025",
  "place_of_expiry": "Frankfurt, Germany",
  "amount": "EUR 150,000.00",
  "tolerance": "+/- 5%",
  "description_of_goods": "50,000 units of Smart LED Driver Modules",
  "shipment_details": {
    "port_of_loading": "Dalian Port, China",
    "port_of_discharge": "Hamburg Port, Germany",
    "latest_shipment_date": "September 30, 2025",
    "partial_shipment": "Not Allowed",
    "transshipment": "Allowed"
  }
}
```

| Extraction Accuracy | ✅ Very High |
|---------------------|-------------|
| Source of Prompt    | `extraction_prompt_template.txt` |
| Output Format       | JSON |
| Ground Truth Match  | Full match across all categories |

---

## 📚 DynamoDB Context (Summarized)

From the audit logs:

- **Doc ID:** `test-letter-of-credit_1`
- **Classification Time:** 2.9s
- **Model Used:** `claude-instant-v1`
- **Prompt Chain:** `classification → extraction → transformation`
- **Audit Trail Status:** Successful with zero retries
- **Stored In:** `tdv/test-letter-of-credit_1.png`

---

## 🔍 Observations

- This format mimics a structured business template and improves Claude’s ability to extract nested fields (e.g., shipment block)
- LLM correctly identified and parsed fields like tolerance and expiry location
- Good example of a “complete document” for training or benchmarking

---

## ✅ Next Actions

- Compare this against other LCs for layout sensitivity
- Validate consistency in multiline field extraction (like goods description)
- Use in batch inference test

---
