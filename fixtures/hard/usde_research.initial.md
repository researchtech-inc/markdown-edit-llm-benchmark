s# USDe Protocol: Comprehensive Due Diligence and Risk Assessment Report

**Date:** November 26, 2025
**Subject:** Ethena (USDe) Integrated Analysis
**Scope:** Contract Maturity, Financial Mechanics, Infrastructure Risks, and Incident History

---

## 1. Executive Summary

USDe is a synthetic dollar protocol operating on Ethereum and various Layer 2 networks. As of October 30, 2025, the protocol manages approximately $9.829 billion in Assets Under Management (AUM), with a circulating supply of roughly 9.65 billion USDe. The protocol generates yield through a delta-neutral hedging strategy, combining spot liquid staking token (LST) assets with short perpetual futures positions.

The protocol has demonstrated significant operational resilience, particularly during the market stress event of October 10-11, 2025. Despite a localized flash crash on Binance where USDe briefly de-pegged to $0.65, on-chain redemptions functioned without interruption, processing over $2 billion in volume while maintaining a peg deviation of less than 0.3% on decentralized exchanges.

However, the protocol faces distinct centralization and regulatory risks. Infrastructure relies heavily on off-chain operators for hedging, centralized exchange (CEX) counterparty risk, and a governance model that eschews on-chain timelocks for operational agility. Furthermore, regulatory headwinds are significant, notably an S&P Global risk weighting of 1,250% assigned in August 2025, potentially limiting institutional banking integration.

This report synthesizes data regarding contract maturity, upgrade history, financial hedging mechanics, infrastructure vulnerabilities, and a detailed forensic analysis of historical incidents.

---

## 2. Protocol Architecture and Contract Deployment

### 2.1. Core Contract Maturity
The Ethena protocol's core contracts on the Ethereum mainnet have been operational since early 2024, predating the public mainnet launch.

*   **USDe Token:** ERC-20 standard.
    *   **Address:** `0x4c9EDD5852cd905f086C759E8383e09bff1E68B3`
    *   **Status:** Immutable, non-proxy. Verified.
*   **sUSDe Staking:** ERC-4626 yield-bearing vault.
    *   **Address:** `0x9d39a5de30e57443bff2a8307a4256c8797a3497`
    *   **Deployment:** November 14, 2023.
    *   **Mechanics:** 7-day unstaking cooldown; value increases via revenue deposits rather than rebasing.
*   **ENA Governance Token:** ERC-20.
    *   **Address:** `0x57e114B691Db790C35207b2e685D4A43181e6061`
    *   **Deployment:** May 16, 2024.
    *   **Supply:** Capped at 15 billion tokens.
*   **Mint and Redeem V2:**
    *   **Address:** `0xe3490297a08d6fC8Da46Edb7B6142E4F461b62D3`
    *   **Deployment:** July 8, 2024.
    *   **Type:** UUPS Proxy with SingleAdminAccessControl.
*   **Reserve Fund:**
    *   **Address:** `0x2b5ab59163a6e93b4486f6055d33ca4a115dd4d5`
    *   **Deployment:** January 11, 2024.
    *   **Type:** Gnosis Safe Proxy.
*   **USDTB Token:**
    *   **Address:** `0xc139190f447e929f090edeb554d95abb8b18ac1c`
    *   **Creation:** November 28, 2024 (Launch: December 16, 2024).
    *   **Backing:** Tokenized T-Bills (BlackRock BUIDL) and stablecoins.

### 2.2. Multi-Chain Deployment Strategy
Ethena utilizes a hybrid approach for multi-chain expansion, employing LayerZero's Omnichain Fungible Token (OFT) standard for EVM chains and native implementations for non-EVM chains.

**LayerZero OFT Deployments (EVM):**
*   **Address:** `0x5d3a1Ff2b6BAb83b63cd9AD0787074081a52ef34` (Canonical for L2s).
*   **Networks:** BNB Smart Chain, Arbitrum One, Optimism, Base, Mantle, Linea, Manta Pacific, Scroll, Kava, Metis Andromeda, Zircuit.
*   **Benefit:** Enables cross-chain transfers without wrapping or fragmented liquidity pools.

**Native Deployments (Non-EVM):**
*   **Solana:** Address `DEkqHyPN7GMRJ5cArtQFAWefqbZb33Hyf6s5iCwjEonT` (SPL Standard). TVL exceeded $1.6B post-deployment.
*   **ZKSync Era:** Address `0x39Fe7a0DACcE31Bd90418e3e659fb0b5f0B3Db0d`.
*   **TON:** Jetton address `EQAIb6KmdfdDR7CN1GBqVJuP25iCnLKCvBlJ07Evuu2dzP5f` (Launched April 2025).
*   **Aptos:** Address `0xb30a694a344edee467d9f82330bbe7c3b89f440a1ecd2da1f3bca266560fce69`.

### 2.3. Contract Upgrade History
The protocol has undergone controlled upgrades managed via multisig, with no reported incidents during migration phases.

1.  **V1 to V2 Minting (July 8, 2024):**
    *   **Change:** Implementation of UUPS proxy pattern.
    *   **Features:** Added per-asset mint/redeem limits, EIP-1271 signature verification, and on-chain whitelisting.
    *   **Execution:** Involved ~15 minutes of planned downtime.
    *   **Audit:** Preceded by Pashov audit (May 2024).

2.  **sENA Staking Deployment (September 9, 2024):**
    *   **Details:** New staking contract using OpenZeppelin TransparentUpgradeableProxy.
    *   **Purpose:** Enable fee-switch revenue accrual for governance participants.

3.  **USDTB Integration (November 2024):**
    *   **Details:** Extension for tokenized T-Bill backing.
    *   **Audit:** Reviewed by Pashov, Quantstamp, and Code4rena prior to launch.

---

## 3. Financial Mechanics and Hedging Strategy

### 3.1. Delta-Neutral Strategy
USDe functions as a synthetic dollar. It does not rely on fiat reserves in a bank but maintains stability through a hedged portfolio:
*   **Long Position:** Spot assets (BTC, ETH, stETH, USDTB).
*   **Short Position:** Perpetual futures contracts on Centralized Exchanges (CEXs).
*   **Net Exposure:** Delta-neutral (price movements in the spot asset are offset by the short position).

**Yield Sources:**
1.  **Staking Yield:** 3-4% baseline APY from LSTs (e.g., stETH).
2.  **Funding Rates:** Yield generated when shorts pay longs in contango markets.
    *   *Historical Performance:* Averaged ~19% in 2024.
    *   *Current Performance:* Compressed to ~4.1% (30-day average) in late 2025.
    *   *Risk:* Negative funding rates require the protocol to pay out, depleting the Reserve Fund.

### 3.2. Collateral and Custody
*   **Asset Composition:**
    *   ~50% in Ethereum-related assets (ETH, LSTs).
    *   ~50% in Stablecoins (USDC, USDT) used for margin collateral.
    *   Introduction of Bitcoin (Q2 2024) and USDTB (Q4 2024) for diversification.
*   **Off-Exchange Settlement (OES):**
    *   Collateral is not held directly on exchanges. It is held in bankruptcy-remote trust structures.
    *   **Providers:** Copper (Primary), Ceffu, Fireblocks, Cobo, and Coinbase Web3 Wallets.
    *   **Concentration Risk:** As of September 2025, Copper and Ceffu combined held approximately 50.5% of assets, with Coinbase holding 49.1%.

### 3.3. Reserve Fund
*   **Purpose:** On-chain insurance buffer for periods of negative funding.
*   **Address:** `0x2b5ab59163a6e93b4486f6055d33ca4a115dd4d5`.
*   **Balance Status:**
    *   **On-Chain (Oct 26, 2025):** ~$41.89 million (Verified).
    *   **Total Buffer (Oct 11, 2025):** Proof of Reserves indicated a total over-collateralization of $66 million (0.68% of liabilities) following the de-peg event.
    *   *Note:* There is a discrepancy between the on-chain wallet balance and the "Total Buffer" reported in PoR, likely due to assets held in LP positions or unrealized PnL not settled to the main address.

### 3.4. Fee Structure and "Fee Switch"
*   **Base Fees:** 0% management fee. Users pay gas and execution costs.
*   **Fee Switch (Nov 2024):**
    *   **Proposal:** Wintermute proposed directing protocol revenue to sENA holders.
    *   **Status:** Approved in principle by the Risk Committee (Nov 15, 2024).
    *   **Activation:** Thresholds (Supply >$8B, TVL >$12B) were met in September 2025. Implementation details regarding the specific revenue split remain pending final vote.

---

## 4. Operational Governance and Control

### 4.1. The Delegated Committee Model
Ethena utilizes a delegated governance structure rather than a direct token-voting DAO for operational decisions, citing the need for agility in hedging.
*   **Token:** ENA (ERC-20).
*   **Mechanism:** ENA holders vote bi-annually via Snapshot to elect the **Risk Committee**.
*   **Risk Committee Composition:**
    *   Llama Risk (DeFi modeling experts).
    *   Blockworks Advisory.
    *   Kairos Research.
    *   Steakhouse Financial.
    *   Untangled (Credio).

### 4.2. Multisig Controls
Control over the protocol is concentrated in multisig wallets rather than autonomous code.
*   **Primary Multisig:** Gnosis Safe (`0x3B0...1862`).
*   **Threshold Conflict:**
    *   *Documentation/Etherscan:* 7-of-10 threshold.
    *   *Safe App Data (June 2025):* Indicates a potential update to a 4-of-8 threshold.
    *   *Status:* Signer identities are anonymous/undisclosed, keys are in cold storage.
*   **Timelock:** There is **no on-chain timelock**. This is a deliberate design choice to allow immediate reaction to market volatility, but it represents a significant centralization risk.

### 4.3. The GATEKEEPER Role
*   **Function:** A circuit breaker mechanism.
*   **Control:** Requires 3+ externally owned accounts (EOAs) to activate.
*   **Capability:** Can disable minting/redeeming or remove operator roles in response to oracle failures or exchange outages.
*   **Triggers:** Activation is based on off-chain monitoring of price anomalies.
*   **Status:** No historical activations recorded as of October 2025.

---

## 5. Security Audits and Vulnerability Assessment

### 5.1. Audit History
The protocol has engaged in a robust audit schedule (>11 audits).

| Date | Firm | Scope | Findings Summary |
| :--- | :--- | :--- | :--- |
| **Jul 2023** | Zellic | V1 Contracts | No critical/high. 1 Medium (Reentrancy) - Fixed. |
| **Oct 2023** | Quantstamp | V1 Architecture | No critical/high. 4 Medium (Centralization risks acknowledged). |
| **Oct 2023** | Spearbit | V1 Contracts | No critical/high. 1 Low (SafeMath) - Fixed. |
| **Oct 2023** | Pashov | V1 Contracts | No critical/high. |
| **Nov 2023** | Code4rena | V1 Contest | No critical/high. Access control issues fixed in V1.3. |
| **May 2024** | Pashov | V2 Minting | 1 Medium (Nonce casting) - Fixed. |
| **Sep 2024** | Pashov | sENA Contract | No critical/high. |
| **Oct 2024** | Quantstamp | USDTB | No critical/high. Informational findings only. |
| **Nov 2024** | Code4rena | USDTB | 2 Medium (Whitelist edge cases) - Fixed. |
| **2024-25** | Chaos Labs | Economic Risk | Ongoing modeling. Confirmed reserve adequacy for tail risks. |

### 5.2. Bug Bounty Program
*   **Platform:** Immunefi (Launched April 4, 2024).
*   **Reward:** Up to $3,000,000 for critical smart contract vulnerabilities (10% of funds at risk).
*   **Payouts:** No publicly disclosed payouts.
*   **Coverage:** Includes smart contracts, websites, and applications under "primacy of impact."

### 5.3. External Dependencies and Risks
1.  **LayerZero OFT:** Used for bridging to 11+ L2 networks. While LayerZero has been audited, the configurable nature of relayers/oracles introduces third-party risk. (Note: 2025 LayerZero ecosystem incidents were application-level, not protocol-level).
2.  **Oracles:**
    *   *Primary:* Centralized feeds from Binance/Bybit (critical for hedging).
    *   *On-Chain:* Chainlink (USDe/USD).
    *   *Risk:* The October 2025 incident highlighted that reliance on a single CEX's internal oracle (Binance) can cause localized de-pegging even if the on-chain oracle is stable.
3.  **Centralized Keepers:** Hedging is executed by off-chain bots. Quantstamp noted this requires a "high degree of trust."
4.  **AWS Dependence:** Keepers run on AWS; documentation lacks proof of diverse region/account isolation.

---

## 6. Incident Analysis: The October 2025 De-Peg

**Date:** October 10-11, 2025
**Type:** Financial De-peg / Liquidity Flash Crash
**Status:** Resolved (Localized to Binance).

### 6.1. The Event Trigger
Following a geopolitical announcement regarding tariffs, the broader crypto market experienced a massive sell-off, resulting in over $19 billion in liquidations.

### 6.2. The De-Peg Mechanics
*   **Venue:** Binance Spot Market (USDe/USDT).
*   **Deviation:** Price fell to a low of **$0.65** (35% deviation).
*   **Duration:** The "severe window" lasted approximately 45-90 minutes.
*   **Cause:** Binance's internal oracle disconnected from broader market prices due to the volatility and thin order books, triggering cascading margin calls on traders using USDe as collateral.
*   **Contagion Check:**
    *   **Bybit:** Minor deviation (~$0.92 low).
    *   **DeFi (Curve/Uniswap):** Stable. Deviation <0.3% ($0.995 - $1.001).
    *   **Chainlink Oracle:** Remained stable, preventing liquidations on Aave.

### 6.3. Protocol Response and Resilience
*   **Redemptions:** The mint/redeem contract processed over **$1.9 billion** in redemptions within 24 hours.
*   **Performance:** No downtime or contract failures were observed.
*   **Solvency:** An unscheduled Proof of Reserves (PoR) verified by Chaos Labs on Oct 11 confirmed the protocol remained 100.7% collateralized (excess equity of ~$66 million).
*   **Compensation:** Binance established a $283 million compensation fund for affected users, acknowledging the issue was specific to their matching engine/oracle.

---

## 7. Other Historical Incidents

### 7.1. Bybit ETH Cold Wallet Hack (February 21, 2025)
*   **Event:** Bybit suffered a $1.4B - $1.5B theft via a UI compromise.
*   **Ethena Exposure:** Limited to <$30 million in unrealized PnL (unsettled hedging profits).
*   **Mitigation:** Positions were closed, and PnL was settled to zero within 90 minutes.
*   **Losses:** No direct loss of principal collateral, as assets were held in OES custody (Copper/Ceffu), not on Bybit.

### 7.2. Phishing Incident (March 2024)
*   **Event:** A fake ENA token on Binance Launchpool.
*   **Impact:** ~$290k loss to users.
*   **Relevance:** Non-protocol incident. Core contracts were unaffected.

---

## 8. Data Quality and Gap Analysis

### 8.1. Verified Data (High Confidence)
*   **Contract Addresses:** All mainnet and L2 addresses have been verified against block explorers.
*   **Audit Reports:** Existence and findings of Zellic, Quantstamp, and Code4rena audits are confirmed via official repositories.
*   **October Event:** The $0.65 low on Binance and the functional on-chain redemptions are corroborated by exchange data and governance posts.
*   **Reserve Balance:** The $41.89M on-chain balance is verified via Etherscan (as of Oct 26, 2025).

### 8.2. Material Data Gaps
1.  **Reserve Fund Total Value:** There is a discrepancy between the on-chain wallet ($41.89M) and the PoR reported equity ($66M). The breakdown of the difference (likely LP positions) is not granularly documented in the latest snapshots.
2.  **Multisig Threshold:** Documentation says 7-of-10; Safe App data suggests a shift to 4-of-8. This governance change lacks a confirmed transaction hash.
3.  **Formal Verification:** There is no evidence of formal verification (mathematical proofs) for the contracts, only standard audits.
4.  **S&P Report:** The primary source for the 1,250% risk weighting (Basel III context) is unavailable; the report relies on secondary media coverage.
5.  **OES Allocation:** The exact percentage split of assets between Copper, Ceffu, and Fireblocks is not real-time transparent, obscuring specific counterparty concentration risk.

### 8.3. Red Flags
*   **Regulatory Risk:** The 1,250% S&P risk weighting effectively bars regulated banks from holding USDe, capping institutional adoption.
*   **Centralization:** The lack of a timelock and the reliance on off-chain keepers for hedging remain the most significant structural risks.
*   **Documentation:** Disclosures regarding the October 2025 de-peg were fragmented across social media rather than a centralized post-mortem report.

---

## 9. Conclusion

Ethena (USDe) presents a mature, high-yielding stablecoin product that has successfully weathered significant market stress. The protocol's ability to process $2 billion in redemptions during the October 2025 crash without breaking peg on-chain validates the delta-neutral design and the OES custody model.

However, USDe cannot be classified as "trustless." It functions as a **CeDeFi** hybrid, heavily dependent on the performance of centralized exchanges, off-chain hedging operators, and a multisig-governed intervention model. The centralization risks are mitigated by robust audit coverage and insurance buffers but are not eliminated. Investors must weigh the attractive yield against the counterparty risks of the hedging venues and the regulatory friction restricting institutional capital integration.