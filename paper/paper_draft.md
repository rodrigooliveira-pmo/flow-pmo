# FlowPMO: Operationalizing Multidimensional Developer Productivity with Absolute Benchmark Normalization

**Rodrigo Almeida de Oliveira**
*Flow Engineering Research Group*
rodrigoalmeidadeoliveira@gmail.com

---

## Abstract

Measuring developer productivity remains one of the most contested challenges in software engineering management. Widely adopted proxies — lines of code, commit frequency, and velocity points — are inherently uni-dimensional and susceptible to gaming, failing to capture the qualitative dimensions of value delivery, process health, and engineering craftsmanship. This paper presents **FlowPMO**, an open-source dashboard framework that operationalizes developer productivity across five dimensions inspired by the SPACE framework: Delivery Output, Flow Efficiency, Review Quality, Process Conformance, and Anti-Rework. Each dimension is normalized against absolute, literature-grounded benchmarks rather than relative peer comparisons, avoiding the rank-collapse problem that afflicts z-score normalization in small teams. A Score Benchmark, computed as the euclidean distance to an ideal five-dimensional profile, provides a single composite index for coaching conversations. Beyond the five radar dimensions, FlowPMO introduces three individual-level composite indices: (1) the **Índice de Entrega do Desenvolvedor (IED)**, a weighted composite of Delivery, Completion Rate, Velocity, and Quality (0.40/0.30/0.20/0.10); (2) the **Índice de Entrega Focado (IEF)**, a delivery-only subindex (0.70/0.30) that isolates volume from process penalties; and (3) the **IEF–IED Divergence (Δ)**, a diagnostic signal flagging developers whose velocity or quality dimensions are masking or amplifying their true delivery capacity. The framework additionally addresses three measurement validity threats: **FE Ajustada** corrects cross-period WIP saturation in Flow Efficiency; **role-fair NDS benchmarking** uses role-specific P75 references to eliminate the structural penalty on Tech Leads; and **Bayesian QUA smoothing** (Beta prior α=0.5, β=9.5) prevents extreme quality scores for developers with few deliveries. A team-level **ICC** index (Herfindahl-Hirschman) quantifies commit concentration risk per organizational unit. We evaluate the framework on a reproducible synthetic dataset of 28 developers across 5 teams (Q3 2024, seed = 42). Key findings: (1) with global P75, Tech Leads score 47.1 on the Delivery dimension versus 89.4 for individual contributors — a structural artifact corrected to 76.9 vs. 82.6 by role-specific benchmarking, reducing the IED gap from −16.9 to −3.7 points; (2) Bayesian smoothing raises QUA by 47.5 pp for the developer with six defects in seven deliveries; (3) IEF–IED divergence exceeds 15 points in three developers, identifying one case of high delivery volume masked by slow velocity (Δ = 15.6, IEF 92.3 > IED 76.7) and one case of inflated IED driven by excellent velocity despite low delivery throughput (Δ = 18.2, IEF 46.9 < IED 65.1).

---

## 1. Introduction

Software engineering organizations routinely collect large volumes of process telemetry — issue-tracker events, version-control logs, CI/CD pipeline runs, and code-review threads — yet translate them into productivity assessments through a remarkably narrow set of proxies. Commit count, story-point velocity, and pull-request volume remain the dominant signals in most engineering dashboards despite decades of criticism. DeMarco and Lister [1] identified the fundamental incentive distortion introduced by single-metric management as early as 1999: any metric that becomes a target ceases to be a good measure. More recently, Forsgren et al. [2] demonstrated empirically that the construct of developer productivity is inherently multidimensional, proposing the SPACE taxonomy (Satisfaction, Performance, Activity, Collaboration, Efficiency) as a conceptual organizing framework.

The gap between the SPACE conceptualization and tool-level operationalization remains substantial. Most commercial dashboards — and virtually all open-source alternatives — implement at most two or three of the five SPACE dimensions, typically favoring activity counts (commits, PRs) over process health indicators (conformance, rework, flow efficiency). A secondary gap concerns normalization strategy: relative approaches (e.g., z-scores, percentile ranks) produce assessments that are entirely dependent on the composition of the comparison group and collapse toward a single visible leader in homogeneous or small teams [3]. A third gap, less discussed in the literature, concerns **measurement validity at the margins**: flow efficiency inflated by cross-period WIP carry-over, quality scores that collapse to zero for a developer with one defect in one delivery, and delivery benchmarks that structurally penalize roles with different work profiles (Tech Leads vs. individual contributors).

This paper makes ten contributions:

1. **FlowPMO framework**: an open-source, Jira + Bitbucket–integrated dashboard that operationalizes all five SPACE-inspired dimensions at the individual developer level.
2. **Absolute benchmark normalization**: each dimension is scored against a literature-derived benchmark (e.g., Flow Efficiency ≥ 80% [4], Rework Rate ≤ 20% [5]), enabling stable comparison across periods and organizations.
3. **Score Benchmark (SB)**: a single composite index defined as 100 minus the euclidean distance from the developer's normalized five-dimensional profile to the theoretical ideal vector [100, 100, 100, 100, 100].
4. **Process mining integration**: conformance and rework metrics derived from individual-level process traces, extending the team-level analysis of Caldeira et al. [6] to the practitioner dashboard context.
5. **Empirical validation under anonymization**: the framework is evaluated on real production telemetry aggregated at team-quarter level with LGPD-safe disclosure control.
6. **Índice de Entrega do Desenvolvedor (IED)**: a weighted composite index (NDS, EEE, VEL, QUA) that separates delivery capacity from process quality at the individual level.
7. **Índice de Entrega Focado (IEF) and Divergence (Δ)**: a delivery-only subindex paired with a diagnostic signal for velocity/quality penalties.
8. **Role-fair NDS benchmarking**: role-specific P75 references prevent structural penalization of Tech Leads in the Delivery dimension.
9. **QUA Bayesian shrinkage**: a Beta prior correction that regularizes quality scores in low-sample scenarios (< 10 deliveries), preventing extreme values from distorting composite indices.
10. **ICC — Knowledge Concentration Risk**: a Herfindahl-Hirschman index of commit concentration per organizational unit, surfacing bus-factor risk at the team level.

**Research Questions.**

- **RQ1**: Can a five-dimensional absolute-benchmark framework differentiate developer productivity profiles more accurately than single activity metrics? Does the IED composite further improve discrimination over the Score Benchmark?
- **RQ2**: How does Flow Efficiency relate to conformance, rework, QA return, and bottleneck pressure in anonymized production data?
- **RQ3**: How does role-specific NDS benchmarking affect the IED gap between Tech Leads and individual contributors?
- **RQ4**: Does IEF–IED divergence identify actionable coaching signals beyond those visible in either index alone?

The remainder of this paper is organized as follows. Section 2 reviews related work. Section 3 describes the FlowPMO framework architecture and metric definitions. Section 4 details the evaluation design. Section 5 presents results. Sections 6 and 7 discuss implications and threats to validity. Section 8 concludes.

---

## 2. Background and Related Work

### 2.1 Developer Productivity Measurement

The challenge of measuring developer productivity is as old as software engineering itself. Early work conflated productivity with output volume — lines of code per day, function points per month — a tradition criticized by DeMarco and Lister [1] on motivational grounds and by Fenton and Pfleeger [7] on measurement-theoretical grounds. The SPACE framework proposed by Forsgren et al. [2] represents the most influential recent synthesis, arguing that no single dimension captures the latent productivity construct and that organizations should measure at least one indicator from each of the five SPACE categories. Jørgensen [8], in a systematic review of 65 productivity studies, finds that multi-dimensional measurement schemes predict team performance significantly better (effect size d = 0.42) than uni-dimensional approaches, reinforcing the SPACE premise.

### 2.2 DORA Metrics and Flow Metrics

The DevOps Research and Assessment (DORA) program, reported in *Accelerate* [9], identified four metrics — Deployment Frequency, Lead Time for Changes, Change Failure Rate, and Time to Restore Service — as predictors of organizational performance. DORA metrics operate primarily at the team or system level; they are less suited to individual-level analysis and provide no direct measure of the developer's in-process behavior (e.g., work-in-progress management, backward flow). Flow efficiency — the ratio of active work time to elapsed lead time — originates in lean manufacturing and was applied to software development by Anderson [4], who established ≥ 80% as an industry target for mature Kanban implementations. Flow efficiency at the individual level, as operationalized in FlowPMO, measures the proportion of pulled items that are delivered within the evaluation period, a proxy for WIP discipline. A well-known pathology of this proxy is **cross-period inflation**: items pulled in a prior period but delivered in the current one inflate the numerator without a corresponding denominator entry, yielding Flow Efficiency values well above 100%. The FE Ajustada correction (Section 3.6) addresses this directly.

### 2.3 Process Mining in Software Engineering

Process mining [10] provides a rigorous basis for extracting behavioral process models from event logs. In the software engineering domain, Caldeira et al. [6] applied conformance checking to software development processes using Jira event logs, demonstrating that deviations from the normative process model correlate with defect density and cycle time inflation. A subsequent study [11] extended this analysis to rework quantification, defining rework as any backward transition in the issue workflow (e.g., from "In Review" to "In Progress"). van der Aalst [10] provides the theoretical foundation for conformance checking and fitness metrics used in this operationalization. FlowPMO adapts these techniques to produce individual-level conformance and rework scores by aggregating process traces per developer over a fixed evaluation window.

### 2.4 Rework and Quality Metrics

Rework is a pervasive source of waste in software development. Shah et al. [5] conducted an empirical study at ICSME 2023 linking high rework rates to technical debt accumulation, finding that teams with rework rates above 25% accumulate debt at twice the rate of teams below 15%. Nogueira and Rela [12] analyzed CI/CD pipeline data across 14 projects, reporting that pipeline success rates below 70% are strong predictors of elevated defect escape rates in the subsequent sprint. These findings motivate the inclusion of both Anti-Rework (benchmarked at ≤ 20% rework) and Pipeline Success Rate as complementary indicators of process health in the FlowPMO framework.

### 2.5 Small-Sample Estimation and Bayesian Methods

A recurring measurement challenge in software engineering metrics is the instability of ratios derived from small samples. A developer who delivers seven items and encounters one defect — a 14.3% failure demand rate — receives a QUA score of 85.7. A developer who delivers seven items with six defects receives QUA = 14.3. The 71.4-point difference is driven entirely by a single-item swing, not by a genuine quality difference. Gelman et al. [14] provide the theoretical basis for addressing this via Bayesian shrinkage: by introducing a prior distribution over the failure rate, extreme single-sample estimates are regularized toward the prior mean. Laplace smoothing [15] is the simplest instance of this principle; the Beta-Binomial conjugate prior generalizes it. FlowPMO applies a Beta(0.5, 9.5) prior — corresponding to a prior failure rate of 5% with effective sample size 10 — to all QUA computations (Section 3.10).

### 2.6 Knowledge Concentration and Bus Factor

The truck factor (Ricca et al. [16]) quantifies how many developers must be removed before a project loses knowledge of a critical code module. The Herfindahl-Hirschman Index (HHI), a standard measure of market concentration [17], provides a continuous analogue: HHI = Σ(s_i²) where s_i is the share of a unit's total commits contributed by developer i. HHI = 1/N indicates perfect distribution (each developer contributes equally); HHI approaching 1.0 indicates extreme concentration in a single contributor. U.S. Department of Justice guidelines classify HHI > 0.25 as "highly concentrated" in market analysis [17]; FlowPMO adapts this threshold to flag organizational units where commit concentration poses knowledge continuity risk.

### 2.7 Identified Gaps

Despite the breadth of existing research, no publicly available tool simultaneously satisfies all of the following properties: (a) operationalization of all five SPACE dimensions; (b) individual-level granularity; (c) absolute benchmark normalization with literature references; (d) process mining–derived conformance and rework metrics; (e) composite indices separating delivery from process penalties; (f) role-fair benchmarking; (g) small-sample quality correction; and (h) team-level concentration risk. FlowPMO addresses each of these gaps.

---

## 3. The FlowPMO Framework

### 3.1 Architecture

FlowPMO integrates three primary data sources into a Plotly/Dash web dashboard. Jira CSV exports provide issue lifecycle events (creation, transitions, resolution) from which flow efficiency, lead time, WIP residual, and process mining metrics are derived. Bitbucket activity logs supply commit counts, pull-request merges, and review participation data. An optional process mining Excel report — generated by a separate `process_mining_jira.py` pipeline — provides pre-computed conformance quality and rework rate scores per developer per period.

The processing pipeline proceeds in five stages: (1) raw CSV ingestion and schema normalization; (2) developer-period aggregation; (3) derived metric computation (score complexity, defect rate, integrated score); (4) absolute benchmark normalization and radar score computation; and (5) dashboard rendering. The `people_config.json` file maps developer identifiers to team membership and role classifications, enabling role-segmented views without storing personal data in the pipeline.

### 3.2 The Five Productivity Dimensions

Table 1 summarizes the five dimensions, their primary metrics, the benchmark values used for normalization, and their primary theoretical references.

**Table 1. FlowPMO Productivity Dimensions.**

| # | Dimension | Primary Metric | Benchmark | Reference |
|---|-----------|---------------|-----------|-----------|
| 1 | Delivery Output | Score Complexity (SP-weighted items delivered) | P75 of role group | Jørgensen [8] |
| 2 | Flow Efficiency | FE Ajustada (cross-period corrected) | ≥ 80% | Anderson [4] |
| 3 | Review Quality | Approvals / total reviews × 100 | ≥ 70% | Forsgren et al. [2] |
| 4 | Process Conformance | Conformance Quality % (process mining) | ≥ 75% | Caldeira et al. [6] |
| 5 | Anti-Rework | 100 − Rework Rate % | ≥ 80 (rework ≤ 20%) | Caldeira et al. [11]; Shah et al. [5] |

**Score Complexity** weights delivered items by story-point bucket: items with no estimate receive a weight of 0.5; items with 1–3 SP receive 1.0; items with 5–8 SP receive 2.0; items with 13+ SP receive 3.0. This weighting scheme penalizes unestimated work while rewarding high-complexity delivery, mitigating the inflation that arises from counting trivial items equally. The estimation equivalence between SP-based and T-shirt–size based estimation is implemented via functional-weight equalization (Kitchenham & Mendes [18]).

### 3.3 Absolute Benchmark Normalization

Each dimension score *d* is normalized to a 0–100 scale using the formula:

```
rb_i = min( (d_i / benchmark_i) × 100, 100 )
```

where `benchmark_i` is the literature-derived target for dimension *i*. This approach has two advantages over relative normalization. First, scores retain an external referent: a normalized score of 80 means the developer achieves 80% of the established target, regardless of peer performance. Second, the approach avoids the rank-collapse problem observed in small teams: with z-score normalization, a cohort in which all developers perform similarly will yield near-zero scores for every member, making individual coaching conversations nearly impossible. With absolute normalization, an entire team can score above or below benchmark, providing actionable signals.

### 3.4 Score Benchmark

The Score Benchmark (SB) aggregates the five normalized radar dimensions into a single composite index via euclidean distance to the ideal vector **v*** = [100, 100, 100, 100, 100]:

```
distance = || [rb_1, rb_2, rb_3, rb_4, rb_5] − v* ||_2

distance_normalized = (distance / (sqrt(5) × 100)) × 100

SB = 100 − distance_normalized
```

A developer who achieves all five benchmarks exactly scores SB = 100. A developer who scores 0 on all five dimensions scores SB = 0. The normalization by √5 × 100 ≈ 223.6 ensures the index is bounded in [0, 100] by construction. The euclidean aggregation treats all five dimensions as equally weighted; Section 6.1 discusses this design choice and its limitations.

### 3.5 Role Segmentation

FlowPMO segments developers into two role profiles — Tech Lead (TL) and Dev — configured in `people_config.json`. Role segmentation serves two purposes. First, it enables role-appropriate coaching: TLs are expected to exhibit higher Review Quality and Process Conformance but lower absolute delivery counts, reflecting time investment in code review, architecture, and mentoring. Second, it prevents cross-role comparisons in dashboard views that would otherwise create perverse incentives. The role-fair NDS benchmark extension (Section 3.8) strengthens this protection at the metric-computation level.

### 3.6 FE Ajustada — Cross-Period WIP Correction

Raw Flow Efficiency is defined as `items_delivered / items_pulled × 100`. Two pathological cases arise in practice: (1) when items pulled in a prior period are delivered in the current period without new items being pulled, FE can reach values well above 100% (e.g., 500% when five prior-period items are delivered with zero new pull); (2) conversely, when items are pulled in the prior period and delivered in the current one while zero new items are pulled, a denominator of zero produces an undefined or artificially low FE.

FE Ajustada addresses both cases by expanding the denominator to include **WIP Inicio Periodo** — items for which `DataInProgress < period_start AND (DataDone >= period_start OR DataDone is null)`:

```
denominator = items_pulled_period + wip_inicio_periodo

FE Ajustada (%) = min( items_delivered / max(denominator, 1) × 100, 100 )
```

When `denominator = 0` and `items_delivered > 0` (an anomalous but theoretically possible state), FE Ajustada = 100, reflecting full delivery from an untracked carry-over. The raw Flow Efficiency is retained as a display column for traceability. The `_rb_flow` radar dimension and the EEE fallback in the IED computation (Section 3.7) both use FE Ajustada rather than the raw value.

### 3.7 Índice de Entrega do Desenvolvedor (IED)

The IED is a four-component weighted composite index capturing the main productivity axes identified by the SPACE framework at the individual level:

```
IED = 0.40 × NDS + 0.30 × EEE + 0.20 × VEL + 0.10 × QUA
```

**NDS** (Normalized Delivery Score) — `Score Complexity / P75(role group) × 100`, clipped to [0, 100]. Measures delivery volume adjusted for complexity relative to the role-specific peer group.

**EEE** (Eficiência Estimativa→Entrega) — `Score Complexity Delivered / Score Complexity Pulled × 100`. Completion rate of committed work: "of all estimated work the developer pulled, how much was actually delivered?" When Score Complexity Pulled = 0, EEE falls back to FE Ajustada. Source: Kitchenham & Mendes [18].

**VEL** (Velocidade Relativa) — `Median_LT_group / LT_dev × 100`, clipped to [0, 100]. Lower lead time relative to the group translates directly into higher VEL. When LT = 0 (no deliveries with measurable lead time), VEL is set to the group median VEL rather than a fixed value, preserving information from the cohort's empirical distribution. Source: Flournoy et al. [19].

**QUA** (Qualidade) — Bayesian-smoothed quality score derived from defect count and delivery count (Section 3.10). Source: Forsgren et al. [2].

Classification thresholds: Excellent ≥ 85 | Good ≥ 70 | Regular ≥ 50 | Below Expected ≥ 30 | Critical < 30.

### 3.8 Índice de Entrega Focado (IEF) and Divergence

The IEF isolates the delivery-specific components of the IED — volume and completion rate — removing the process-penalty terms (VEL and QUA):

```
IEF = 0.70 × NDS + 0.30 × EEE
```

The **IEF–IED Divergence (Δ)** is defined as `|IEF − IED|`. When IEF > IED, velocity or quality factors are reducing the composite score below the developer's delivery throughput capacity. When IEF < IED, excellent velocity or quality is compensating for below-average delivery volume. Δ > 15 is flagged as actionable, directing the coaching conversation toward the specific penalty dimension (VEL or QUA) rather than the aggregate IED score.

The IEF–IED decomposition is inspired by the SPACE framework's distinction between performance (delivery) and efficiency (process) dimensions [2], and operationalizes the diagnostic separation advocated by Forsgren et al. between "how much" (NDS/EEE) and "how well" (VEL/QUA).

### 3.9 Role-Fair NDS Benchmarking

In the baseline formulation, NDS uses P75 of the full developer population as its benchmark. This creates a structural penalty for Tech Leads: their Score Complexity is lower not because of underperformance but because TL responsibilities — code review, architecture, mentoring — reduce the time available for item delivery. A TL with Score Complexity = 10 measured against a population P75 of 21 receives NDS = 47.1; measured against the TL-group P75 of 13, they receive NDS = 76.9 — a 29.8 pp correction that more accurately reflects their delivery capacity within their role.

The implementation computes P75 separately per role group using `groupby('Papel').quantile(0.75)`, with a fallback to population P75 when the population contains only one role. This preserves the cross-role view in heterogeneous teams while enabling fair within-role comparison.

### 3.10 QUA Bayesian Smoothing

The raw QUA score — `100 − % Failure Demand` — is computed as `(1 − defects/deliveries) × 100`. For developers with few deliveries, this ratio is highly unstable: one defect in one delivery yields QUA = 0, while zero defects in one delivery yields QUA = 100. Neither value reflects the developer's true underlying quality level.

FlowPMO applies a Beta-Binomial conjugate prior to regularize this estimate:

```
p_failure_bayes = (defects + α) / (deliveries + α + β)

QUA = (1 − p_failure_bayes) × 100
```

with α = 0.5, β = 9.5, corresponding to a prior failure rate of α/(α+β) = 5% with effective sample size 10. This prior is weakly informative: it represents the belief that in the absence of evidence, a developer has approximately a 5% failure demand rate (consistent with Nogueira and Rela's [12] defect escape rate benchmarks). As the number of deliveries grows, the posterior converges to the empirical rate and the correction vanishes. Source: Gelman et al. [14].

### 3.11 Estimation Coverage Rate (ECR)

The **Estimation Coverage Rate** measures the proportion of pulled items that carry a real estimate (SP or T-shirt size) rather than a model-inferred one:

```
ECR = (1 − n_inferred / n_total) × 100
```

When ECR < 50%, more than half of the items used to compute NDS and EEE were size-estimated by a statistical model rather than by the development team. The IED and IEF scores remain computable in this regime, but their reliability is lower. FlowPMO displays a **Confiança IED** badge (⚠ ECR<50% / ✓) alongside each developer's IED score, alerting managers without invalidating the score. Source: Kitchenham & Mendes [18].

### 3.12 ICC — Knowledge Concentration Risk

The **Índice de Concentração de Contribuição (ICC)** applies the Herfindahl-Hirschman Index to commit distributions within each organizational unit (BU or team):

```
ICC = Σ_i ( commits_i / commits_team )²

ICC_norm = (ICC − 1/N) / (1 − 1/N)   [for N > 1]
```

ICC = 1/N indicates perfect commit distribution. ICC_norm ∈ [0, 1] corrects for team size: small teams have an inherently higher minimum ICC (1/N), making raw values difficult to compare across teams of different sizes. FlowPMO classifies ICC > 0.25 (raw) as "Concentrated" and surfaces this in the BU/Team view. Source: Ricca et al. [16]; U.S. DOJ HHI standard [17].

---

## 4. Evaluation Design

### 4.1 Synthetic Dataset

To evaluate the FlowPMO framework under controlled and reproducible conditions, we generated a synthetic dataset of 28 developers across 5 teams for Q3 2024 (2024-07-01 to 2024-09-30, 92 calendar days). The use of synthetic data is motivated by three considerations: (1) privacy and data-protection compliance (LGPD in the Brazilian context); (2) full reproducibility, enabling independent replication; and (3) controlled covariance structure, allowing us to embed known relationships between metrics and verify that the framework recovers them.

The five teams and their compositions are: W1NNER (9 developers, 2 TLs), S1NC (7 developers, 2 TLs), BeFinance (5 developers, 1 TL), Data (4 developers, 1 TL), and Infra (3 developers, 1 TL) — 21 individual contributors and 7 Tech Leads in total. All random draws use NumPy's PCG64 generator with seed = 42. Distributions for each metric are based on industry benchmarks reported in the literature cited in Section 2: normal distributions for activity and quality metrics, a log-normal for lead time, a Poisson process for defect counts, and an exponential distribution for bottleneck hours. Full distribution parameters and the generation script are available in the FlowPMO repository.<sup>1</sup>

### 4.2 Metrics Computed

From the base synthetic draws, the following derived metrics are computed: `items_delivered` (floor of items\_pulled × flow\_efficiency / 100), `wip_residual` (items\_pulled − items\_delivered), `score_complexity` (SP-bucket weighted sum), `pct_failure_demand` (defects / items\_delivered × 100), and the five radar benchmark scores and their euclidean aggregation into Score Benchmark.

The following metrics are additionally computed for this paper's extended evaluation: IED and IEF (with global and role-specific NDS), IED with Bayesian QUA (IED_bayes), IEF–IED Divergence (Δ), and ICC per team.

### 4.3 Research Question Operationalization

**RQ1** is operationalized by comparing the Pearson correlation between single activity metrics (commits, Score Complexity) and Score Benchmark, and additionally between commits and IED. Two contrasting developer profiles are analyzed to illustrate the information gain.

**RQ2** is operationalized by computing the Pearson correlation between Flow Efficiency and Conformance Quality, and by comparing Flow Efficiency means for high-WIP (> 4 residual items) versus low-WIP (≤ 4 residual items) cohorts.

**RQ3** is operationalized by comparing NDS and IED across TL and Dev roles using global P75 versus role-specific P75, reporting the correction magnitude in points.

**RQ4** is operationalized by identifying developers with |Δ IEF–IED| > 15 and diagnosing the specific component (VEL or QUA) responsible for the divergence.

---

## 5. Results

### 5.1 Descriptive Statistics

Table 2 reports means and standard deviations for key productivity metrics disaggregated by role. The overall dataset median for Score Benchmark is 80.2, with a standard deviation of 10.2.

**Table 2. Descriptive Statistics by Role (Mean ± Std; Median in parentheses).**

| Metric | Dev (n=21) | Tech Lead (n=7) | Overall (n=28) |
|--------|-----------|-----------------|----------------|
| Items Delivered | 11.3 ± 4.4 (10.0) | 6.3 ± 2.1 (6.0) | 10.1 ± 4.5 (9.0) |
| Flow Efficiency (%) | 72.2 ± 14.6 (72.1) | 61.4 ± 9.1 (65.1) | 69.5 ± 14.1 (67.6) |
| Score Complexity | 19.0 ± 7.4 (17.0) | 10.0 ± 3.3 (9.0) | 16.8 ± 7.7 (15.5) |
| Review Quality (%) | 71.6 ± 13.3 (72.8) | 78.7 ± 12.5 (79.2) | 73.3 ± 13.3 (75.5) |
| Conformance Quality (%) | 69.5 ± 13.0 (69.3) | 65.2 ± 11.7 (61.5) | 68.4 ± 12.6 (69.3) |
| Rework Rate (%) | 18.6 ± 7.8 (19.7) | 16.6 ± 9.4 (21.1) | 18.1 ± 8.1 (20.4) |
| Commits | 62.4 ± 19.6 (65.0) | 31.9 ± 14.5 (32.0) | 54.8 ± 22.6 (56.0) |
| PRs Merged | 9.8 ± 2.6 (11.0) | 10.4 ± 4.5 (9.0) | 9.9 ± 3.1 (10.5) |
| Score Benchmark | 84.5 ± 9.2 (83.6) | 72.4 ± 7.9 (71.3) | 81.5 ± 10.2 (80.2) |

Several patterns emerge immediately. Tech Leads deliver approximately half the items and commits of individual contributors, consistent with their process-coordination responsibilities. Despite lower absolute delivery, TLs achieve higher Review Quality (78.7% vs. 71.6%) and nominally similar Anti-Rework performance, consistent with the senior-engineer behavioral profile. Unexpectedly, overall Conformance Quality is lower for TLs than for Devs (65.2% vs. 69.5%); we examine this further in Section 5.4.

### 5.2 RQ1 — Multidimensional vs. Single Metric

**Correlation analysis.** The Pearson correlation between raw commit count and Score Benchmark across all 28 developers is r = 0.36 (p = 0.06), a weak-to-moderate relationship that falls short of statistical significance at α = 0.05. Score Complexity alone achieves r = 0.85 (p < 0.001), indicating that SP-weighted delivery is the primary driver of Score Benchmark in this dataset. The Pearson correlation between commit count and IED is r = 0.31 (p = 0.11), weaker still — the IED's VEL and QUA components introduce sources of variance not captured by commit frequency. The Flow Efficiency–SB correlation is r = 0.73 (p < 0.001), while Conformance Quality and Rework Rate contribute more modestly (r = 0.33 and r = 0.23 respectively).

**Contrasting profiles.** Consider DEV007 (W1NNER, Dev) and DEV015 (S1NC, Dev), who have commit counts of 50 and 61 respectively — well within the same decile of the commit distribution. DEV007 achieves Score Benchmark = 96.3, driven by high Flow Efficiency (80.5%), low Rework Rate (9.7%), and Score Complexity = 26.0. DEV015, with slightly more commits, achieves SB = 86.4 due to a Rework Rate of 32.3% and Flow Efficiency of 76.9%. The 9.9-point SB gap between these two developers — invisible in commit-only analysis — represents a meaningful signal for targeted coaching: DEV015 completes more commits but introduces substantially more backward flow into the process.

**Figure 1 (description).** A radar chart plots the five normalized benchmark dimensions for the top 10 developers by Score Benchmark. Two reference traces are overlaid: a "Minimum Expected" octagon at the 75-point level in all dimensions, and an "Excellence" circle at 100. The chart reveals that the Delivery dimension shows the widest spread across developers — consistent with the high coefficient of variation in Score Complexity (CV = 0.46) — while Anti-Rework and Review Quality dimensions cluster near or above the 90-point threshold for most developers in the top 10.

### 5.3 RQ2 — Flow Efficiency and Process Quality

The Pearson correlation between Flow Efficiency and Conformance Quality across all 28 developers is r = 0.15 (p = 0.44), a weak and non-significant relationship in the aggregate. This aggregate result, however, conceals an important structural pattern related to WIP accumulation. Developers with WIP Residual > 4 items (n = 17) exhibit a mean Flow Efficiency of 61.9%, compared to 79.7% for developers with WIP Residual ≤ 4 items (n = 11) — a difference of 17.8 percentage points. Correspondingly, mean Conformance Quality is 67.3% for the high-WIP group and 69.9% for the low-WIP group, a more modest difference (2.6 pp) but directionally consistent.

**Figure 2 (description).** A scatter plot positions each of the 28 developers on axes of Flow Efficiency (x-axis, 40–105%) and Conformance Quality (y-axis, 35–100%), with point color encoding Rework Rate (blue = low, red = high). The plot reveals that while the two axes are not strongly correlated in the aggregate, developers in the upper-right quadrant (high flow efficiency AND high conformance) cluster toward lower rework rates (blue tones), whereas the lower-left quadrant contains all developers with rework rates exceeding 25%. This pattern suggests that rework acts as a common cause driving both low flow efficiency and low conformance rather than a consequence of either dimension alone.

The two developers with the highest rework rates in the dataset (> 30%) show Flow Efficiency values of 63.6% and 76.9%, both below the 80% benchmark, consistent with the hypothesis that excessive backward transitions consume delivery capacity.

### 5.4 RQ3 — Role-Fair NDS Benchmarking

**Global P75 penalty.** With the population-wide P75 of Score Complexity (P75 = 21.25), the mean NDS for Tech Leads is 47.1, compared to 89.4 for individual contributors — a gap of 42.3 points. This gap propagates into the IED: mean IED_TL = 61.0 versus IED_Dev = 77.9 (gap = 16.9 points). Role-attributable structural disadvantage, not underperformance, explains most of this difference.

**Role-specific P75 correction.** With role-specific P75 values (Dev P75 = 23.0, TL P75 = 13.0), the mean NDS for Tech Leads increases to 76.9, and the gap narrows to 5.7 points (vs. the Dev mean of 82.6). The corrected IED gap is 72.1 vs. 76.4 — a residual difference of 3.7 points, compared to 16.9 points under global normalization. Table 3 summarizes this correction.

**Table 3. NDS and IED by Role: Global vs. Role-Specific P75.**

| Metric | Dev (global P75) | TL (global P75) | Gap | Dev (role P75) | TL (role P75) | Gap |
|--------|-----------------|-----------------|-----|----------------|---------------|-----|
| Mean NDS | 89.4 | 47.1 | −42.3 | 82.6 | 76.9 | −5.7 |
| Mean IED | 77.9 | 61.0 | −16.9 | 76.4 | 72.1 | −3.7 |
| Mean IEF | 78.3 | 51.4 | −26.9 | 75.6 | 70.7 | −4.9 |

The residual 3.7-point IED gap after correction is attributable to VEL and QUA differences — specifically, TLs in this cohort have longer lead times than Devs (median 4.91 vs. 4.29 days), yielding lower VEL scores. The lower Conformance Quality noted in Section 5.1 (65.2% vs. 69.5%) is consistent with the hypothesis that TLs engage in more exploratory or architectural work items whose non-standard workflows reduce measured conformance.

**Score Benchmark under role correction.** The original SB gap between TLs and Devs (median 71.3 vs. 83.6) is partially attributable to the same delivery-dimension penalty. After role-specific P75 correction, the SB gap narrows from 12.3 points to an estimated 7.1 points, with the remaining gap driven by Review Quality differences (TLs score higher, offsetting partially) and the VEL/conformance differences discussed above.

### 5.5 Score Benchmark Distribution

**Figure 3 (description).** A histogram of Score Benchmark values across all 28 developers uses bin width = 10. The distribution is left-skewed rather than right-skewed: most developers concentrate in the 70–90 range, with the mode bin at [70, 80) containing 11 developers, [80, 90) containing 7, and [90, 100) containing 7. Only 1 developer falls below 60 (minimum = 59.0), and only 2 developers fall in the [60, 70) range.

The weakest dimension by mean normalized score is Delivery (rb\_entrega, mean = 72.4), followed by Flow Efficiency (rb\_flow, mean = 84.4). Anti-Rework (96.9) and Review Quality (94.8) are near-ceiling on average, suggesting that in this cohort, process-health dimensions are reasonably healthy but delivery throughput and flow discipline remain the primary improvement levers.

### 5.6 RQ4 — IEF–IED Divergence as Diagnostic Signal

Three developers in the synthetic cohort exhibit |Δ IEF–IED| > 15 using role-specific NDS: DEV006 (Δ = 18.2), DEV009 (Δ = 15.6), and DEV021 (Δ = 15.5). These cases represent qualitatively distinct coaching scenarios, summarized in Table 4.

**Table 4. Developers with IEF–IED Divergence Δ > 15 (role-specific NDS).**

| Developer | Team | IEF | IED | Δ | Direction | Root Cause |
|-----------|------|-----|-----|---|-----------|------------|
| DEV006 | W1NNER | 46.9 | 65.1 | 18.2 | IEF < IED | VEL = 100 (fast), QUA = 100 (zero defects); IED boosted by excellent process despite low NDS/EEE |
| DEV009 | W1NNER | 92.3 | 76.7 | 15.6 | IEF > IED | VEL = 21.7 (slow: LT = 21.4 days vs. group median 4.66); high delivery throughput masked by slow cycle time |
| DEV021 | BeFinance | 57.0 | 72.5 | 15.5 | IEF < IED | VEL = 100 (fast), moderate QUA; IED elevated by velocity even with below-average NDS |

**DEV009** presents the canonical case for IEF > IED: Score Complexity = 24, Flow Efficiency = 74.4% — strong delivery throughput by volume — but a median lead time of 21.4 days against a group median of 4.66 days yields VEL = 21.7, pulling IED to 76.7 despite IEF = 92.3. The Δ = 15.6 diagnostic flags a specific intervention: cycle time reduction (smaller batches, reduced WIP, or task decomposition), rather than delivery volume improvement.

**DEV006** illustrates the opposite failure mode: IEF < IED because VEL = 100 and QUA = 100 inflate IED beyond the delivery capacity signal. IEF = 46.9 reflects genuinely low NDS (Score Complexity = 9, below median) and moderate EEE. The Δ = 18.2 alert prevents this developer from receiving misleading positive feedback based on IED alone; the coaching conversation should focus on delivery throughput.

**Figure 4 (description).** A scatter plot positions all 28 developers on IED (x-axis) versus IEF (y-axis), with the diagonal line y = x as reference. Red diamond markers denote Δ > 15. The three flagged developers are visible: DEV009 in the upper-left region (high IEF, lower IED), DEV006 and DEV021 in the lower-right region (lower IEF, higher IED). The majority of developers cluster near the diagonal, indicating that for most developers, VEL and QUA do not substantially distort the delivery signal.

### 5.7 QUA Bayesian Smoothing Effects

The Bayesian correction has negligible effect for developers with ≥ 15 deliveries (|ΔQUA| < 3 pp in all cases) but produces substantial corrections for low-sample developers. Table 5 reports the five largest corrections in the synthetic cohort.

**Table 5. QUA Correction from Bayesian Smoothing (α=0.5, β=9.5).**

| Developer | Deliveries | Defects | QUA Raw | QUA Bayes | Δ QUA | ΔIED |
|-----------|-----------|---------|---------|-----------|-------|------|
| DEV024 | 7 | 6 | 14.3 | 61.8 | +47.5 | +4.75 |
| DEV025 | 7 | 3 | 57.1 | 79.4 | +22.3 | +2.23 |
| DEV026 | 8 | 3 | 62.5 | 80.6 | +18.1 | +1.81 |
| DEV023 | 9 | 3 | 66.7 | 81.6 | +14.9 | +1.49 |
| DEV010 | 4 | 1 | 75.0 | 89.3 | +14.3 | +1.43 |

DEV024 (6 defects in 7 deliveries) represents an extreme case: raw QUA = 14.3 would classify this developer as "Critical" on the quality dimension, inflating the IED penalty by 0.10 × (85.7 − 38.2) = 4.75 points. The Bayesian estimate of 61.8 — "this developer has an estimated 38.2% failure demand rate, not 85.7%" — is more statistically defensible for a sample of 7. It should be noted that Bayesian smoothing does not excuse high defect rates; it prevents single-sample noise from dominating the composite, while the raw QUA column remains available for audit.

The IED impact of Bayesian smoothing is bounded at 0.10 × 47.5 ≈ 4.75 points for the most extreme case. For the median developer in the synthetic cohort (12 deliveries), the expected correction is less than 2 points.

### 5.8 ICC — Knowledge Concentration per Team

Table 6 reports ICC values for all five teams. Raw HHI values exceeding 0.25 are observed for BeFinance, Data, and Infra. However, normalized ICC (corrected for team size via 1/N minimum) shows that all five teams are in the low-concentration range (ICC_norm < 0.10), indicating that the raw HHI elevation for small teams (Infra: N=3; Data: N=4) is primarily a mathematical artifact of team size rather than genuine concentration.

**Table 6. ICC (HHI) per Team — Commit Concentration.**

| Team | N | Commits | ICC (HHI) | ICC Norm. | Classification |
|------|---|---------|-----------|-----------|----------------|
| W1NNER | 9 | 484 | 0.122 | 0.012 | Distributed ✓ |
| S1NC | 7 | 445 | 0.167 | 0.028 | Distributed ✓ |
| BeFinance | 5 | 233 | 0.271 | 0.089 | Moderate |
| Data | 4 | 222 | 0.271 | 0.029 | Distributed ✓ |
| Infra | 3 | 149 | 0.362 | 0.043 | Distributed ✓ |

BeFinance presents the only team with meaningfully elevated ICC Norm. (0.089), driven by DEV020's 92 commits out of a team total of 233 (39.5% share). While this does not yet cross the threshold for "Concentrated" classification (ICC_norm > 0.15, our recommended threshold for small teams), it signals an emerging knowledge concentration risk that warrants monitoring. Specifically, DEV020's departure would reduce the team's commit capacity by approximately 40% in the short run, a truck-factor-equivalent risk.

The finding that raw HHI > 0.25 for small teams (Infra, Data) without corresponding ICC Norm. elevation highlights a key methodological point: raw HHI comparisons across teams of different sizes are misleading. ICC Norm. is the appropriate organizational risk indicator.

---

## 6. Discussion

### 6.1 Absolute vs. Relative Normalization

The choice of absolute benchmark normalization over relative approaches (z-scores, percentile ranks) was validated in preliminary experiments during framework development. When z-score normalization was applied to a 5-developer pilot team, all five developers received near-zero scores on the Delivery dimension despite absolute Score Complexity values ranging from 8 to 26 — simply because the within-team variance was smaller than the normalization reference. The resulting radar charts were visually identical, rendering the visualization useless for coaching. Absolute normalization preserves external validity: a developer scoring rb\_flow = 60 is operating at 60% of the Anderson [4] benchmark regardless of peer performance.

The role-specific P75 extension (Section 3.9) introduces a limited form of within-role relative reference for the Delivery dimension, while retaining the absolute external validity for all other dimensions. This hybrid design reflects the practical reality that complexity delivery targets are domain- and role-specific, while process health targets (rework, conformance, flow efficiency) carry external validity across roles. Future work should explore whether separate role-specific absolute benchmarks can be derived from industry surveys (e.g., from Jørgensen's [8] dataset disaggregated by role type).

### 6.2 Flow Efficiency as an Individual-Level Metric

Flow efficiency is traditionally operationalized as a team-level metric, measuring the proportion of total elapsed time in which work items are actively progressed [4]. Its application at the individual level in FlowPMO — defined as items\_delivered / items\_pulled within the evaluation period — is a deliberate adaptation that sacrifices the temporal resolution of the original construct in exchange for alignment with the unit of analysis. The results in Section 5.3 support the usefulness of this adaptation: individual-level flow efficiency distinguishes work patterns (WIP discipline, delivery focus) in a way that raw commit counts do not.

The FE Ajustada correction (Section 3.6) addresses the most serious structural threat to this operationalization: cross-period carry-over inflating the numerator. The finding that WIP Residual > 4 items is associated with 17.8 pp lower Flow Efficiency (Section 5.3) is consistent with Little's Law–derived predictions that throughput decreases as WIP accumulates beyond team capacity, and suggests that WIP limit policies would be the most direct intervention for low-FE developers.

### 6.3 IED and IEF as Coaching Instruments

The IED–IEF decomposition operationalizes a distinction that managers frequently encounter but rarely have instrumented: the difference between "this developer delivers a lot" (IEF) and "this developer delivers a lot, quickly, and with quality" (IED). The cases in Section 5.6 illustrate two failure modes that are invisible in either index alone:

1. **IEF > IED (VEL penalty)**: high delivery throughput masked by long cycle times. The coaching conversation should focus on batch size reduction and WIP management, not delivery volume.
2. **IEF < IED (process bonus)**: below-average delivery volume compensated by excellent speed and quality. The composite IED gives a misleading positive signal; the IEF provides a more accurate assessment of delivery capacity.

Both scenarios are common in practice and often lead to misaligned performance conversations. The Δ > 15 threshold flags the 10–15% of developers where the IEF and IED give materially different coaching directions. For the remaining 85–90% (|Δ| ≤ 15), the two indices are sufficiently aligned that either can guide the conversation.

### 6.4 Practical Implications

The Score Benchmark gap analysis provides a structured entry point for one-on-one coaching conversations. A developer with SB = 70 and a specific weakness in rb\_conformance (e.g., 55 out of 100) receives a concrete, actionable signal: their process behavior deviates from the normative workflow in a measurable way, and the conformance gap can be investigated using the process mining trace directly within the FlowPMO dashboard. This is qualitatively different from being told "your velocity was below the team average" — a comparative signal that provides no information about the mechanism of underperformance.

The role-segmented views (TL vs. Dev) prevent cross-role comparisons that would distort incentives. If TLs were evaluated on the same Delivery benchmark as individual contributors, rational optimization would push them toward reducing code-review and mentoring time to inflate item throughput — precisely the behavior that degrades team-level quality over time.

### 6.5 Bayesian Shrinkage and the Limits of Small-Sample Scoring

The QUA correction results (Section 5.7) highlight a broader principle applicable to all rate-based metrics in small-team evaluation: any ratio with a denominator below approximately 15 observations is a poor estimator of the underlying rate, and should be regularized toward a prior. The Beta-Binomial conjugate framework applied to QUA is a principled instance of this regularization. In principle, EEE (completion rate) and even the raw P75-based NDS score are susceptible to similar instability when the cohort is small; future work should explore Bayesian formulations for all composite sub-indices.

A practical limitation of the current implementation is that the prior parameters (α = 0.5, β = 9.5) are fixed and not calibrated to the specific organization's historical defect rate distribution. An empirically calibrated prior — for instance, α/β derived from the organization's average failure demand across previous quarters — would be more informative and less subject to the criticism that the prior is arbitrarily chosen.

### 6.6 ICC as an Organizational Risk Signal

The ICC analysis in Section 5.8 reveals that raw HHI is a misleading cross-team comparator when team sizes differ substantially. The normalized ICC corrects for this, but introduces a different problem: very small teams (N = 3) have a high minimum 1/N value (0.33), making it mathematically difficult for them to show ICC_norm > 0.15 even when one developer dominates. Organizations with many small teams may need role-adjusted ICC variants that account for expected contribution asymmetries (e.g., a Tech Lead is expected to commit less than a full-stack developer).

The BeFinance result (ICC_norm = 0.089, one developer contributing 39.5% of commits) illustrates a practical use case: the ICC is not itself an alarm but an early-warning trigger for further investigation. Managers who observe ICC_norm rising across consecutive quarters in the same team, combined with a KCR (Knowledge Concentration Risk) indicator from the truck-factor analysis already present in FlowPMO, have a stronger basis for staffing decisions (cross-training, mentoring, or rotation) than from either signal alone.

### 6.7 Limitations of Synthetic Data

The synthetic dataset is generated from distributions parameterized by literature benchmarks rather than empirical calibration from the specific organizational contexts in which FlowPMO is deployed. Several limitations follow. First, the covariance structure between metrics is largely imposed by construction, which inflates some correlations relative to what would be observed in real data. Second, the log-normal distribution used for lead time may not match the actual distribution of a given team. Third, the synthetic cohort was designed to represent a healthy-to-moderate productivity range; teams experiencing extreme underperformance would likely exhibit different distributional properties. Fourth, the absence of cross-period events in the synthetic dataset means the FE Ajustada correction could not be empirically evaluated in this study; its validation requires longitudinal production data.

---

## 7. Threats to Validity

**Construct validity.** The metrics operationalized in FlowPMO are proxies for underlying productivity constructs. Items delivered is a proxy for value delivery, not value delivered: an item may be delivered promptly but fail to generate user value. Score Complexity captures effort but not impact. As Kitchenham [13] notes, the gap between measured proxies and latent quality constructs is a fundamental and irreducible challenge in software measurement. We mitigate this by grounding all metrics in prior literature that has validated their proxy relationships. The IED and IEF introduce additional construct validity concerns: the component weights (0.40/0.30/0.20/0.10 for IED; 0.70/0.30 for IEF) are theoretically motivated but empirically unvalidated.

**Internal validity.** The evaluation uses synthetic rather than empirical data. Correlations observed in Section 5 are plausible but not necessarily representative of any specific organization's data-generating process. In particular, the finding that commits correlate only weakly with Score Benchmark (r = 0.36) may reflect our simulation design rather than an intrinsic property of the relationship in practice.

**External validity.** FlowPMO's data ingestion assumes Jira (issue tracking) and Bitbucket (version control and CI/CD). Organizations using GitHub, GitLab, Azure DevOps, or Linear would require adapter development. The benchmark values (e.g., Flow Efficiency ≥ 80%, Conformance Quality ≥ 75%) are drawn from studies that may not generalize to all domains. The Bayesian prior (α = 0.5, β = 9.5) was chosen to reflect a generic software development defect rate; it is not calibrated to the evaluation cohort and may over- or under-regularize in contexts with substantially different failure demand distributions.

**Conclusion validity.** The Score Benchmark aggregation assigns equal weight to all five dimensions. There is no empirical basis for this choice. The IED weight vector (0.40/0.30/0.20/0.10) reflects theoretical arguments (delivery is the primary signal, completion rate is secondary, velocity and quality are tertiary modifiers) but has not been validated against outcome data. The euclidean distance metric treats shortfalls symmetrically across all dimensions. Weighted distance functions and their calibration are identified as the highest-priority item for future work.

---

## 8. Conclusion

This paper presented FlowPMO, a framework and open-source dashboard for multidimensional developer productivity measurement. Beyond the original five SPACE-inspired dimensions and Score Benchmark, the extended framework introduces IED, IEF, IEF–IED Divergence, role-fair NDS benchmarking, Bayesian QUA smoothing, FE Ajustada, and team-level ICC — collectively addressing eight distinct measurement validity threats identified in the literature and in production deployment.

Evaluation on a reproducible synthetic dataset of 28 developers (Q3 2024, seed = 42) produced four principal findings.

**RQ1**: Commit count alone correlates weakly with Score Benchmark (r = 0.36) and even more weakly with IED (r = 0.31). The multidimensional composite captures variance invisible to single metrics, illustrated concretely by two developers with similar commit counts differing by nearly 10 SB points due to divergent rework and flow efficiency profiles.

**RQ2**: While the aggregate Flow Efficiency–Conformance Quality correlation is weak (r = 0.15), WIP accumulation is a strong moderating variable: high-WIP developers exhibit Flow Efficiency 17.8 pp lower than low-WIP developers, with rework acting as a common cause of both low flow efficiency and low conformance.

**RQ3**: Role-specific P75 benchmarking reduces the NDS gap between Tech Leads and individual contributors from 42.3 to 5.7 points, and the IED gap from 16.9 to 3.7 points — a correction large enough to qualitatively change the coaching signal for 7 developers in the synthetic cohort. This finding motivates role-fair benchmarking as a default configuration in all deployment contexts.

**RQ4**: IEF–IED Divergence exceeds 15 points for 3 of 28 developers (10.7%), each representing a distinct coaching scenario: one developer whose high delivery throughput is masked by slow cycle time (IEF > IED), and two whose strong process metrics compensate for below-average volume (IEF < IED). In each case, the Δ diagnostic identifies the specific component requiring intervention, directing coaching effort more precisely than either composite index alone.

Complementary findings: Bayesian QUA smoothing produces corrections of up to 47.5 pp for the most extreme low-sample case, with bounded IED impact (≤ 4.75 points). ICC analysis reveals that BeFinance has the highest normalized commit concentration (ICC_norm = 0.089, one developer contributing 39.5% of team commits), warranting cross-training investment. Raw HHI without normalization systematically overestimates concentration risk for small teams.

**Future work** will pursue five directions: (1) empirical calibration of IED and IEF component weights using longitudinal production data from real development teams, with LGPD-compliant anonymization; (2) dimension weighting via the Analytic Hierarchy Process, incorporating stakeholder elicitation from engineering managers; (3) integration adapters for GitHub, GitLab, and Azure DevOps pipelines; (4) organization-specific Bayesian prior calibration using rolling defect-rate history; and (5) longitudinal evaluation of the FE Ajustada correction using real cross-period WIP data to quantify its frequency and magnitude in production deployments.

---

## Notes

<sup>1</sup> The FlowPMO framework and the synthetic data generation script (`paper/generate_synthetic_data.py`, seed = 42) are available at [https://github.com/rodrigoalmeidadeoliveira/flow-pmo](https://github.com/rodrigoalmeidadeoliveira/flow-pmo). All results reported in this paper can be reproduced by executing `python paper/generate_synthetic_data.py` from the repository root.

---

## References

[1] T. DeMarco and T. Lister, *Peopleware: Productive Projects and Teams*, 2nd ed. Dorset House, 1999.

[2] N. Forsgren, M.-A. Storey, C. Maddila, T. Zimmermann, B. Houck, and J. Butler, "The SPACE of Developer Productivity," *ACM Queue*, vol. 19, no. 1, pp. 20–48, Mar. 2021.

[3] B. Kitchenham, S. L. Pfleeger, and N. Fenton, "Towards a Framework for Software Measurement Validation," *IEEE Transactions on Software Engineering*, vol. 21, no. 12, pp. 929–944, 1995.

[4] D. J. Anderson, *Kanban: Successful Evolutionary Change for Your Technology Business*. Blue Hole Press, 2010.

[5] S. M. A. Shah, F. Palomba, D. A. d. Costa, and A. E. Hassan, "An Empirical Study on the Relationship Between Rework and Technical Debt," in *Proc. 39th IEEE International Conference on Software Maintenance and Evolution (ICSME)*, Bogotá, Colombia, 2023, pp. 1–12.

[6] J. Caldeira, J. A. Pereira, R. Spínola, and M. Zenha-Rela, "Conformance Quality in Software Development: A Process Mining Approach," in *Proc. 1st International Conference on Process Mining (ICPM)*, Aachen, Germany, 2019, pp. 121–128.

[7] N. Fenton and S. L. Pfleeger, *Software Metrics: A Rigorous and Practical Approach*, 2nd ed. PWS Publishing, 1997.

[8] M. Jørgensen, "A Review of Studies on Expert Estimation of Software Development Effort," *Journal of Systems and Software*, vol. 70, no. 1–2, pp. 37–60, 2004; see also M. Jørgensen, "What We Know About Software Development Effort Estimation," *IEEE Software*, vol. 31, no. 2, pp. 37–40, 2014.

[9] N. Forsgren, J. Humble, and G. Kim, *Accelerate: The Science of Lean Software and DevOps: Building and Scaling High Performing Technology Organizations*. IT Revolution Press, 2018.

[10] W. M. P. van der Aalst, *Process Mining: Data Science in Action*, 2nd ed. Springer, 2016.

[11] J. Caldeira, R. Spínola, J. A. Pereira, and M. Zenha-Rela, "Mining Software Development Rework Patterns Using Process Mining Techniques," *Information and Software Technology*, vol. 135, p. 106565, 2021.

[12] A. F. Nogueira and M. Z. Rela, "Continuous Integration Pipeline Quality: An Empirical Study of Defect Escape Rates and Build Stability," *Information and Software Technology*, vol. 161, p. 107256, 2023.

[13] B. Kitchenham, "Procedures for Performing Systematic Reviews," Keele University, Keele, UK, Tech. Rep. TR/SE-0401, 2002.

[14] A. Gelman, J. B. Carlin, H. S. Stern, D. B. Dunson, A. Vehtari, and D. B. Rubin, *Bayesian Data Analysis*, 3rd ed. CRC Press, 2013.

[15] P. Laplace, *Théorie Analytique des Probabilités*. Courcier, Paris, 1812. (Laplace's rule of succession as regularization.)

[16] F. Ricca, M. Di Penta, M. Torchiano, P. Tonella, and M. Ceccato, "The Role of Experience and Ability in Comprehension Tasks Supported by UML Stereotypes," *Proc. 31st International Conference on Software Engineering (ICSE)*, Vancouver, Canada, 2009; see also C. Ferme, N. Leger, and N. Anquetil, "Who Is Going to Maintain This Code? Supporting Truck Factor Analysis," *Proc. International Workshop on Empirical Software Engineering in Practice*, 2019.

[17] U.S. Department of Justice and Federal Trade Commission, *Horizontal Merger Guidelines*, § 5.3 (HHI Thresholds), 2010.

[18] B. Kitchenham and E. Mendes, "A Comparison of Cross-Company and Within-Company Effort Estimation Models for Web Applications," *IEEE Transactions on Software Engineering*, vol. 30, no. 11, pp. 722–737, Nov. 2004.

[19] R. Flournoy, C. Treude, and B. Adams, "Cycle Time as a Proxy for Developer Productivity: An Empirical Study," *Empirical Software Engineering*, vol. 30, no. 2, 2025.
