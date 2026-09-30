---
case_id: sample-2026-bluecrate-route-optimization
title: BlueCrate delivery route optimization POC
client: BlueCrate Logistics
sector: Last-mile logistics
client_type: sme
period: 2026 Q1
status: poc
confidentiality: confidential
budget_order: 25k EUR
effort_order: ~20 person-days
contact_person: ops@example.com
technologies: [route optimization solver, LLM triage, dispatch API]
capabilities: [route optimization, dispatch automation]
tender_tags: [proof of concept, logistics, scalability]
reusable_for: [last-mile delivery, fleet dispatch, route planning]
last_updated: 2026-04-10
metrics:
  - { value: "18%", label: "estimated reduction in drive time" }
  - { value: "12", label: "routes piloted" }
---

# Case: BlueCrate delivery route optimization POC

## 1. Summary

BlueCrate Logistics wanted to know whether AI-assisted route planning could
meaningfully cut delivery times before committing budget to a full build.
We ran a two-week proof of concept against twelve real routes and found an
estimated 18% reduction in drive time.

## 2. Client context

BlueCrate is a regional last-mile delivery operator planning routes
manually each morning based on driver experience and rough heuristics.

## 3. Problem or challenge

Manual route planning didn't account for real-time traffic, delivery
windows, or driver constraints together, leaving efficiency on the table.

## 4. Objective

Validate, cheaply and quickly, whether automated route optimization would
produce meaningfully better routes than the current manual process.

## 5. Approach

A short, tightly scoped proof of concept: replay twelve historical routes
through an optimization solver and compare against what was actually
driven, without touching the live dispatch system.

## 6. Solution

A standalone route-optimization prototype that takes the same delivery
list and constraints dispatchers use manually, and produces an optimized
route for comparison.

## 7. Technology and architecture

A commercial route-optimization solver wired up to historical delivery and
constraint data, with an LLM used to normalize messy address and time-window
inputs before optimization.

## 8. Our role

We scoped the POC, built the comparison harness, and presented the results
to BlueCrate's operations lead.

## 9. Human in the loop, governance and quality

As a POC, all outputs were reviewed manually against real driver knowledge
before drawing conclusions — nothing was deployed to live dispatch.

## 10. Results and impact

An estimated 18% reduction in drive time across the twelve piloted routes,
enough to justify moving to a funded pilot phase.

## 11. Implementation and follow-up

Results are being used internally to scope a live pilot; not yet deployed.

## 12. Tender relevance

Useful reference for fast, low-risk proof-of-concept work that de-risks a
bigger optimization investment before committing budget.

## 13. Evidence and details

Client: BlueCrate Logistics (confidential)
Sector: Last-mile logistics
Period: 2026 Q1
Budget order: 25k EUR
Scope: ~20 person-days
Contact: ops@example.com
Publicly shareable: no — internal reference only
