# 📊 TDV Document Comparison Summary – Corrected

This summary compares the classification and extraction performance across four representative documents evaluated by the **Trade Document Validator (TDV)** pipeline. This version includes the corrected confidence values and notes from the DynamoDB audit.

---

## 🔁 At a Glance

| Document File                       | Predicted Type    | Classification Confidence | Extraction Confidence | Extraction Prompt Type     | Comments |
|------------------------------------|-------------------|----------------------------|------------------------|-----------------------------|----------|
| `test-letter-of-credit.png`        | LetterOfCredit    | 95%                        | ✅ High (custom)       | Tailored for LetterOfCredit | Complete and accurate |
| `test-letter-of-credit_1.png`      | LetterOfCredit    | 96%                        | ✅ High (custom)       | Tailored for LetterOfCredit | All fields matched |
| `test-commercial-invoice.png`      | CommercialInvoice | 93%                        | ❌ Low (generic)       | Fallback generic extraction | Line-items and totals missing |
| `test-ambiguous-financial-doc.png` | OTHER             | **90%**                    | ❌ Low (0.3)           | Fallback generic extraction | Response was invalid JSON |

---

## 🔍 Key Corrections

- The ambiguous memo was **correctly classified as `OTHER` with 90% confidence**, not as low-confidence "Unknown."
- The system **attempted extraction**, but the LLM returned malformed JSON with **low confidence (0.3)**.
- This validates that fallback extraction logic needs improvement for confidently labeled `OTHER` cases.

---

## 🧠 Insights

- Tailored prompts for known types like **Letters of Credit** produce excellent results.
- **Generic extraction** is insufficient for structured documents like invoices or undefined types (`OTHER`).
- Classification is functioning well — even `OTHER` is being correctly detected with high confidence.

---

## ✅ Next Actions

- Implement **prompt templates for CommercialInvoice** and other common types.
- Add schema validation for JSON extraction output.
- Consider routing high-confidence `OTHER` cases to a separate workflow for manual review or specialized LLM chains.
- Flag and log invalid extractions for retraining or pattern analysis.

---

## 📂 Individual Document Reports

- [`test-letter-of-credit_README.md`](./test-letter-of-credit_README.md)
- [`test-letter-of-credit_1_README.md`](./test-letter-of-credit_1_README.md)
- [`test-commercial-invoice_README.md`](./test-commercial-invoice_README.md)
- [`test-ambiguous-financial-doc_README.md`](./test-ambiguous-financial-doc_README.md)

---

This summary helps communicate the **end-to-end observability** and **real-world performance** of the TDV pipeline — useful for stakeholders like Diego who care about classification precision, production safety, and traceability.