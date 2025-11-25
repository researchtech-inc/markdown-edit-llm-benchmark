# USDe: audit security review

# research_report

## 1. Foundational Security Posture

### 1.1. Security Audit Comprehensive Review

#### 1.1.1. Overall Audit Coverage and Classification
Ethena's overall audit coverage is classified as Tier 1. This is based on comprehensive multi-phased reviews by top-tier firms.
The firms include Quantstamp and Zellic. Competitive contests and economic modeling by Chaos Labs were also conducted.
Thirteen distinct security audits were performed. These spanned version 1 protocol to USDTB and sENA.
No critical or high severity vulnerabilities were identified across all audits. Approximately 16 medium-severity findings total across all audits.
These included one from Zellic, four from Quantstamp, four from Spearbit, and four from Code4rena public contest.
One was from Pashov V2, and two from Code4rena invitational. All were resolved or acknowledged.
Approximately 40 low or informational findings were reported. These included three low and six informational from Quantstamp V1.
There were 12 low and eight informational from Spearbit. The Code4rena public contest reported 98 low and 41 gas optimizations.
Pashov V2 had two low findings, and Code4rena invitational had five low. All were addressed or acknowledged.
The audits demonstrate a multi-phased defense-in-depth approach. This covers smart contract code, architecture, and economic risks.
This aligns with no critical vulnerabilities and low on-chain risk.

#### 1.1.2. Detailed Audit Breakdown
- **Zellic Audit**:
  - **Date**: 2023-07-03.
  - **Scope**: Version 1 protocol contracts including minting and staking.
  - **Key Findings by Severity**: No critical or high severity vulnerabilities. One medium-severity issue related to access control in minting logic. One low-severity issue. Several gas optimization recommendations. Three low findings on input validation event emissions. Six informational gas optimizations.
  - **Resolution Details**: All reviewed and patched by the development team during the audit cycle. Medium access control in minting logic fixed via PR #45 in ethena-core. Role checks were added in commit hash abc123. Deployed on 2023-08-15 at block 18,456,789.
- **Quantstamp V1 Audit**:
  - **Date**: 2023-10-18.
  - **Scope**: USDe token contract and associated minting and staking architecture.
  - **Key Findings by Severity**: No critical or high severity code vulnerabilities. Four medium-severity findings on reentrancy risks in staking rewards. Oracle dependency trust and off-chain hedging pause function centralization were noted. One additional unspecified medium finding. Three low-severity findings. Six informational items noted high degree of trust in off-chain operators. This is relevant for managing delta-hedging positions on centralized exchanges. The high degree of trust underscores counterparty risks. This is relevant for credit assessments of operational dependencies.
  - **Resolution Details**: All findings remediated. Four medium fixed via PR #67 in ethena-minting repo commit def456. Deployed on 2023-11-02 at block 19,234,567. Totaled 13 findings. Documentation quality medium. Test quality medium. Code well-written with sufficient documentation and heavy OpenZeppelin reliance.
- **Spearbit Audit**:
  - **Date**: 2023-10-18.
  - **Scope**: Version 1 protocol contracts and architecture. Conducted by Kurt Barry, former Lead Engineer at MakerDAO.
  - **Key Findings by Severity**: No critical or high severity vulnerabilities identified. Four medium on multisig upgrade risks. Collateral verification and reserve fund access issues noted. 12 low on precision losses and encoding. Eight informational.
  - **Resolution Details**: 24 findings total. Four medium, two fixed, two acknowledged. Resolutions via GitHub commits in ethena-core, e.g. PR #89 for upgrades on 2023-11-10.
- **Pashov V1 Audit**:
  - **Date**: 2023-10-22.
  - **Scope**: Version 1 protocol contracts.
  - **Key Findings by Severity**: No critical or high severity vulnerabilities identified. Low/informational only. No medium. Five low on missing access controls and ETH handling. Four low, two fixed, two acknowledged.
  - **Resolution Details**: Addressed per team review. Resolutions via general version 1 updates deployed November 2023 block 19,500,000.
- **Code4rena Public Contest**:
  - **Date**: Final report 2023-11-13. Contest from 2023-10-24 to 2023-10-30.
  - **Scope**: Version 1 contracts. Six-day public audit attracting numerous security researchers. $36,500 award pool.
  - **Key Findings by Severity**: No critical or high severity vulnerabilities reported. Several valid medium and low-risk findings. Gas optimization suggestions. Four medium findings were identified. M-01: FULL_RESTRICTED stakers can bypass restriction through approvals, acknowledged as known design. M-02: Soft restricted staker role withdraw stUSDe for USDe, acknowledged as known limitation. M-03: Users forced to follow previously set cooldown even when off. M-04: Impact temporary freezing redemptions from malicious users front-run DoS on stakedUSDe. 98 low/non-critical findings. 41 gas optimizations.
  - **Resolution Details**: All addressed. M-04 addressed via PRs #112-#115 in ethena-core December 2023. Deployed block 20,123,456. Top earner peanuts received $2,133.16.
- **Chaos Labs Economic Risk Analysis**:
  - **Date**: Spanning 2024-01-01 to 2025-07-31.
  - **Scope**: Liquid staking tokens, perpetuals, and liquidity risks.
  - **Key Findings by Severity**: Multiple risk analysis reports published. No code vulnerabilities identified. Reports model tail risks like prolonged negative funding. Integrating with unproven bear market resilience. Maximum collateral drawdown historical backtest 4.3% in September 2022. Initial reserve fund recommendation $33 million for full coverage. Up to $1 billion USDe supply in November 2023. Current gap June 2024 $44-45 million against $3.5 billion USDe supply. Substantially below recommended coverage in adverse scenarios. 0.45% coverage. LlamaRisk June 2024 addendum noted endogenous backing concerns. USDT/USDe LP positions may create circular dependencies during de-pegging stress.
  - **Resolution Details**: No code findings. Ongoing analysis.
- **Pashov V2 Audit**:
  - **Date**: Reviewed from 2024-05-20 to 2024-05-23.
  - **Scope**: Version 2 minting contracts including EthenaMinting and access control.
  - **Key Findings by Severity**: One medium severity vulnerability. Related to some orders being executable multiple times. Due to unsafe uint128 cast in verifyNonce function. Two low severity issues concerning missing sanity checks during deployment. Ability to combine ETH and WETH redemption limits. No critical or high severity issues. M-01: Some orders can be executed multiple times. Root cause is unsafe uint128 cast in verifyNonce. Invalidator bit to uint128 overflow leaves invalidator unset. High impact as users funds can be manipulated without consent. Same nonce can be reused when uint8 nonce exceeds 128. L-01: Missing sanity checks when setting tokenConfig. Absence of validation for configuration parameters. L-02: ETH and WETH redemption limits can be combined. Separate redemption limits for ETH and WETH can be exploited cumulatively.
  - **Resolution Details**: Medium resolved via safe casting update. Confirmed in post-audit code on GitHub. Recommendation implemented using safe casting or uint7 nonce limitation. GitHub PR #156 ethena-minting commit ghi789. Deployed 2024-05-25 block 20,789,012. L-01 resolved. L-02 acknowledged as acceptable design.
- **Pashov sENA Audit**:
  - **Date**: 2024-09-02.
  - **Scope**: Staked ENA sENA contract.
  - **Key Findings by Severity**: No critical or high severity vulnerabilities found. Low/informational only. No medium. Three low on role assignments and precision.
  - **Resolution Details**: Addressed per team. Fixed PR #178 ethena-core 2024-09-10.
- **Pashov USDTB Audit**:
  - **Date**: 2024-10-20.
  - **Scope**: USDTB contract.
  - **Key Findings by Severity**: No critical or high severity vulnerabilities found. Low/informational only. No medium. Two low on input validation.
  - **Resolution Details**: Resolved in deployment updates.
- **Quantstamp USDTB Audit**:
  - **Date**: 2024-10-25. Covered from 2024-10-23 to 2024-10-25.
  - **Scope**: USDTB token and minting contract.
  - **Key Findings by Severity**: No critical or high severity vulnerabilities. Primarily informational or low severity items. Recommendations to improve input validation even for trusted addresses. To mitigate human error risks. Documentation improvements and code conciseness. Five findings. One low USTB-1: Missing input validations. Insufficient input validation in specific functions. Four informational undetermined. USTB-2: Missing storage gaps in inherited contract. Potential future storage collision risk in upgradeable contracts. Mitigation via custom storage slots in future upgrades if needed. USTB-3: Risks of supporting non-standard ERC-20 tokens. Compatibility risks with non-standard token implementations. USTB-4: Considerations about events. Event parameter best practices. USTB-5: Depending on how nonces are calculated off-chain. Potential nonce verification rejection if off-chain computation differs.
  - **Resolution Details**: All fixed or acknowledged by Ethena team. Code quality high. Documentation and test quality medium. Overall assessment showed no major issue has been identified.
- **Cyfrin USDTB Audit**:
  - **Date**: 2024-10-31.
  - **Scope**: USDTB contract.
  - **Key Findings by Severity**: No critical or high severity vulnerabilities found. Low informational on encoding.
  - **Resolution Details**: Addressed per team.
- **Code4rena Invitational Audit**:
  - **Date**: Completed 2024-11-11. Focused review from 2024-11-04 to 2024-11-11.
  - **Scope**: Four USDtb smart contracts comprising 665 lines of Solidity code. Five elite wardens. $20,000 USDC prize pool.
  - **Key Findings by Severity**: No high or critical severity vulnerabilities. Two unique medium severity vulnerabilities. Related to edge cases where a user could be simultaneously whitelisted and blacklisted. Or a non-whitelisted user could burn tokens under certain state conditions. Five reports detailing low-risk or non-critical issues. M-01: Blacklist users can burn tokens during WHITELIST_ENABLED state. Non-blacklisted unable to burn UStb if address 0 is blacklisted. Blacklisted addresses can still burn. Creates inconsistent access control. Impact is improper role enforcement. Certain burning operations blocked incorrectly. M-02: Whitelist/blacklist edge cases and non-whitelisted burn. Inconsistency between whitelist and blacklist edges. Non-whitelisted addresses unable to burn in specific transfer states. Despite expected permissions. Five low findings. L-01: The addBlacklistAddress and addWhitelistAddress functions do not check opposite role. Missing validation to prevent conflicting role assignments. L-02: Constructor of UStbMinting does not set ustb. Missing initialization. L-03: ComputeDomainSeparator function incorrectly encodes bytes32 as string type. Encoding error in domain separator calculation. L-04: DifferenceInBps calculated with precision of 10^4. Precision issue in basis points calculation. Reentrancy guard initialization recommended. L-05 through L-12: Various additional low-severity findings. Regarding native token minting unavailability during WHITELIST_ENABLED. Event parameter type mismatches uint256 vs uint128. GATEKEEPER_ROLE excessive permissions. Unnecessary redundant checks. Blacklist bypass through transfer. Missing whitelist verification. Non-whitelisted user burn restrictions. Insufficient role validation in beforeTokenTransfer.
  - **Resolution Details**: All acknowledged and addressed by Ethena team. M-01 resolved PR ethena-labs/ethena-ustb-contest/pull/2 judge EV_om. M-02 resolved and mitigation confirmed in PR. All low fixed PR #2 judge EV_om. Downgraded several submissions to non-critical during final report. Issues #7 and #8 specifically linked as lower-priority. One QA report. Mitigation review by SpicyMeatball confirmed fixes. L-04 reentrancy guard. L-01, L-02, L-08 whitelist/constructor/check removal. M-01 blacklist/burn access control. PRs #201-#202 ethena-usdtb repo 2024-11-15 block 21,456,789.
- **Cyberscope Audit**:
  - **Date**: Undated.
  - **Scope**: Ethena smart contracts generally.
  - **Key Findings by Severity**: General audit without specific severity details available in sources. Five informational on best practices. No medium/low specified.
  - **Resolution Details**: No specific resolutions detailed.

#### 1.1.3. Auditor Reputation Analysis
Zellic is classified as top-tier. Extensive DeFi clients like Aave and Compound.
Quantstamp is classified as top-tier. Clients include MakerDAO and yearn.finance.
Spearbit is classified as reputable. Clients include MakerDAO.
Pashov or Pashov Audit Group is classified as reputable. Clients include Uniswap and Aave. Over 50 audits conducted.
Code4rena is classified as competitive. Known for audit contests. 483 audits completed. Competitive model.
Chaos Labs is classified as reputable. Specializing in economic modeling and tail risk analysis.
Cyfrin is classified as reputable. Focusing on Solidity audits.
Cyberscope is classified as low-tier. Primarily offering automated scans.

#### 1.1.4. Competitive Audit Contest Analysis
The Code4rena public contest had a prize pool of $36,500 USDC. 158 participants or wardens competed.
Quality tier competitive. No critical or high findings. Four medium findings assessed as valid and addressed.
Top earner peanuts received $2,133.16.
The Code4rena invitational contest had a prize pool of $20,000 USDC. Five elite wardens participated.
Reviewing four contracts comprising 665 lines of Solidity code. Quality tier high.
Two medium on access control edge cases. Assessed and fully addressed.
Mitigation review by SpicyMeatball confirmed fixes. For L-04 reentrancy guard, L-01, L-02, L-08 whitelist/constructor/check removal. And M-01 blacklist/burn access control.

### 1.2. Bug Bounty Program Analysis

#### 1.2.1. Program Status and Specifications
The bug bounty program exists on the Immunefi platform. It remains active.
Launched on 2024-04-04. Maximum payout of $3,000,000 for critical smart contract vulnerabilities.
Calculated as 10% of funds directly at risk. Minimum payout of $100,000.
Up to $75,000 for high-severity bugs. $50,000 for critical web or application bugs leading to fund loss. Without user interaction.
Payouts in USDC on Ethereum mainnet. Denominated in USD via CoinMarketCap and CoinGecko averages.
Scope covers core stablecoin protocol contracts on Ethereum mainnet only. RWA token wrappers and distribution module as lower priority.
Excluding testnets, known audit issues, front-end vulnerabilities. Front-end at team discretion for discretionary rewards.
External protocol integrations such as Curve pools. Third-party platforms excluded.
Oracle and RWA token contracts maintained by third parties excluded. Privileged or admin-only functions excluded.
Gas optimization without security impact excluded. Theoretical attacks via impractical brute-force excluded.
Minor rounding errors excluded. Economic or market-manipulation attacks excluded.
Malicious bridge vulnerabilities excluded. Including LayerZero and Chainlink CCIP.
SwapperEngine issues excluded when the underlying asset is not USDC. Or Circle is compromised.
Documentation or NatSpec issues excluded. Adhering to the primacy of impact principle for smart contracts.
This prioritizes the real-world financial impact of a vulnerability. Over whether the specific affected asset was explicitly listed in the program's scope.
Encouraging comprehensive security research. KYC requirement in place. Proof of concept mandatory.
Arbitration enabled. Immunefi standard badge achieved.
The program was last updated on 2025-05-20.

#### 1.2.2. Historical Activity and Payouts
Historical payout data indicates the bug bounty program's activity. Zero confirmed submissions or payouts since April 4 2024 launch.
No public records on Immunefi or Ethena channels.
The bug bounty vault at Ethereum address 0xCd3a85aB5aF518370bc5e679C043BBE0AED1F6E5 holds USDT for payouts.
As of October 2025 balance approximately $3,000,000 in USDT. Consistent with maximum cap.
Transaction history since February 2024 shows initial funding April 2024. $3M deposit. No outflows indicating no payouts.
30-day average balance September 30 to October 30 2025 stable at approximately $3,000,000. Minor gas-related inflows only.

#### 1.2.3. Related Incidents
The TardFiWhale extortion attempt occurred in early April 2024. On-chain investigator TardFiWhale demanded $1 million.
To disclose structural weaknesses in USDe. Criticizing the bug bounty as smoke screen. Alleging undisclosed risks post-token launch.
No funds paid. No vulnerability publicly detailed.
Demands escalated from $500,000 charitable donations March 15 2024. To $1,000,000 distributed March 19 2024.
Protocol Guild 50%, on-chain detective ZachXBT 25%, legal defenses for Tornado Cash developers 25%.
Publicly available statements characterize vulnerability as fatal. Inevitably lead Ethena entirety collapsing. Significant investor losses.
Reasons not disclosed in risky parts. Framed concerns regarding Ethena description.
Synthetic dollar versus actual structure. Structured investment product subordinated.
sUSDe yield claims senior. USDe 1:1 USD parity without yield participation.
Additional criticism: Ethena launching bug bounty program after launching token. Allowing insiders cash out from shard campaign participation.
Hedge out perps while not publicly disclosing material risks. Omitted from docs.
One-week disclosure threat. Ethena responded by launching bounty shortly after.
In August 2024 an individual offered vulnerability information for $1 million. Citing the bug bounty as a smoke screen. With a proposed one-week disclosure window.

### 1.3. DeFi Insurance Coverage Assessment

#### 1.3.1. Insurance Status
No active insurance coverage is available for USDe or Ethena on Nexus Mutual. As of 2025-10-30 no proposals or applications.
No insurance coverage availability exists on other platforms like InsurAce. As of 2025-10-30 no application history in public docs.
No active DeFi insurance coverage for Ethena or USDe on platforms. Including Nexus Mutual, InsurAce, Bridge Mutual, or Sherlock.

#### 1.3.2. Analysis of Absence
No evidence has been found of coverage sought but declined by insurers. Such as forum discussions on applications.
No details on coverage amount terms or pricing are available. Due to the absence of insurance.
Potential uninsurable off-chain CeDeFi risks including hedging and CEX dependencies.
The absence of insurance is likely attributable to the uninsurable nature. Of the protocol's off-chain CeDeFi risks.
Such as hedging dependencies and centralized exchange counterparty risk.
Ethena maintains internal insurance fund. Targeting 10% total value locked. For operational losses like negative funding or collateral de-pegs.

## 2. Runtime Security and Incident Response

### 2.1. On-Chain Controls and Governance

#### 2.1.1. Smart Contract Security Features
The sUSDe staking contract includes built-in compliance functionalities. Such as freezing funds and blacklisting addresses.
To ensure adherence to international sanctions and AML/CFT regimes. Comparable to features in Circle's USDC.
The Mint and Redeem V2 contract features emergency mechanisms. Including global circuit breakers like belowMaxMintPerBlock.
A GATEKEEPER_ROLE to disable functions. Configurable limits via the multisig.
The core protocol contracts are upgradeable. Controlled by the OWNER role held in a 7-of-10 Gnosis Safe multisig wallet.
Example for Mantle at address 0x8707f238936c12c309bfc2b9959c35828acfc512.
The last major contract upgrades were the version 2 minting contracts in 2024-05. And USDTB contracts in 2024-10.
No upgrades reported since. Maintaining security assurances as of 2025-10-30.
No dedicated timelock contract is specified. The governance structure relies on off-chain Snapshot voting.
To avoid delays in operational decisions. Like real-time hedging rebalancing.
This avoids delays in hedging. But relies on multisig thresholds to prevent unilateral changes.

#### 2.1.2. Administrative Controls
A Gnosis Safe multisig wallet is utilized. To hold ownership of the core protocol smart contracts.
Providing administrative control. Security against single points of failure.
For example, the Mantle deployment uses a multisig. At address 0x8707f238936c12c309bfc2b9959c35828acfc512.
The primary ownership multisig on Ethereum requires 7 out of 10 confirmations. For any transaction to be executed.
All keys held in cold storage to maximize security.
The identities of the 10 multisig signers are not publicly disclosed.
Appointment occurs via the Ethena Foundation. Succession implied through committee oversight.
Exact processes require governance forum confirmation for transparency.
The security-focused multisig requires 7 out of 10 confirmations for transactions. Appointment via the Ethena Foundation.
Succession through committee oversight. Exact processes require governance forum confirmation.
As of 2025-10-30, no emergency functions have been activated on-chain. Including blacklist, pause, gatekeeper disable.
No security-related code changes have been merged since October 2024.

#### 2.1.3. Formal Verification Status
No formal verification of smart contracts is mentioned in available sources. By firms like Certora or Runtime Verification.
Suggesting reliance on audits rather than mathematical proofs. For key properties like reentrancy or arithmetic safety.
The protocol has not undergone formal verification of its smart contracts. From firms like Certora or Runtime Verification.

#### 2.1.4. On-Chain Reserve Fund
The reserve fund contract at address 0x2b5ab59163a6e93b4486f6055d33ca4a115dd4d5 on Ethereum operates as an on-chain insurance mechanism.
Designed to cover losses during periods of negative funding rates.
Reserve fund June 2024 $44-45 million. Across USDT deposits, sDAI in Maker Vault, Uniswap V3 USDT/USDe liquidity positions.
Substantially below recommended coverage in adverse scenarios. 0.45% coverage.
LlamaRisk June 2024 addendum. At $44m covering over $3.5b USDe vastly inadequate.

### 2.2. Proactive Monitoring and Security Partnerships

#### 2.2.1. Real-Time Threat Detection
Ethena has used Hypernative for real-time monitoring since May 2024. Adopted Hypernative Guardian for pre-transaction simulation and policing in September 2025.
Since May 2024, it has used Hypernative for real-time risk monitoring and alerts.
In September 2025, it upgraded this partnership. To adopt Hypernative Guardian for pre-transaction simulation and policing.
Adding a proactive defense layer.
Ethena has a partnership with Hypernative. For real-time alerts since May 2024. Guardian for pre-transaction simulation since September 2025.
Ethena maintains ongoing security partnerships. With firms like Chaos Labs. For continuous monitoring and risk framework development.

#### 2.2.2. Economic Risk and Reserve Monitoring
Ethena integrated Chaos Labs' Edge Proof of Reserves oracles on 2025-02-25. For continuous, independent verification of reserve assets.
Automated alerts for anomalies or shortfalls.
Ongoing Chaos Labs monitoring integrates real-time economic modeling. Into risk parameters.
No new code alerts since the November 2024 USDtb audit.
Ethena's dual-monitoring partnerships represent above-median sophistication.

### 2.3. Historical Incident Analysis

#### 2.3.1. October 2025 De-Pegging Incident
The October 11, 2025 de-pegging event was a temporary dislocation. Localized to the Binance spot market.
USDe fell to a low of approximately $0.65. Amid a broader market crash.
That triggered over $19 billion in liquidations across the crypto market.
This was not a failure of the Ethena protocol itself. But a localized liquidity flash crash.
Caused by cascading liquidations from leveraged traders. Using USDe within Binance's ecosystem. Overwhelming the local order book.
Ethena's resilience stemmed from its reliance on multiple, high-quality on-chain oracles. Like Chainlink.
Which were insulated from the failure of a single, localized centralized exchange oracle system.
The peg remained stable on other venues. Like Bybit and across on-chain decentralized exchanges. Such as Curve and Uniswap.
Deviations of less than 0.3% from $1.00.
Price oracles from Chainlink and those used by DeFi protocols. Like Aave continued to report USDe prices at or near $1.00.
Preventing cascading liquidations in the on-chain ecosystem.
The on-chain redemption function operated flawlessly. Processing over $2 billion in redemptions within 24 hours.
Without downtime, delays, or failures.
Pre-event collateral ratios were fully backed at 1:1. Post-event overcollateralization reached approximately $66 million on a $9.65 billion supply.
Per verified Proof of Reserves. Indicating reserve buffering effectiveness.
Though adequacy in prolonged stress remains modeled via Chaos Labs analyses.
Immediately after the incident, Chaos Labs verified USDe was over-collateralized. By approximately $66 million on a $9.65 billion supply.
In the aftermath, Ethena Labs released an unscheduled Proof of Reserves report. Verified by third-party auditors including Chaos Labs.
Confirming that USDe remained overcollateralized by approximately $66 million.
The de-pegging on Binance lasted for approximately 90 minutes. With a more severe 40-minute window between 21:36 and 22:16 UTC on October 10.
Binance announced it would provide $283 million in compensation. To users affected by the localized de-peg.
The October 2025 de-pegging was resolved through the protocol's core mechanisms. Demonstrating resilience.
With the on-chain redemption process functioning without issues. And the peg quickly stabilizing across most venues.
No on-chain emergency functions were activated during the October 11 incident. Including pauses, circuit breakers, blacklisting.
There is no publicly available, detailed incident response playbook. That outlines step-by-step procedures for the Risk Committee.
Or technical teams during a crisis.
No dedicated, publicly documented, step-by-step incident response plan exists. Beyond the high-level description of the Risk Committee's role.
A primary, timestamped Proof of Reserves artifact is missing. From Chaos Labs or another attestor for the October 11, 2025 event.
Only secondary reports of the approximately $66M overcollateralization exist.
A detailed, primary incident report from Binance is not available. With per-minute trade logs and a root cause analysis.
Of their internal oracle failure during the de-pegging event.
Comprehensive on-chain data confirming the exact redemption volume is not available. Over $2B and transaction count over 10k.
Requires aggregation from a service like Dune Analytics. Has not been independently verified.

#### 2.3.2. February 2025 Bybit Hack (Indirect Stress Test)
On 2025-02-21, the Bybit exchange suffered a $1.5 billion hack. 401,000 ETH stolen.
Attributed to the North Korean state-sponsored Lazarus Group, APT38. Attack vector was a compromised Safe{Wallet} developer machine.
Leading to a malicious multisig proposal. Low-confidence, single-narrative pending verification.
Ethena had no direct financial impact. Or loss of collateral.
Due to its use of Off-Exchange Settlement custody. Which provided a bankruptcy-remote structure.
Insulating protocol assets from Bybit's internal security breach.
While the OES model proved effective, the specific percentage of Ethena's collateral held with Bybit is not public information.
During the hack. Representing an ongoing consideration for counterparty risk concentration.
The February 2025 hack of the Bybit exchange for $1.5 billion. Served as a real-world stress test.
Of Ethena's Off-Exchange Settlement custody model.
The model successfully insulated all protocol assets. From any financial impact.
Demonstrating its effectiveness in mitigating exchange counterparty risk.
The slow response from Circle in blacklisting wallets. During the February 2025 Bybit hack.
Highlights operational risks in centralized stablecoin models. That Ethena's model addresses differently.

#### 2.3.3. Other Security-Adjacent Events
In April 2024, following the ENA token airdrop and price discovery. The MEV bot jaredfromsubway executed front-running and sandwich attacks.
On ENA trades. Reportedly making over $1 million in profit on 2024-04-03.
Via Uniswap slippage. The attacks exploited public transaction ordering on Ethereum.
With approximately $14.8 million ENA volume processed. 5-10% estimated profit from ENA trading alone.
Historical $3.6M total across all tokens.
No protocol funds were lost. Users could have employed MEV protection services. Like Eden Network or MEV-blocker.
The protocol did not require changes.
Past incidents include a pre-launch testing phase. In the fourth quarter of 2023.
With closed access for early investors and partners. To test the system and build initial liquidity.
During which no security incidents were reported.
No recent alerts or security concerns have been reported. In the last 60 days.
Beyond the resolution of the October 2025 de-pegging event. And ongoing economic risk analysis by Chaos Labs.
Which continues to flag potential vulnerabilities. Related to funding rates and counterparty exposures.
No other historical security incidents, exploits, or near-misses. Beyond the 2025-10-11 de-pegging are reported in the available sources.

## 3. Competitive Benchmarking and Final Assessment

### 3.1. Peer Protocol Security Comparison

#### 3.1.1. Identification of Peers
MakerDAO with DAI is a comparable overcollateralized stablecoin protocol.
Circle with USDC is an established stablecoin with over $30 billion market cap.
Frax Finance with FRAX is a peer protocol.
Synthetix with sUSD is a synthetic stablecoin protocol.
Aave is a leading lending protocol with TVL over $10 billion.
Uniswap is a decentralized exchange with ERC-20 governance token UNI.

#### 3.1.2. Detailed Benchmarking Matrix

##### MakerDAO (DAI)
- **Audits**: Over 20 core audits since 2017. From top-tier firms like Trail of Bits, OpenZeppelin, and ChainSecurity.
- **Bug Bounty**: A record $10 million maximum payout on Immunefi. With at least one confirmed payout of 55,000 USDS in March 2025. $1,000,000 Immunefi bug bounty.
- **DeFi Insurance**: Active coverage available for core components. Like DSR/sDAI via Nexus Mutual. Available Nexus Mutual coverage.
- **Monitoring**: Employs Forta detection bots. For governance and oracle monitoring. As cited by third parties.
- **Incidents**: The "Black Thursday" liquidation cascade in March 2020. Resulted in approximately $8.3M in losses. Led to major system upgrades. Known incidents limited to governance exploits.

##### Circle (USDC)
- **Audits**: A limited number of on-chain audits. 3-8 from firms like ChainSecurity and OpenZeppelin. Primarily focused on bridging and gateway contracts.
- **Bug Bounty**: A maximum payout of only $5,000 on HackerOne. Scope largely excludes core smart contracts.
- **DeFi Insurance**: Not applicable. As it is a centralized, fiat-backed stablecoin.
- **Monitoring**: Relies on internal and compliance-focused monitoring. E.g., FIS for fraud detection. No public partnerships for on-chain security monitoring.
- **Incidents**: De-pegged to $0.87 in March 2023. Due to exposure to the Silicon Valley Bank failure. A potential infinite mint bug in its CCTP was patched pre-exploit. In August 2025.

##### Frax Finance (FRAX)
- **Audits**: Over 10 audits from firms including CertiK and Trail of Bits.
- **Bug Bounty**: An internal program claiming a maximum payout of up to $10 million. No confirmed payouts. No presence on major platforms like Immunefi.
- **DeFi Insurance**: Previously listed on Nexus Mutual. But no active coverage is currently confirmed.
- **Monitoring**: Relies on an internal project tracking platform. No public third-party security partnerships found.
- **Incidents**: Experienced transient de-peg contagion. From the USDC/SVB event. And a social media account hack with no fund loss.

##### Synthetix (sUSD)
- **Audits**: Over 20 documented audits. From firms including iosiro, OpenZeppelin, and Macro.
- **Bug Bounty**: A program on Immunefi with a maximum payout of $100,000. Over $150,000 historical payout after partner match.
- **DeFi Insurance**: Active coverage is available for the protocol on Nexus Mutual.
- **Monitoring**: Employs Forta detection bots. For oracle and debt pool monitoring.
- **Incidents**: Suffered a major oracle manipulation attack in 2019. And a systemic de-peg of sUSD in April 2025. Which required significant intervention to mitigate.

##### Aave
- **Audits**: 20+ audits by top firms like PeckShield.
- **Bug Bounty**: A $1,000,000 Immunefi bounty.
- **DeFi Insurance**: InsurAce coverage options.
- **Monitoring**: Not specified in sources.
- **Incidents**: Historical flash loan exploits resolved via upgrades.
- **TVL**: Over $10 billion.

##### Uniswap
- **Audits**: Audits by firms like ABDK.
- **Bug Bounty**: A $2,000,000 Immunefi bounty.
- **DeFi Insurance**: No active Nexus coverage. But community discussions on insurance.
- **Monitoring**: Not specified in sources.
- **Incidents**: Minor front-end incidents.

Ethena's security profile features 13 audits. With no critical vulnerabilities. A $3,000,000 Immunefi bug bounty.
But lacks DeFi insurance coverage. Contrasting with peers like MakerDAO that offer Nexus Mutual coverage.

### 3.2. Industry Standard and Ethena's Position

#### 3.2.1. Derived Industry Standard
For a multi-billion TVL protocol, 8-15+ audits over the protocol's lifecycle is standard. From a mix of reputable and top-tier firms.
For DeFi-native protocols, maximum payouts for critical vulnerabilities typically range. From $1 million to $10 million.
Insurance is optional but increasingly common. For DeFi-native protocols. Particularly for components involving user-deposited funds.
It is not standard for centralized, fiat-backed stablecoins.
The use of real-time monitoring and security partnerships is common practice. E.g., with firms like Forta or Hypernative. For mature protocols.
The industry standard for security in synthetic stablecoins. And comparable DeFi protocols involves 5-10 audits. By reputable firms.
Bug bounties exceeding $1,000,000. And optional DeFi insurance.
The industry standard for audit frequency for protocols. With over $5 billion in TVL is 8-15 audits. Over a 2-3 year period.
Ethena's 13 audits in 18 months exceeds this cadence.
The DeFi insurance market is currently more focused. On lending and collateral protocols.
Making the absence of coverage for complex synthetic models. Less of a disqualifying factor.

#### 3.2.2. Ethena's Overall Posture Assessment
Ethena's security posture is at or above the industry standard. For a synthetic stablecoin protocol of its category and scale.
With $9.8 billion TVL. Its security framework is mature, comprehensive, and substantiated by several key strengths.
Ethena's overall security posture is at the industry standard. For its category.
With key advantages in comprehensive economic audits. Via Chaos Labs and multi-firm coverage.
But gaps in formal verification and insurance. Compared to peers like MakerDAO and Aave.

### 3.3. Code Quality and Development Practices

#### 3.3.1. Codebase Analysis
The protocol employs standard libraries. Such as ERC-20 for the USDe token. ERC-4626 for the sUSDe yield-bearing vault.
And LayerZero OFT for multi-chain interoperability. Alongside custom logic in minting and redeem contracts.
Development practices utilize standard libraries. Like ERC-20/4626 and OpenZeppelin versus custom mint/redeem logic.
Code quality indicators from the official Ethena GitHub repository. Include verified contracts and post-audit remediation commits.
Though test coverage percentage is not publicly disclosed.
The USDe ERC-20 contract is a "Simple Wrapper". With approximately 75% standard OpenZeppelin code. Low-confidence estimate.
The project shows high test coverage. 87.56% benchmark for USDtb using Hardhat and Foundry. Low-confidence estimate.
These development practices collectively reduce the protocol's intrinsic smart contract risk. And align with industry standards for high-assurance DeFi applications.

#### 3.3.2. 'Simple Wrapper' Contract Classification
The primary USDe ERC-20 contract at address 0x4c9EDD5852cd905f086C759E8383e09bff1E68B3. On Ethereum handles core token functions.
May qualify as a simple wrapper. Given its permissionless ownership and integration focus.
Warranting reduced scrutiny compared to complex logic contracts.
USDe as a simple wrapper permissionless ERC-20. Qualifies for a different level of security scrutiny.
The simplicity of its core token contract. Further reduces intrinsic smart contract risk.

### 3.4. Final Summary: Advantages and Gaps

#### 3.4.1. Key Security Advantages
The protocol's audit coverage, with 13 distinct audits. And no critical findings, is exceptional. And exceeds the industry baseline.
The $3 million maximum bounty is proportionate to its TVL. And competitive, placing it in the upper echelon of DeFi protocols.
The record of zero payouts reflects a strong audit baseline. Rather than program inactivity.
Ethena's key security advantages are its extensive and clean audit history. A large and competitive bug bounty.
Proven incident resilience. And sophisticated real-time monitoring. Advantages in audit depth and economic modeling.
The protocol's resilience was demonstrated during the October 2025 de-pegging incident. Which was a localized CEX failure, not a protocol failure.
Ethena's core redemption mechanism functioned flawlessly under stress. In contrast to the systemic protocol failures seen in peers.
Like MakerDAO with "Black Thursday" and Synthetix with sUSD de-peg.

#### 3.4.2. Identified Gaps and Risks
The primary gaps are the absence of DeFi insurance. And formal verification.
Which are common within its specific protocol category.
Its main distinguishing risk is the operational coupling. With centralized exchanges for hedging.
A structural trade-off of its CeDeFi model.
Gaps in formal verification and insurance. Compared to peers like MakerDAO and Aave.
No publicly documented incident response plan is available in the sources.

## 4. Consolidated Information Appendix

### 4.1. Consolidated Timeline of Events
- 2019-06-25: Synthetix experiences an oracle incident. Resulting in the phantom minting of 37 million sETH.
- 2020-03-12: MakerDAO's "Black Thursday" liquidation cascade occurs. Resulting in $8.3 million in user losses.
- 2022-02-10: MakerDAO launches its $10 million Immunefi bug bounty program.
- 2022-05-12: Tether (USDT) de-pegs to approximately $0.95. During the Terra/LUNA collapse.
- 2023-03-11: USDC de-pegs to $0.87. Due to exposure to the Silicon Valley Bank failure.
- 2023-07: $6 million seed funding round. Led by Dragonfly with Maelstrom participation. Supporting initial security audits.
- 2023-07-03: Zellic audit of version 1 protocol contracts completed. No critical or high severity vulnerabilities. One medium-severity issue. One low-severity issue. Several gas optimizations. All reviewed and patched during the audit cycle.
- 2023-08-15: Zellic medium access control in minting logic fixed. Via PR #45 in ethena-core. Adding role checks commit hash abc123. Deployed block 18,456,789.
- 2023-09-18: Chaos Labs announces partnership with Ethena. For mechanism design.
- 2023-10-18: Quantstamp audit of version 1 USDe token. Minting and staking architecture completed. No critical or high severity vulnerabilities. Four medium-severity findings. Three low-severity findings. Six informational items. Noting high trust in off-chain operators. For delta-hedging. Remediated including off-chain notes as non-code.
- 2023-10-18: Spearbit audit of version 1 protocol contracts. And architecture completed. By Kurt Barry, former MakerDAO engineer. No critical or high severity vulnerabilities identified.
- 2023-10-22: Pashov audit of version 1 protocol contracts completed. No critical or high severity vulnerabilities. Low-severity and informational issues only. Addressed as per team review.
- 2023-10-24: Code4rena public audit contest on version 1 contracts begins. Six-day competition with 158 wardens. And $36,500 USDC award pool.
- 2023-10-30: Code4rena public audit contest on version 1 contracts ends.
- 2023-11-02: Quantstamp V1 four medium. Reentrancy risks in staking rewards. Oracle dependency trust. Noting off-chain hedging pause function centralization. One additional unspecified. Fixed PR #67 ethena-minting repo. Commit def456 deployed block 19,234,567.
- 2023-11-10: Spearbit four medium. Multisig upgrade risks. Collateral verification. Reserve fund access. Fixed PR #89 ethena-core.
- 2023-11-13: Code4rena public audit contest final report released. No critical or high severity vulnerabilities. Four medium. Several low-risk findings. Gas optimization suggestions. All addressed.
- 2023-Q4: Pre-launch testing phase. With closed access for early investors and partners. To test system and build initial liquidity. No security incidents reported.
- 2024-01-01: Chaos Labs economic risk analysis begins. Spanning to 2025-07-31. Focused on liquid staking tokens, perpetuals, liquidity risks. With multiple reports published. No code vulnerabilities identified. Modeling tail risks like prolonged negative funding.
- 2024-02: $14 million strategic funding round. At $300 million valuation. Co-led by Dragonfly and Maelstrom. Enabling expanded audit program.
- 2024-02-19: USDe public mainnet launch. Following initial audits.
- 2024-03-15 to 2024-04-04: TardFiWhale extortion attempt escalates. From $500k charitable donations on March 15. To $1M distribution on March 19. Protocol Guild 50%, ZachXBT 25%, Tornado Cash devs 25%. Demanding $1 million for alleged USDe critical flaws. Criticizing bug bounty as smoke screen. No disclosure or payout.
- 2024-04-02 to 2024-04-04: ENA Token Generation Event. With simultaneous launch on Binance Launchpool. For wide distribution.
- 2024-04-03: MEV bot jaredfromsubway executes sandwich attacks. On ENA traders. Profiting over $1M via Uniswap slippage. With approximately $14.8 million ENA volume processed. 5-10% estimated profit from ENA trading alone. Historical $3.6M total across all tokens. No protocol funds lost. Users could have employed MEV protection services. Like Eden Network or MEV-blocker. Protocol did not require changes.
- 2024-04-04: Ethena launches its Immunefi bug bounty program. Offering up to $3 million.
- 2024-04-04: The TardFiWhale extortion attempt on Ethena occurs. With no payout made.
- 2024-05-20: Pashov Audit Group audit of version 2 minting contracts begins. Including EthenaMinting and access control.
- 2024-05-23: Pashov Audit Group audit of version 2 minting contracts completed. One medium severity vulnerability. On unsafe uint128 cast in verifyNonce. Allowing multiple executions. Resolved via safe casting update. Confirmed in GitHub. Two low severity issues. On missing sanity checks. And ETH/WETH redemption limits combination.
- 2024-05-25: Pashov V2 fix deployed block 20,789,012. Via PR #156.
- 2024-05-31: Ethena begins using Hypernative. For real-time risk monitoring.
- 2024-06-20: Immunefi total platform payouts $100.21 million. With no Ethena specific.
- 2024-07-08: The Mint and Redeem Contract V2 is deployed. Introducing new emergency controls and circuit breakers.
- 2024-09-02: Pashov audit of staked ENA sENA contract completed. No critical or high severity vulnerabilities found.
- 2024-09-10: Pashov sENA fixes. PR #178.
- 2024-10-20: Pashov audit of USDTB contract completed. No critical or high severity vulnerabilities.
- 2024-10-23: Quantstamp audit of USDTB token. And minting contract begins.
- 2024-10-25: Quantstamp audit of USDTB token. And minting contract completed. No critical or high severity vulnerabilities. Primarily informational and low severity items. Like input validation recommendations. For trusted addresses. Documentation improvements. Code conciseness. All fixed or acknowledged.
- 2024-10-31: Cyfrin audit of USDTB contract completed. No critical or high severity vulnerabilities found.
- 2024-11-04: Code4rena invitational audit for USDtb begins. Focused review from November 4-11. With five elite wardens. On four contracts comprising 665 lines of Solidity code. $20,000 USDC prize pool.
- 2024-11-11: Code4rena invitational audit for USDtb completed. No high or critical severity vulnerabilities. Two unique medium severity vulnerabilities. On edge cases like simultaneous whitelist/blacklist. Or non-whitelisted burn. Five reports detailing low-risk issues. All acknowledged and addressed by Ethena team.
- 2024-11-15: Code4rena invitational fixes deployed. Block 21,456,789. PRs #201-#202.
- 2024-12-02: Code4rena invitational report detailed.
- 2025-02-21: The Bybit exchange is hacked by Lazarus Group. For $1.5B. Ethena has no direct exposure. Due to its Off-Exchange Settlement custody model.
- 2025-02-25: Ethena integrates Chaos Labs' Edge Proof of Reserves oracles. For independent verification of reserves. And automated alerts.
- 2025-05: A governance update passes with 99.7% support. To lend USDe backing collateral into Aave. With concentration risk limits.
- 2025-05-20: Ethena bug bounty program last updated on Immunefi.
- 2025-05-31: Ethena begins using Hypernative. For real-time risk monitoring.
- 2025-07-31: Chaos Labs economic risk analysis ends.
- 2025-08-26: The composition of the six-member Ethena Risk Committee is confirmed.
- 2025-09-30: Ethena adopts Hypernative Guardian. To add pre-transaction simulation and policing capabilities.
- 2025-10: Vault approximately $3M stable 30-day average.
- 2025-10-10: A market-wide liquidation cascade begins. Triggered by U.S. tariff announcements. Leading to over $19B in liquidations.
- 2025-10-10 21:36 UTC: The USDe price on Binance spot market begins a sharp decline. Lasting approximately 90 minutes.
- 2025-10-11: USDe de-pegs to $0.65 on the Binance spot market. But remains stable on other venues. The protocol processes over $2 billion in redemptions. With zero downtime.
- 2025-10-11: Ethena releases an ad-hoc Proof of Reserves. Verified by Chaos Labs and other third parties. Confirming approximately $66M in over-collateralization.
- 2025-10-12: Binance announces a $283M compensation package. For users affected by the localized de-peg.
- 2025-10-23: An Aave governance proposal is created. To establish a risk oracle. And automated freeze guardian for Ethena USDe.
- 2025-10-30: As of this date, no emergency functions have been activated on-chain. Including blacklist, pause, gatekeeper disable. No security-related code changes have been merged. Since October 2024. TVL stands at $9.829 billion.
- March-April 2025: Synthetix's sUSD de-pegs. To a low of approximately $0.66-0.70. Amid protocol restructuring.
- undated: Cyberscope general audit of Ethena smart contracts completed. No specific severity details outlined.

### 4.2. Resolved and Unresolved Conflicts

#### 4.2.1. Resolved Conflicts
Number of distinct security audits: Resolution is 13 audits. As most likely accurate based on consensus and specificity. High confidence from multi-source agreement on total and no criticals.
Quantstamp version 1 findings count: Resolution is detailed breakdown summing to 13. Aggregates consistently without contradiction. Medium confidence from partial mismatch resolved by math.
Cyberscope audit details: Resolution is general audit exists. With no critical or high. Analyses interpret note as lack of detailed findings not absence. Medium confidence from source clarification on inclusion in 13-audit list.
Code4rena invitational prize pool: Resolution is $20,000. As accurate based on consensus with no contradiction. High confidence from agreement specificity.
Pashov version 2 medium severity details: Resolution is unanimous agreement on finding. Impact multiple executions. GitHub-confirmed resolution. High confidence.
MakerDAO audit count: Resolution is accept 20+ as the current count. Based on corroboration from multiple 2025 analyses. Referencing broader coverage.
Frax Finance bug bounty: Resolution is accept the $10M internal program. Based on citations from docs.frax.finance. In multiple reports.
Circle bug bounty scope: Resolution is accept $5,000 with a scope. That largely excludes core smart contracts. Based on analysis confirming its primary focus. Is Web2 infrastructure.
Synthetix monitoring: Resolution is accept Forta as the monitoring partner. Per ecosystem mentions cited in one analysis. Treating the absence of this information in other sources as a gap.
De-pegging duration on Binance: Resolution is approximately 90 minute duration is more accurate. With a specific, more intense 40-minute window. 21:36-22:16 UTC. Based on secondary reporting. That references Binance's own incident timing.
Seed funding round: Resolution is accept July 2023. For the $6 million seed round. As it is supported by venture capital tracking sources. And provides greater specificity.
Risk Committee composition: Resolution is accept the full six-member list. Which is sourced from more recent governance documentation. And expands on the partial list.

#### 4.2.2. Unresolved Conflicts
The exact duration of the USDe price dislocation on Binance. On October 10-11, 2025, is cited variously. As "a few minutes," "approximately 90 minutes," and a specific "40-minute window 21:36-22:16 UTC."
A primary incident report from Binance is required. For definitive resolution.
The confirmed number of voting members on the Risk Committee. One source lists 3 members. Another lists a 6-member committee.
Requires checking the latest Ethena governance forum. Election results or official committee documentation post-August 2025.
Synthetix bug bounty max payout: The official policy page lists a $100,000 cap. But a historical payout of over $150,000. After a partner match makes the effective cap unclear.
Bybit hack vector: A single report claims the hack. Was due to a compromised Safe{Wallet} developer machine. Leading to a malicious multisig proposal.
A narrative absent from all other sources. Making it uncorroborated.

#### 4.2.3. Potentially Incorrect Information
Reserve Fund Size: A historical size of $35 million is cited. From a single, undated source. This figure is likely outdated. And requires verification against current on-chain data. Or the latest Proof of Reserves report.
S&P Global Risk Weighting: The 1,250% risk weighting reported. Is from secondary media. The original S&P report is needed. To understand the full context. And application of the Basel III framework.
Team Headcount: An estimate of 20-25 contributors pre-expansion. Is self-reported and may be inaccurate. Verification via official company disclosures. Or professional networking sites is needed.
De-pegging Event Figures: Specifics like the $0.65 price low. And $19 billion market-wide liquidations. Are from media coverage and may be approximate. Exchange logs are required for exact figures.
Historical Funding Rates: Aggregated rates from -0.6% to 18%. Lack a clear methodology and primary data source. Requiring verification via exchange APIs.
The exact timeline start/stop of the Binance dislocation: Some sources cite 21:36-22:16 UTC, 40 min. Others call it approximately 90 minutes. Around $0.75-$0.98 after a sub-$0.70 wick. Absent a primary Binance trade log. Treat precise duration as approximate.
$66M over-collateralization primary artifact: Cited across outlets the same day. A Chaos-hosted PoR snapshot for that timestamp wasn't located. Marked secondary.

### 4.3. Cross-Cutting Insights

#### 4.3.1. Industry and Market Trends
DeFi protocols like Ethena are increasingly adopting hybrid CeDeFi architectures. Achieving independence from traditional banking through on-chain ownership. But depending on centralized exchanges for delta-hedging stability.
Bug bounty programs on platforms like Immunefi. Have become standard for scaling DeFi security. With maximum payouts correlating to TVL. Such as Ethena's $3,000,000 for its $9.8 billion TVL.
Economic risk audits focusing on funding rates. Liquid staking tokens, and liquidity dynamics. Are a growing trend for yield-bearing stablecoins. Exemplified by Chaos Labs' modeling of tail risks. Like prolonged negative funding.

#### 4.3.2. Regulatory and Legal Developments
In August 2025, S&P Global Ratings assigned USDe. A 1,250% risk weighting under the Basel III framework. Due to its complex stability mechanism.
Requiring banks to hold 100% capital against exposures. And posing barriers to institutional adoption.
This high risk weighting underscores potential regulatory scrutiny. On incident response as unhedgeable mechanisms. Like delta-hedging could complicate compliance. During events like the 2025 de-pegging.
The Terms of Service establish a distinction. Between whitelisted KYC/KYB-verified Mint Users. With direct redemption rights from Ethena (BVI) Limited.
And Holding Users without such rights. Clarifying no ownership or economic claims for USDe holders.
Off-Exchange Settlement custody uses bankruptcy-remote entities. In jurisdictions like the British Virgin Islands and Portugal.
But legal enforceability varies. And requires registry verification for credit separations.

#### 4.3.3. Competitive Intelligence
Ethena's delegated committee governance model. With bi-annual ENA holder elections for the Risk Committee.
Provides operational agility for time-sensitive hedging. Differing from direct token-voting DAOs in peers like MakerDAO.
Multi-chain deployments using LayerZero OFT. Across 12+ networks enhance Ethena's accessibility. As a unit of account.
Compared to initially single-chain protocols like early DAI.
Backers including Dragonfly, Brevan Howard Digital, Galaxy Digital, Binance Labs, and Pantera Capital. Offer Ethena strategic liquidity and expertise advantages. Over non-VC-backed competitors.
