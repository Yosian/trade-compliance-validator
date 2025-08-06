# 📄 Document Report – `test-ambiguous-financial-doc.png`

This file represents a **non-standard financial document**, styled as an internal memo related to vendor cost analysis. It was processed through the **Trade Document Validator (TDV)** to assess false positive rates and robustness of the classification pipeline.

---

## 🔍 Document Summary

| Field              | Value |
|--------------------|-------|
| **Document Type**  | Internal Memo (Ambiguous) |
| **Classification Confidence** | 24% |
| **Source**         | Synthetic memo-style PNG |
| **Document Quality** | Excellent (text-based memo) |
| **Image Dimensions** | 947 × 615 px |

---

## 🧠 Classification Results

| Metric        | Value |
|---------------|-------|
| **Predicted Type** | `Unknown` |
| **LLM Confidence Score** | 24% |
| **Prompt Used** | See [`../prompts/classification_prompt_template.txt`](../prompts/classification_prompt_template.txt) |

**Notes:**  
Model correctly returned low confidence. Despite the financial terminology, the structure and phrasing did not match formal documents such as invoices, LCs, or certificates. Key terms like "Approved by" or "Subject" were not sufficient to mislead the classifier.

---

## 🧾 Extraction Results

```json
{
  "document_type": "Internal Memo",
  "classification_confidence": 24,
  "extraction_attempted": false,
  "extraction_reason": "Confidence threshold not met; document excluded from extraction step"
}
```

| Extraction Accuracy | 🚫 Not Applicable |
|---------------------|------------------|
| Reason              | Below confidence threshold for type detection |
| Threshold Used      | 50% |
| Safety Guard        | `extraction_enabled: false` in metadata pipeline |

---

## 📚 DynamoDB Context (Summarized)

- **Doc ID:** `test-ambiguous-financial-doc`
- **Classification Timestamp:** Available
- **Inference Model:** `claude-instant-v1`
- **Pipeline Decision:** Document routed to "review-only" queue
- **Audit Trail:** No retries, flagged as low-priority by `tdv-dev-audit-trail.csv`

---

## 🔎 Observations

- This is a strong **negative control test** – useful for auditing classification boundaries
- Memo-style documents containing financial topics should not be processed as trade documents
- System correctly bypassed extraction phase, maintaining processing integrity

---

## ✅ Next Actions

- Add more ambiguous documents to stress-test classifier boundaries
- Include this case in evaluation benchmark (false positive avoidance)
- Consider a fallback flow for flagging potential memo documents with “Planning Only” disclaimer

---

**Return to [`results/`](../results/)**