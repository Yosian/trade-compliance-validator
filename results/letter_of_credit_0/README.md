# 📄 Document Report – `test-letter-of-credit.png`

This file represents a real-world example of a **Letter of Credit** and was used to test the full document pipeline of the **Trade Document Validator (TDV)**.

---

## 🔍 Document Summary

| Field              | Value |
|--------------------|-------|
| **Document Type**  | Letter of Credit |
| **Classification Confidence** | 95% |
| **Source**         | Uploaded scan (PNG) |
| **Document Quality** | High resolution, OCR-parseable |
| **Image Dimensions** | 839 × 768 px |

---

## 🧠 Classification Results

| Metric        | Value |
|---------------|-------|
| **Predicted Type** | `LetterOfCredit` |
| **LLM Confidence Score** | 95% |
| **Prompt Used** | See [`../prompts/classification_prompt_template.txt`](../prompts/classification_prompt_template.txt) |

**Notes:**  
Classification was correct. Model showed high confidence. Heuristics matched keyword patterns such as "Irrevocable Documentary Letter of Credit", "Applicant", "Beneficiary", and "Governing Rules".

---

## 🧾 Extraction Results

Extracted fields from Claude (via Bedrock):

```json
{
  "issuing_bank": "Global Trade Bank Ltd.",
  "letter_of_credit_no": "GTB-LOC-2025-0456",
  "date_of_issue": "July 15, 2025",
  "beneficiary": "Ocean Exports Ltd.",
  "applicant": "Euro-Import Holdings",
  "amount": "USD 350,000",
  "expiry_date": "October 15, 2025",
  "availability": "At sight",
  "governing_rules": "UCP 600, ICC Publication No. 600",
  "partial_drawings": "Allowed",
  "transferable": "No"
}
```

| Extraction Accuracy | ✅ High |
|---------------------|--------|
| Source of Prompt    | `extraction_prompt_template.txt` |
| Output Format       | JSON |
| Ground Truth Match  | All fields matched expectation |

---

## 📎 Document Requirements (Extracted)

1. Original of this Letter of Credit  
2. Commercial Invoice (2 originals)  
3. Ocean Bill of Lading  
4. Packing List  
5. Insurance Policy  
6. Certificate of Origin  

**Notes:**  
Claude correctly identified the checklist as an embedded ordered list and extracted items verbatim.

---

## 📚 DynamoDB Context (Summarized)

From `tdv-dev-documents.csv` and `tdv-dev-audit-trail.csv`, this document was:

- Uploaded as part of test run `batch_0723_testdoc_001`
- Assigned a `classification_result` of `LetterOfCredit`
- Extraction was completed in 3.2s using `claude-instant-v1`
- Audit log shows single retry due to timeout on first call

---

## 📌 Observations

- Claude handled field formatting and bullet structures well  
- Extraction was resilient to visual formatting differences  
- No manual overrides required  
- Document stored in S3 under: `tdv/test-letter-of-credit.png`  

---

## ✅ Next Actions

- Include this example in batch summary comparison
- Add link to this doc in results dashboard
- Use prompt caching for faster reruns

---
