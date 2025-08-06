# 📄 Document Report – `test-commercial-invoice.png`

This document is a structured **Commercial Invoice** and was processed through the Trade Document Validator (TDV) pipeline to evaluate its classification, tabular field extraction, and structured parsing accuracy.

---

## 🔍 Document Summary

| Field              | Value |
|--------------------|-------|
| **Document Type**  | Commercial Invoice |
| **Classification Confidence** | 93% |
| **Source**         | Synthetic document (PNG) |
| **Document Quality** | High (clearly segmented, machine-readable) |
| **Image Dimensions** | 772 × 768 px |

---

## 🧠 Classification Results

| Metric        | Value |
|---------------|-------|
| **Predicted Type** | `CommercialInvoice` |
| **LLM Confidence Score** | 93% |
| **Prompt Used** | See [`../prompts/classification_prompt_template.txt`](../prompts/classification_prompt_template.txt) |

**Notes:**  
Claude correctly identified this document based on cues such as “Invoice Number”, “Description of Goods”, and “Grand Total”. The inclusion of freight charges and Incoterms further increased classification certainty.

---

## 🧾 Extraction Results

```json
{
  "invoice_number": "INV-2025-1087",
  "invoice_date": "August 6, 2025",
  "purchase_order": "PO-45372-ZMS",
  "exporter": "Artemis Microdevices GmbH",
  "importer": "Zenith Medical Supplies Ltd.",
  "currency": "EUR",
  "payment_terms": "Net 30 days",
  "shipment_details": {
    "carrier": "DHL Global Forwarding",
    "mode_of_transport": "Air Freight",
    "awb_number": "172-45639822",
    "departure_airport": "Frankfurt am Main (FRA)",
    "arrival_airport": "London Heathrow (LHR)",
    "dispatch_date": "August 4, 2025",
    "estimated_arrival": "August 7, 2025"
  },
  "line_items": [
    {
      "item_no": "001",
      "description": "Portable ECG Monitoring Devices (Model X90)",
      "quantity": 100,
      "unit_price": 350.00,
      "total": 35000.00
    },
    {
      "item_no": "002",
      "description": "Replacement Electrodes Pack (Box of 20)",
      "quantity": 250,
      "unit_price": 25.00,
      "total": 6250.00
    }
  ],
  "freight_charges": 750.00,
  "total_amount": 41250.00,
  "grand_total": 42000.00
}
```

| Extraction Accuracy | ⚠️ Partial |
|---------------------|------------|
| Errors              | Totals and freight parsed as raw text only in some tests |
| Improvements Needed | Table row detection; numerical field cleaning |
| Prompt Used         | `extraction_prompt_template.txt` |

---

## 📚 DynamoDB Context (Summarized)

- **Doc ID:** `test-commercial-invoice`
- **Classification Time:** 3.5s
- **LLM Model:** `claude-instant-v1`
- **Prompt Chain:** `classification → extraction`
- **Audit Trail:** One retry logged due to incomplete JSON (corrected on re-run)

---

## 📌 Observations

- The invoice structure (header + table + totals) makes it a valuable test case for layout-aware extraction.
- Claude performs well on block text, but struggles slightly with financial tables.
- Extraction of multiple line items worked, but formatting edge cases (e.g. comma-separated values) could affect parsing.

---

## ✅ Next Actions

- Add post-processing logic to detect tabular data regions
- Improve value type coercion and validation
- Use this doc for evaluating table parsing improvements

---
