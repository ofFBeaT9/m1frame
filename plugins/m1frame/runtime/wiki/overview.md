# Overview

Auto-regenerated global summary. Human may edit.

## What this wiki is
The starter knowledge graph for the [[m1frame]] framework. It describes the engine and its real-time UI
([[m1frame Studio]], [[m1frame Constellation Release]]) and carries one worked demo so the pipeline has something
to show with no setup.

## The demo decision
m1frame's bundled run deliberates a question every team faces: **ship the MVP as a monolith or microservices?**
A 3-member council plus a red-team converge on the [[MVP Architecture Decision]] — start with a
[[Modular Monolith]], keep strict seams, and extract [[Microservices]] only on a real scaling trigger. The
reasoning leans on [[Conway's Law]] (don't make more services than you have teams) and avoids
[[Premature Decomposition]] (the "distributed monolith" trap). The red-team removes the one false claim that
microservices "eliminate" coupling — they relocate it to the network.

## Thesis
The point isn't the demo's answer; it's that you can **watch how it was reached** — debate, red-team veto,
grounding, and memory — then point m1frame at your own questions and replace these pages with your own.
