---
case_id: sample-2026-port-authority-document-intake
title: Harbor Authority document intake automation
client: Regional Harbor Authority
sector: Public sector logistics
client_type: public
period: 2025
status: pilot
confidentiality: anonymized
budget_order: unknown
effort_order: ~40 person-days
contact_person: ops@example.gov
technologies: [document extraction, OCR, LLM classification, validation UI]
capabilities: [document extraction, email classification, human in the loop, masterdata matching]
tender_tags: [governance, human in the loop, public sector, data intensive]
reusable_for: [customs document processing, permit intake, regulated document workflows]
last_updated: 2026-05-20
metrics:
  - { value: "70%", label: "manifests auto-classified" }
  - { value: "1,200+", label: "documents per month" }
diagram:
  type: flow
  caption: "Incoming manifests are extracted, classified and validated before entering the case system."
  nodes:
    - { id: mail, label: "Document\nintake" }
    - { id: ext,  label: "OCR +\nextraction" }
    - { id: llm,  label: "Model API\n+ classification", accent: true }
    - { id: ui,   label: "Validation UI\n(human in the loop)" }
    - { id: case, label: "Case\nsystem" }
  edges:
    - [mail, ext]
    - [ext, llm]
    - [llm, ui]
    - [ui, case]
---

# Case: Harbor Authority document intake automation

## 1. Summary

A regional harbor authority receives shipping manifests and customs
paperwork in inconsistent formats from hundreds of vessels each month. We
built a document-intake pipeline that extracts structured data from scans
and PDFs, classifies each document, and routes uncertain cases to a human
reviewer before anything reaches the case-management system.

## 2. Client context

A public harbor authority responsible for processing shipping documentation
under regulatory oversight, with a small back-office team handling growing
volumes manually.

## 3. Problem or challenge

Manifests arrive as scans, PDFs, and free-text emails, in varying formats
and languages, and had to be manually keyed into the case system — slow,
error-prone, and increasingly a bottleneck.

## 4. Objective

Automate extraction and classification without weakening the audit trail
regulators require, and without ever silently guessing on uncertain
documents.

## 5. Approach

Because this is a regulated public-sector context, the project began with a
governance workshop to agree what "safe automation" meant here, then built
a narrow pilot scope with heavy validation before any expansion.

## 6. Solution

An OCR and extraction pipeline reads incoming documents, a model classifies
and structures the content, and every result below a confidence threshold
is queued in a validation UI for a human reviewer before it reaches the
case system.

## 7. Technology and architecture

OCR and document-extraction tooling feed a classification model; a
lightweight validation interface gives reviewers full visibility into what
the model was and wasn't confident about.

## 8. Our role

We designed the extraction-to-validation pipeline and the audit-friendly
review interface, working closely with the authority's compliance team.

## 9. Human in the loop, governance and quality

Every document below the confidence threshold is reviewed by a human before
it reaches the case system; all decisions are logged for audit.

## 10. Results and impact

70% of manifests are now auto-classified with no human involvement, across
over 1,200 documents per month, with a full audit trail retained.

## 11. Implementation and follow-up

Currently in pilot with a subset of document types; expansion planned after
the current audit cycle.

## 12. Tender relevance

Strong reference for regulated, audit-sensitive document automation with an
explicit human-in-the-loop and governance story.

## 13. Evidence and details

Client: Regional Harbor Authority (anonymized)
Sector: Public sector logistics
Period: 2025
Budget order: unknown
Scope: ~40 person-days
Contact: ops@example.gov
Publicly shareable: describe only, do not name the client
