# Requested Changes to Audit Security Report

## Section: 1.1.1 Overall Audit Coverage and Classification

- **Modify**: Change "Tier 1" to "Tier 1 Plus"
- **Modify**: Change "Quantstamp and Zellic" to "Quantstamp, Zellic, and Trail of Bits"
- **Modify**: Change "Thirteen distinct security audits" to "Fifteen distinct security audits"
- **Modify**: Change "USDTB and sENA" to "USDTB, sENA, and the latest V3 contracts"
- **Modify**: Change "Approximately 16 medium-severity findings" to "Approximately 18 medium-severity findings"
- **Modify**: Change "four from Quantstamp" to "five from Quantstamp"
- **Modify**: Change "two from Code4rena invitational" to "three from Code4rena invitational"
- **Modify**: Change "Approximately 40 low or informational findings" to "Approximately 45 low or informational findings"

## Section: 1.1.2 Detailed Audit Breakdown

- **Modify**: In Zellic Audit, change deployment date from "2023-08-15" to "2023-08-20"
- **Modify**: In Quantstamp V1 Audit Key Findings by Severity, change "Four medium-severity findings on reentrancy risks in staking rewards." to "Five medium-severity findings on reentrancy risks in staking rewards."
- **Modify**: In Pashov V2 Audit, change deployment date from "2024-05-25" to "2024-05-30"
- **Modify**: In Pashov sENA Audit, change audit date from "2024-09-02" to "2024-09-05"
- **Modify**: In Pashov sENA Audit Key Findings by Severity, change "Three low on role assignments and precision" to "Four low on role assignments and precision"
- **Modify**: In Code4rena Invitational Audit, change prize pool from "$20,000 USDC" to "$22,000 USDC"
- **Modify**: In Code4rena Invitational Audit Key Findings by Severity, change "Two unique medium severity vulnerabilities" to "Three unique medium severity vulnerabilities"
- **Add**: New medium finding M-03 in Code4rena Invitational Audit: "M-03: Additional edge case in redemption flow allowing potential front-running"
- **Add**: Resolution detail for M-03 in Code4rena Invitational Audit: "M-03 resolved with additional validation checks"
- **Add**: New audit entry for Trail of Bits V3 Audit: "Trail of Bits V3 Audit" dated 2025-09-15, scope "Version 3 protocol contracts and cross-chain bridge implementation", Key Findings: "No critical or high severity vulnerabilities. Two medium findings on bridge security and oracle dependencies. Eight low findings on gas optimizations and edge cases. Four informational recommendations for code clarity", Resolution Details: "Both medium findings addressed via PRs #245-#247. Low findings partially implemented. All changes deployed on 2025-09-30"
- **Modify**: In Chaos Labs Economic Risk Analysis Key Findings by Severity, change "Maximum collateral drawdown historical backtest 4.3% in September 2022" to "Maximum collateral drawdown historical backtest 4.8% in September 2022"
- **Modify**: In Chaos Labs Economic Risk Analysis Key Findings by Severity, change "Initial reserve fund recommendation $33 million" to "Initial reserve fund recommendation $38 million"

## Section: 1.1.3 Auditor Reputation Analysis

- **Modify**: Change Pashov audits from "Over 50 audits" to "Over 60 audits"
- **Modify**: Change Code4rena from "483 audits completed" to "520 audits completed"
- **Add**: New entry for Trail of Bits: "Trail of Bits is classified as top-tier. Premier security firm with extensive blockchain experience."

## Section: 1.1.4 Competitive Audit Contest Analysis

- **Modify**: Change Code4rena invitational prize pool from "$20,000" to "$22,000"
- **Modify**: Change "Two medium on access control edge cases" to "Three medium on access control edge cases"

## Section: 1.2.1 Bug Bounty Program Status and Specifications

- **Modify**: Change maximum payout from "$3,000,000" to "$3,500,000"
- **Modify**: Change high-severity payout from "$75,000" to "$85,000"
- **Modify**: Change last update date from "2025-05-20" to "2025-06-15"

## Section: 1.2.2 Historical Activity and Payouts

- **Modify**: Change vault balance from "$3,000,000" to "$3,500,000"
- **Modify**: Change transaction history from "$3M deposit. No outflows indicating no payouts" to "$3M deposit. Additional $500k deposit in July 2025. No outflows indicating no payouts"
- **Modify**: Change 30-day average from "$3,000,000" to "$3,500,000"

## Section: 2.1.1 Smart Contract Security Features

- **Add**: New sentence after "And USDTB contracts in 2024-10": "Version 3 contracts were deployed in 2025-09 following the Trail of Bits audit."

## Section: 2.3.1 October 2025 De-Pegging Incident

- **Modify**: Change "USDe fell to a low of approximately $0.65" to "USDe fell to a low of approximately $0.62"
- **Modify**: Change "That triggered over $19 billion in liquidations" to "That triggered over $21 billion in liquidations"
- **Modify**: Change "Processing over $2 billion in redemptions" to "Processing over $2.4 billion in redemptions"
- **Modify**: In the paragraph beginning "Comprehensive on-chain data confirming", change "Over $2B and transaction count over 10k" to "Over $2.4B and transaction count over 11k"
- **Modify**: Change all three occurrences of "$66 million" overcollateralization to "$72 million":
  - "Post-event overcollateralization reached approximately $66 million" to "$72 million"
  - "By approximately $66 million on a $9.65 billion supply" to "$72 million"
  - "Confirming that USDe remained overcollateralized by approximately $66 million" to "$72 million"
  - "Only secondary reports of the approximately $66M overcollateralization exist" to "$72M"
- **Modify**: Change "The de-pegging on Binance lasted for approximately 90 minutes" to "The de-pegging on Binance lasted for approximately 105 minutes"
- **Modify**: Change "With a more severe 40-minute window between 21:36 and 22:16 UTC" to "With a more severe 50-minute window between 21:30 and 22:20 UTC"
- **Modify**: Change "Binance announced it would provide $283 million in compensation" to "Binance announced it would provide $295 million in compensation"

## Section: 3.1.2 Detailed Benchmarking Matrix

- **Modify**: In the final summary paragraph, change "13 audits" to "15 audits"
- **Modify**: In the final summary paragraph, change "$3,000,000 Immunefi bug bounty" to "$3,500,000 Immunefi bug bounty"

## Section: 3.2.1 Derived Industry Standard

- **Modify**: Change "Ethena's 13 audits in 18 months" to "Ethena's 15 audits in 20 months"

## Section: 3.3.1 Codebase Analysis

- **Modify**: Change test coverage from "87.56%" to "89.2%"

## Section: 3.4.1 Key Security Advantages

- **Modify**: Change "13 distinct audits" to "15 distinct audits"
- **Modify**: Change "$3 million maximum bounty" to "$3.5 million maximum bounty"

## Section: 4.1 Consolidated Timeline of Events

- **Modify**: In the 2023-07-03 entry, change "Zellic audit of version 1 protocol contracts completed. No critical or high severity vulnerabilities. One medium-severity issue. One low-severity issue. Several gas optimizations. All reviewed and patched during the audit cycle." to "Zellic audit of version 1 protocol contracts completed. No critical or high severity vulnerabilities. One medium-severity issue. One low-severity issue. Several gas optimizations. Three low findings on input validation event emissions. Six informational gas optimizations."
- **Modify**: Change Zellic deployment date from "2023-08-15" to "2023-08-20"
- **Modify**: In the 2023-10-18 entry, change "Four medium-severity findings" to "Five medium-severity findings"
- **Modify**: Change Pashov V2 deployment date from "2024-05-25" to "2024-05-30"
- **Add**: New entry for 2024-07-15: "Bug bounty vault increased to $3.5M with additional deposit."
- **Modify**: Change Pashov sENA date from "2024-09-02" to "2024-09-05"
- **Modify**: Change Code4rena invitational prize from "$20,000" to "$22,000"
- **Modify**: Change Code4rena invitational findings from "Two unique medium" to "Three unique medium"
- **Modify**: Change the 2025-05-20 entry date to 2025-06-15 (entry moves from before 2025-05-31 to after 2025-05-31 in the timeline)
- **Add**: New entry for 2025-09-15: "Trail of Bits completes V3 protocol audit. Two medium findings addressed."
- **Add**: New entry for 2025-09-30: Modify existing entry to include "V3 contracts deployed" after "To add pre-transaction simulation and policing capabilities"
- **Modify**: Change vault balance from "$3M" to "$3.5M" in the 2025-10 entry
- **Modify**: Change de-pegging details in 2025-10-10 21:36 UTC entry: change "21:36 UTC" to "21:30 UTC" and "90 minutes" to "105 minutes"
- **Modify**: Change de-pegging low from "$0.65" to "$0.62" in 2025-10-11 entry
- **Modify**: Change liquidations from "$19 billion" to "$21 billion" in 2025-10-10 entry
- **Modify**: Change redemptions from "$2 billion" to "$2.4 billion" in 2025-10-11 entry
- **Modify**: Change all three overcollateralization references from "$66M" to "$72M" in the 2025-10-11 entries
- **Modify**: Change Binance compensation from "$283M" to "$295M" in 2025-10-12 entry

## Section: 4.2.1 Resolved Conflicts

- **Modify**: Change "Resolution is 13 audits" to "Resolution is 15 audits"
- **Modify**: Change prize pool resolution from "$20,000" to "$22,000"
- **Modify**: Change de-pegging duration from "90 minutes" to "105 minutes"
- **Modify**: Change severe window from "40 minutes at 21:36-22:16" to "50 minutes at 21:30-22:20"

## Section: 4.2.2 Unresolved Conflicts

- **Modify**: Update de-pegging duration reference from "approximately 90 minutes" and "40-minute window 21:36-22:16 UTC" to "approximately 105 minutes" and "50-minute window 21:30-22:20 UTC"

## Section: 4.2.3 Potentially Incorrect Information

- **Modify**: Update de-pegging figures to reference "$0.62 price low" instead of "$0.65 price low"
- **Modify**: Update market liquidations to reference "$21 billion liquidations" instead of "$19 billion liquidations"
- **Modify**: Update timeline references from "40/90 minutes" to "50/105 minutes"
- **Modify**: Update UTC time range from "21:36-22:16 UTC, 40 min" to "21:30-22:20 UTC, 50 min"
- **Modify**: Change overcollateralization reference from "$66M" to "$72M"

## Section: 4.3.1 Industry and Market Trends

- **Modify**: Change bug bounty example from "$3,000,000" to "$3,500,000"
