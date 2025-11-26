# Requested Changes to USDe Research Report

## Title

- **Modify**: Change "# USDe Protocol: Comprehensive Due Diligence and Risk Assessment Report" to "# USDe Protocol: Comprehensive Due Diligence, Risk Assessment, and User Rights Report"

## Header - Scope

- **Modify**: Change "**Scope:** Contract Maturity, Financial Mechanics, Infrastructure Risks, and Incident History" to "**Scope:** Contract Maturity, Financial Mechanics, User Rights, Legal Framework, Infrastructure Risks, and Incident History"

## Section 1: Executive Summary - Paragraph 3

- **Delete**: Remove the entire paragraph: "However, the protocol faces distinct centralization and regulatory risks. Infrastructure relies heavily on off-chain operators for hedging, centralized exchange (CEX) counterparty risk, and a governance model that eschews on-chain timelocks for operational agility. Furthermore, regulatory headwinds are significant, notably an S&P Global risk weighting of 1,250% assigned in August 2025, potentially limiting institutional banking integration."

- **Add**: After "The protocol has demonstrated significant operational resilience, particularly during the market stress event of October 10-11, 2025. Despite a localized flash crash on Binance where USDe briefly de-pegged to $0.65, on-chain redemptions functioned without interruption, processing over $2 billion in volume while maintaining a peg deviation of less than 0.3% on decentralized exchanges.", add the following paragraphs:

"However, a forensic assessment of the legal framework and user rights reveals a security profile significantly weaker than the operational metrics suggest. The overall assessment of user rights strength is **Weak**. This classification is driven by a tiered user system that strictly limits redemption rights to verified "Mint Users," while the vast majority of holders ("Holding Users") are legally defined as non-customers with no direct claim on the issuer. Furthermore, holders are positioned as unsecured creditors with no beneficial ownership of the underlying reserves, and the issuer retains broad discretion to suspend redemptions without notice or liability.

The protocol faces distinct centralization, legal, and regulatory risks:
*   **Infrastructure:** Heavy reliance on off-chain operators for hedging and centralized exchange (CEX) counterparty risk.
*   **Governance:** A model that eschews on-chain timelocks for operational agility, placing immense trust in multisig signers.
*   **Regulatory:** Significant headwinds, notably an S&P Global risk weighting of 1,250% assigned in August 2025, and a BaFin prohibition order in March 2025 classifying USDe as a MiCA Asset-Referenced Token (ART) with reserve shortcomings."

## Section 1: Executive Summary - Paragraph 4

- **Modify**: Change "This report synthesizes data regarding contract maturity, upgrade history, financial hedging mechanics, infrastructure vulnerabilities, and a detailed forensic analysis of historical incidents." to "This report synthesizes data regarding contract maturity, upgrade history, financial hedging mechanics, infrastructure vulnerabilities, and a detailed forensic analysis of user rights and historical incidents."

## Section 2.1: Core Contract Maturity - Intro

- **Modify**: Change "The Ethena protocol's core contracts on the Ethereum mainnet have been operational since early 2024, predating the public mainnet launch." to "The Ethena protocol's core contracts on the Ethereum mainnet have been operational since early 2024, predating the public mainnet launch. The architecture separates the stablecoin issuance from the yield-bearing staking modules and governance."

## Section 2.1: USDe Token

- **Modify**: Change "*   **USDe Token:** ERC-20 standard.
    *   **Address:** `0x4c9EDD5852cd905f086C759E8383e09bff1E68B3`
    *   **Status:** Immutable, non-proxy. Verified." to "*   **USDe Token:**
    *   **Type:** ERC-20 standard.
    *   **Address:** `0x4c9EDD5852cd905f086C759E8383e09bff1E68B3`
    *   **Status:** Immutable, non-proxy. Verified.
    *   **Legal Status:** Defined in the Terms of Service (ToS) not as a claim on assets, but effectively as prepaid access or stored value."

## Section 2.1: sUSDe Staking

- **Modify**: Change "*   **sUSDe Staking:** ERC-4626 yield-bearing vault.
    *   **Address:** `0x9d39a5de30e57443bff2a8307a4256c8797a3497`
    *   **Deployment:** November 14, 2023.
    *   **Mechanics:** 7-day unstaking cooldown; value increases via revenue deposits rather than rebasing." to "*   **sUSDe Staking:**
    *   **Type:** ERC-4626 yield-bearing vault.
    *   **Address:** `0x9d39a5de30e57443bff2a8307a4256c8797a3497`
    *   **Deployment:** November 14, 2023.
    *   **Mechanics:** Implements a 7-day unstaking cooldown; value increases via revenue deposits rather than rebasing.
    *   **Compliance Features:** Contains blacklist/freeze functionality enabling the issuer to block specific addresses from unstaking, aligning with sanctions compliance but introducing censorship risk."

## Section 2.1: ENA Governance Token

- **Modify**: Change "*   **ENA Governance Token:** ERC-20.
    *   **Address:** `0x57e114B691Db790C35207b2e685D4A43181e6061`
    *   **Deployment:** May 16, 2024.
    *   **Supply:** Capped at 15 billion tokens." to "*   **ENA Governance Token:**
    *   **Type:** ERC-20.
    *   **Address:** `0x57e114B691Db790C35207b2e685D4A43181e6061`
    *   **Deployment:** May 16, 2024.
    *   **Supply:** Capped at 15 billion tokens.
    *   **Vesting Risks:** Approximately 30% of supply (4.5 billion tokens) is subject to opaque vesting schedules with varying immediate and vested unlocks, potentially impacting governance control over user rights via committee elections."

## Section 2.1: Mint and Redeem V2

- **Add**: After "    *   **Type:** UUPS Proxy with SingleAdminAccessControl.", add: "    *   **Capabilities:** Includes a `disableMintRedeem` function (Gatekeeper role), allowing the protocol to technically override the legal redemption commitment during emergencies."

## Section 2.1: Reserve Fund - Remove Type

- **Modify**: Change "*   **Reserve Fund:**
    *   **Address:** `0x2b5ab59163a6e93b4486f6055d33ca4a115dd4d5`
    *   **Deployment:** January 11, 2024.
    *   **Type:** Gnosis Safe Proxy." to "*   **Reserve Fund:**
    *   **Address:** `0x2b5ab59163a6e93b4486f6055d33ca4a115dd4d5`
    *   **Deployment:** January 11, 2024.
    *   **Type:** Gnosis Safe Proxy."

## Section 2.2: New Corporate Structure Section

- **Add**: After "### 2.1. Core Contract Maturity" section ends and before "### 2.2. Multi-Chain Deployment Strategy", insert a new section:

"### 2.2. Corporate Structure and Jurisdiction
Understanding the contract deployment requires mapping the corporate entities that control them, as this dictates the legal recourse for users.

*   **Issuer:** Ethena BVI Limited (British Virgin Islands).
    *   *Role:* Primary issuer per Terms of Service. Holds legal title to reserves.
    *   *Registry Status:* Registered under no. 2127704 (Incorporated July 7, 2023).
*   **Development:** Ethena Labs SA (Portugal).
    *   *Role:* Development and technical operations.
    *   *Registry Status:* NIPC 517591111 (Incorporated May 24, 2023).
*   **Governance:** Ethena Foundation.
    *   *Role:* Non-profit entity for governance support.
*   **Risk:** The multi-jurisdictional structure (BVI/Portugal) creates opacity regarding liability and asset segregation enforceability. There are no confirmed filings detailing the credit separation between these entities, raising concerns about liability cross-contamination in an insolvency event."

## Section Headers - Renumber after Corporate Structure insertion

- **Modify**: Change "### 2.2. Multi-Chain Deployment Strategy" to "### 2.3. Multi-Chain Deployment Strategy"
- **Modify**: Change "### 2.3. Contract Upgrade History" to "### 2.4. Contract Upgrade History"

## Section 3.1: Delta-Neutral Strategy - Funding Rates Risk

- **Modify**: Change "    *   *Risk:* Negative funding rates require the protocol to pay out, depleting the Reserve Fund." to "    *   *Risk:* Negative funding rates require the protocol to pay out, depleting the Reserve Fund. Chaos Labs modeling (Jan 2024 - July 2025) suggests resilience, but historical funding data (2021-2022) used for modeling relies on unverified volume-weighted methodologies."

## Section 3.2: Heading Change

- **Modify**: Change "### 3.2. Collateral and Custody" to "### 3.2. Collateral and Custody: The Segregation Reality"

## Section 3.2: Add Disclaimer Paragraph

- **Add**: After "### 3.2. Collateral and Custody: The Segregation Reality", add: "While operational documents highlight "Off-Exchange Settlement" (OES) to mitigate exchange risk, the **legal reality for the user differs from the operational description.**"

## Section 3.2: Asset Composition - Restructure

- **Delete**: Remove "*   **Off-Exchange Settlement (OES):**
    *   Collateral is not held directly on exchanges. It is held in bankruptcy-remote trust structures.
    *   **Providers:** Copper (Primary), Ceffu, Fireblocks, Cobo, and Coinbase Web3 Wallets.
    *   **Concentration Risk:** As of September 2025, Copper and Ceffu combined held approximately 50.5% of assets, with Coinbase holding 49.1%."

- **Add**: After "*   **Asset Composition:**
    *   ~50% in Ethereum-related assets (ETH, LSTs).
    *   ~50% in Stablecoins (USDC, USDT) used for margin collateral.
    *   Introduction of Bitcoin (Q2 2024) and USDTB (Q4 2024) for diversification.", add:

"*   **Operational OES Structure:**
    *   Collateral is not held directly on exchanges but in bankruptcy-remote trust structures managed by OES providers.
    *   **Providers:** Copper (Primary), Ceffu, Fireblocks, Cobo, and Coinbase Web3 Wallets.
    *   **Concentration:** As of September 2025, Copper and Ceffu combined held approximately 50.5% of assets, with Coinbase holding 49.1%.

*   **Legal Segregation Assessment: WEAK**
    *   **No Direct Beneficiary Status:** There is no explicit evidence in the binding Terms of Service (August 2025) that USDe holders are named beneficiaries of the OES trusts.
    *   **Title Holding:** Legal title to the reserves is held by "The Company" (Ethena BVI), which administers assets. The ToS explicitly states the Company "is not a fiduciary and does not provide any trust or fiduciary services."
    *   **Bankruptcy Risk:** In the event of an Ethena BVI insolvency, reserves would likely be part of the general estate. BVI Business Companies Act Section 179 permits independent insolvency, but without specific trust deeds naming holders, users remain **unsecured creditors**.
    *   **Regulatory Findings:** The BaFin prohibition order (March 21, 2025) specifically cited "shortcomings in reserve composition and organization," further validating concerns about the legal robustness of the segregation."

## Section 4: Title Change

- **Modify**: Change "## 4. Operational Governance and Control" to "## 4. Operational Governance, Legal Framework, and User Rights"

## Section 4.3: The GATEKEEPER Role - Add Rights Implication

- **Add**: After "*   **Status:** No historical activations recorded as of October 2025.", add: "*   **Rights Implication:** The technical ability to pause the contract via this role supersedes any legal redemption commitment in the short term, placing functional control entirely in the hands of the issuer."

## Section 4.4: New Legal Framework Section

- **Add**: After "### 4.3. The GATEKEEPER Role" section ends, add a new section:

"### 4.4. Legal Framework and User Rights Assessment
A critical analysis of the Terms of Service (ToS) dated August 13, 2025, reveals a "Weak" user rights profile, characterized by significant legal disclaimers that undermine the concept of USDe as a bearer asset with inherent value.

#### 4.4.1. Tiered Redemption Rights
The protocol divides users into two distinct classes with vastly different rights:
1.  **Mint Users:**
    *   **Definition:** Entities that have completed KYC/AML verification, onboarding, and whitelisting.
    *   **Rights:** Have a conditional contractual commitment from Ethena BVI to redeem USDe for the pro rata portion of reserves.
    *   **Limitations:** Redemption is subject to "terms, applicable law, and fees."
2.  **Holding Users (The majority of the market):**
    *   **Definition:** Non-whitelisted holders (e.g., retail users, DeFi participants).
    *   **Rights:** Explicitly defined as **"not customers of Ethena BVI."**
    *   **Redemption:** Lack direct redemption rights. They must sell on secondary markets or become a Mint User to redeem.
    *   **Impact:** Approximately 40-50% of supply is estimated to be held by Holding Users who have no legal claim against the issuer.

#### 4.4.2. Discretionary Suspension and Denial
The ToS grants the issuer broad, unilateral powers:
*   **Clause:** Section 14 allows "sole discretion" to suspend, delay, or decline redemptions without notice.
*   **Grounds:** Fraud suspicion, misconduct, violations of law, or "other risks."
*   **Assessment:** This is classified as **Unreasonable** under standard consumer protection frameworks. It effectively makes the redemption promise revocable at will.
*   **Precedent:** The BaFin prohibition (March 2025) forced a suspension of the redemption window for GmbH-issued tokens from June 25 to August 6, 2025, demonstrating that these discretionary powers are actively used in response to regulatory pressure.

#### 4.4.3. Ownership and Creditor Status
*   **No Beneficial Ownership:** The ToS (Section 1) states that holding USDe "does not grant the holder any form of ownership claim... in Ethena BVI or its assets."
*   **No Economic Rights:** USDe does not represent a participation interest, economic right, voting right, or entitlement to yield/interest from reserves.
*   **Unsecured Creditor:** In the event of insolvency, USDe holders would likely stand as general unsecured creditors. They do not have priority over other claims, and the reserves are not legally ring-fenced for their exclusive benefit in the binding documents.

#### 4.4.4. Legal Evolution and Regulatory Actions
*   **BaFin Prohibition (March 21, 2025):** The German regulator classified USDe as an Asset-Referenced Token (ART) under MiCA and ordered a cessation of business, citing "shortcomings in reserve composition and organization."
*   **ToS Weakening (August 2025):** Following the regulatory actions in Europe, the ToS were updated to shift jurisdiction fully to BVI, formalize US ineligibility, and expand prohibited jurisdictions (adding Northern Cyprus). This update reinforced the "no-ownership" and "discretionary denial" clauses, effectively weakening user rights further."

## Section 5.1: Audit History - Update Intro

- **Modify**: Change "The protocol has engaged in a robust audit schedule (>11 audits)." to "The protocol has engaged in a robust audit schedule (>11 audits), though legal reviews of the user rights framework are notably absent from technical audits."

## Section 6.3: Protocol Response - Add Legal Context

- **Modify**: Change "*   **Performance:** No downtime or contract failures were observed." to "*   **Performance:** No downtime or contract failures were observed. The "Weak" legal rights of holders did not result in operational blocks during this specific event."

## Section 7.1: Bybit Hack - Add OES Validation

- **Modify**: Change "*   **Losses:** No direct loss of principal collateral, as assets were held in OES custody (Copper/Ceffu), not on Bybit." to "*   **Losses:** No direct loss of principal collateral, as assets were held in OES custody (Copper/Ceffu), not on Bybit. This validated the OES operational model."

## Section 8.1: Verified Data - Expand List

- **Modify**: Change "*   **Contract Addresses:** All mainnet and L2 addresses have been verified against block explorers.
*   **Audit Reports:** Existence and findings of Zellic, Quantstamp, and Code4rena audits are confirmed via official repositories.
*   **October Event:** The $0.65 low on Binance and the functional on-chain redemptions are corroborated by exchange data and governance posts.
*   **Reserve Balance:** The $41.89M on-chain balance is verified via Etherscan (as of Oct 26, 2025)." to "*   **Contract Addresses:** All mainnet and L2 addresses have been verified against block explorers.
*   **Legal Documents:** The August 13, 2025 Terms of Service, Mint User Agreement, and Privacy Policy are active and verified.
*   **Regulatory Actions:** The BaFin prohibition order (March 21, 2025) and subsequent winding-up orders are verified via regulatory filings.
*   **Audit Reports:** Existence and findings of Zellic, Quantstamp, and Code4rena audits are confirmed.
*   **October Event:** The $0.65 low on Binance and the functional on-chain redemptions are corroborated.
*   **Reserve Balance:** The $41.89M on-chain balance is verified via Etherscan (as of Oct 26, 2025)."

## Section 8.2: Material Data Gaps - Update and Expand

- **Modify**: Change "1.  **Reserve Fund Total Value:** There is a discrepancy between the on-chain wallet ($41.89M) and the PoR reported equity ($66M). The breakdown of the difference (likely LP positions) is not granularly documented in the latest snapshots.
2.  **Multisig Threshold:** Documentation says 7-of-10; Safe App data suggests a shift to 4-of-8. This governance change lacks a confirmed transaction hash.
3.  **Formal Verification:** There is no evidence of formal verification (mathematical proofs) for the contracts, only standard audits.
4.  **S&P Report:** The primary source for the 1,250% risk weighting (Basel III context) is unavailable; the report relies on secondary media coverage.
5.  **OES Allocation:** The exact percentage split of assets between Copper, Ceffu, and Fireblocks is not real-time transparent, obscuring specific counterparty concentration risk." to "1.  **Reserve Fund Total Value:** There is a discrepancy between the on-chain wallet ($41.89M) and the PoR reported equity ($66M). The breakdown of the difference (likely LP positions) is not granularly documented.
2.  **Historical ToS:** Full texts of pre-August 2025 Terms of Service are inaccessible, preventing a red-line comparison of exactly how rights degraded post-BaFin.
3.  **BVI Registry Data:** Due to payment walls and interactive barriers, the specific corporate filings for "Ethena BVI Limited" regarding trust deeds or SPV structures cannot be independently verified.
4.  **S&P Report:** The primary source for the 1,250% risk weighting (Basel III context) is unavailable; the report relies on secondary media coverage.
5.  **Multisig Threshold:** Documentation says 7-of-10; Safe App data suggests a shift to 4-of-8 without a confirmed transaction hash."

## Section 8.3: Red Flags - Expand

- **Modify**: Change "*   **Regulatory Risk:** The 1,250% S&P risk weighting effectively bars regulated banks from holding USDe, capping institutional adoption.
*   **Centralization:** The lack of a timelock and the reliance on off-chain keepers for hedging remain the most significant structural risks.
*   **Documentation:** Disclosures regarding the October 2025 de-peg were fragmented across social media rather than a centralized post-mortem report." to "*   **Legal/Operational Contradiction:** Whitepapers claim "bankruptcy-remote" protection, but binding ToS describe users as unsecured creditors without beneficiary status.
*   **Regulatory Risk:** The 1,250% S&P risk weighting effectively bars regulated banks from holding USDe.
*   **Centralization:** The lack of a timelock, the reliance on off-chain keepers, and the "Gatekeeper" ability to pause the contract override the theoretical decentralization.
*   **User Rights:** The "Sole Discretion" clause to suspend redemptions creates a fundamental right-to-exit risk."

## Section 9: Conclusion - Complete Rewrite

- **Delete**: Remove "Ethena (USDe) presents a mature, high-yielding stablecoin product that has successfully weathered significant market stress. The protocol's ability to process $2 billion in redemptions during the October 2025 crash without breaking peg on-chain validates the delta-neutral design and the OES custody model.

However, USDe cannot be classified as "trustless." It functions as a **CeDeFi** hybrid, heavily dependent on the performance of centralized exchanges, off-chain hedging operators, and a multisig-governed intervention model. The centralization risks are mitigated by robust audit coverage and insurance buffers but are not eliminated. Investors must weigh the attractive yield against the counterparty risks of the hedging venues and the regulatory friction restricting institutional capital integration."

- **Add**: Replace with: "Ethena (USDe) presents a mature, high-yielding stablecoin product that has successfully weathered significant market stress, most notably processing $2 billion in redemptions during the October 2025 crash without breaking peg on-chain. This validates the delta-neutral design and the operational efficacy of the OES custody model.

However, the protocol's **legal and rights framework is significantly weaker than its operational performance.** USDe cannot be classified as a bearer asset with inherent redemption rights for the average holder. It functions as a **CeDeFi** hybrid where:
1.  **Rights are Tiered:** Only whitelisted institutions have contractual standing; retail holders are explicitly "not customers."
2.  **Custody is Opaque:** While assets are physically segregated in OES accounts, holders are legally unsecured creditors of the BVI issuer, not beneficiaries of a trust.
3.  **Control is Centralized:** The combination of discretionary ToS clauses and smart contract "Gatekeeper" functions gives the issuer absolute control over liquidity.

Investors must weigh the attractive yield and proven operational resilience against the reality that they hold an unsecured claim against a BVI entity with broad discretionary powers to freeze or deny access to their funds."
