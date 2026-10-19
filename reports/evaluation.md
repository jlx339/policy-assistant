# Policy Assistant Evaluation

Run: 2026-10-18T07:12:04.080096+00:00. Corpus hash: `9fac481a920c38d74f42f59563d67dd9b55dc8928138a872cf4c23c9fdf8c642`.

Scores use the frozen 15 questions and manually reviewed chunk labels. Human judgments are separate from the runtime model checker.

## Dense results

| Metric | Value |
| --- | --- |
| queries | 15 |
| errors | 0 |
| recall_at_4 | 0.958 |
| precision_at_4 | 0.375 |
| answer_coverage | 0.800 |
| answerable_coverage | 1.000 |
| expected_status_rate | 0.933 |
| edge_status_rate | 0.667 |
| citation_id_validity | 1.000 |
| reviewed_answers | 12 |
| substantive_answers | 12 |
| supported_claims | 26 |
| total_claims | 29 |
| faithfulness | 0.897 |
| correct_answer_rate | 0.750 |
| reviewed_citation_support_rate | 0.750 |
| median_warm_seconds | 1.476 |

Targets: recall ≥0.80: True; faithfulness ≥0.95: False; median warm latency <10s: True. Errors: 0.

| Case | Expected / actual | Recall@4 | Precision@4 | Required sources present |
| --- | --- | --- | --- | --- |
| Q01 | answer / answer | 1.00 | 0.50 | True |
| Q02 | answer / answer | 1.00 | 0.25 | True |
| Q03 | answer / answer | 1.00 | 0.25 | True |
| Q04 | answer / answer | 1.00 | 0.25 | True |
| Q05 | answer / answer | 1.00 | 0.25 | True |
| Q06 | answer / answer | 1.00 | 0.25 | True |
| Q07 | answer / answer | 1.00 | 0.50 | True |
| Q08 | answer / answer | 1.00 | 0.25 | True |
| Q09 | answer / answer | 1.00 | 0.50 | True |
| Q10 | answer / answer | 1.00 | 0.75 | True |
| Q11 | answer / answer | 0.50 | 0.25 | False |
| Q12 | answer / answer | 1.00 | 0.50 | True |
| Q13 | clarify / insufficient | 0.00 | 0.00 | True |
| Q14 | insufficient / insufficient | 0.00 | 0.00 | True |
| Q15 | insufficient / insufficient | 0.00 | 0.00 | True |

### Per-question evidence and analysis

#### Q01: How old can an expense claim be before manager approval is needed for reimbursement?

Expense claims that are more than 90 days old from the purchase date will not be reimbursed unless they receive approval from the employee's manager. [c2844c845e1f0735][c22543c9ab6131bc]

Retrieved: c2844c845e1f0735, ce643b246c310be6, c22543c9ab6131bc, c1418d63d8a6da5c. Time: 1.37s. Error: none.

Review hash: `50e8ae8db0de9fc34459f21f6c95d6205a49e20b7d3aa8087dfae46e9e761fe8`.

Correct 90-day threshold and manager-approval exception; cited Guidelines passages support it.

#### Q02: What does the handbook say about knowingly expensing personal purchases that the expense policy does not cover?

Knowingly submitting expense claims for personal purchases that are not covered by the expense policy is a violation of GitLab's Code of Business Conduct & Ethics. [c2844c845e1f0735]

Retrieved: c2844c845e1f0735, ce643b246c310be6, c22543c9ab6131bc, c170d277056d31ff. Time: 1.42s. Error: none.

Review hash: `fa53e47c17e03b22887f8398bf8246db8936d485e7a8f3dd5170316406d814ea`.

Correctly identifies knowingly expensing uncovered personal purchases as a Code of Business Conduct & Ethics violation.

#### Q03: Who can help with home office expense questions or a new-hire virtual card?

For additional questions about home office expenses or using a virtual card as a new hire, contact the team via Compass or email expenses@gitlab.com. [c6159f78c3435187]

Retrieved: c6159f78c3435187, ce57173a40c887f4, c1418d63d8a6da5c, ce643b246c310be6. Time: 1.46s. Error: none.

Review hash: `0b77af3e5f5dd96697de4a2a57f4639708a922dbf176f75244b187778d2ee694`.

Compass and expenses@gitlab.com are both present in the cited equipment contact passage. The new-hire qualifier is preserved.

#### Q04: What device evidence must I provide to IT Ops before finishing onboarding?

- You must provide evidence that your device is encrypted to IT Ops before completing the onboarding period. [ca17f2d61c1584a3]

- You must provide your device’s serial number to IT Ops before completing the onboarding period. [ca17f2d61c1584a3]

Retrieved: ca17f2d61c1584a3, ccdd874a2cdfb713, ce88a501f62960ce, cda6f2af7c253ae2. Time: 1.41s. Error: none.

Review hash: `5af4d1b4df88f27c862d2cf77ad5339d72dedabc989fd2dad7c183eafc08eedf`.

Both device-encryption evidence and the serial number are required before onboarding is complete; both points are supported.

#### Q05: Are USB flash drives allowed on company-managed devices, and how can a business exception be requested?

- USB flash drives and other removable storage devices are not allowed on company‑managed devices and are blocked by default. [c46b02bc32b4b7f4]

- A business exception can be requested by opening an exception request through the provided issue tracker link, after which corporate security will coordinate to determine an appropriate encrypted device. [c46b02bc32b4b7f4]

Retrieved: c46b02bc32b4b7f4, cd246bda265f91f7, cad744e91646f0cc, cba64b866dd48aba. Time: 1.89s. Error: none.

Review hash: `bcf3fa48adf6391041a046c515fb433a4a2b55e77ea73e6506ee6e36f90b3042`.

The removable-storage passage supports the default block, business-need exception request, and Corporate Security coordination of encryption-enabled hardware.

#### Q06: May I back up company files to a file-sharing service other than the company Google Drive?

Backing up company files to a file‑sharing service other than GitLab’s Google Drive is prohibited unless an explicit exception is granted through an access request. [ca2b9f75d54524b0][cf288ec6bd8a38e1]

Retrieved: ca2b9f75d54524b0, c739799599525b66, cf288ec6bd8a38e1, c46b02bc32b4b7f4. Time: 1.84s. Error: none.

Review hash: `5b7863673fefca3d427126e6443016f40286bdcf527c6a31ec4cc0a4dbb47553`.

Failure: the answer invents an exception to the backup prohibition. The cited source prohibits backup/redundancy on other services; the access-request exception is specifically for external sharing. The continuation chunk also does not support the claimed exception.

#### Q07: I found a receipt from more than three months ago. Can I still get it paid back without asking my boss?

Expense claims that are more than 90 days old are not reimbursed unless they receive approval from your manager. [c2844c845e1f0735][c22543c9ab6131bc]

Retrieved: c2844c845e1f0735, c5ef5044ae21289d, c22543c9ab6131bc, c96e2b5aca3e7e71. Time: 1.48s. Error: none.

Review hash: `b60d8ee535d46eb811c011c4a74386389899933940ad0d30e514df204b3e87a4`.

Preserves the exact 90-day threshold and manager approval rather than converting three calendar months into a rule.

#### Q08: How can I avoid losing connectivity when my mobile carrier has no signal on a work trip?

- Maintain at least two connectivity sources, ideally from different mobile network operators, to provide redundancy when one carrier has no signal. [cf7fe83ce177b570]

- Use your smartphone with tethering enabled as one source of internet connectivity. [c37f3b16c56074e3]

- Procure a separate mobile hotspot from a different carrier as an additional connectivity source. [cf7fe83ce177b570]

- Bring an Ethernet cable and adapter to connect directly to wired internet when available, as it offers a fast and secure connection. [cf7fe83ce177b570]

- Consider purchasing a local eSIM data plan (e.g., via GigSky or Airalo) as a redundant option if your primary SIM loses service. [c0577a651a2eb93f]

Retrieved: c37f3b16c56074e3, cf7fe83ce177b570, ce6501cae218588b, c0577a651a2eb93f. Time: 1.84s. Error: none.

Review hash: `00544d23633475b95b443ad2a48cc9fe145e50d5409a7b05bcd365b37dd6d13b`.

Connectivity redundancy, different carriers, tethering, a separate hotspot, Ethernet, and local eSIM options appear in the cited travel guidance. These are travel recommendations; the answer should also preserve eSIM device compatibility.

#### Q09: What is Jamf used for on company Mac laptops?

- Jamf is used as the endpoint management solution for macOS laptops at GitLab. [ca17f2d61c1584a3]

- All macOS laptops procured by GitLab are configured with Jamf and it must be installed as part of day‑1 security tasks for team members. [c3832195b6905a63]

Retrieved: ca17f2d61c1584a3, c3832195b6905a63, cad744e91646f0cc, cda6f2af7c253ae2. Time: 1.75s. Error: none.

Review hash: `7101fb4f302a23c8942f2710698878c77e2f468a18f9e19b95922d515dcd1b95`.

Endpoint-management purpose is supported. The answer blurs preconfigured company-procured Macs with the Day-1 Jamf installation requirement for team members procuring/expensing Macs. It does not clearly preserve that distinction.

#### Q10: Where should I ask about a home office purchase, and what general deadline applies when I submit the expense claim?

- For questions about a home office purchase, you should reach out via Compass or email expenses@gitlab.com. [c6159f78c3435187]

- Expense claims must be submitted within 90 days of the purchase date, otherwise they will not be reimbursed unless approved by your manager. [c2844c845e1f0735][c22543c9ab6131bc]

Retrieved: c2844c845e1f0735, c6159f78c3435187, c22543c9ab6131bc, ce643b246c310be6. Time: 1.65s. Error: none.

Review hash: `8c115136632330b014db153895c4c9acc88dde1500e5f9dbb98f7fd4637addd0`.

Correctly combines the equipment contact route with the spending-page 90-day/manager-approval rule. Both required source pages are retrieved.

#### Q11: May I use the company laptop for personal email or a movie, and is that use exempt from security monitoring?

- Company‑provided laptops may be used for limited personal activities such as checking personal email or watching movies. [ccdd874a2cdfb713]

- All personal use of GitLab‑managed assets is subject to security monitoring and protection, unless local law specifically prohibits such monitoring. [ccdd874a2cdfb713]

Retrieved: cad744e91646f0cc, c2421a3c4afd01f4, ccdd874a2cdfb713, ca230a7d7ced1511. Time: 2.57s. Error: none.

Review hash: `1f1963da1d4f8baed29a7eb2c3c5dc6d25f73bdacd773b8a5b440be655c6ae17`.

Failure: retrieval missed the Spending Company Money permission passage and its conditions. The cited monitoring passage allows consideration of limited personal use subject to employment agreements, but does not itself establish the email/movie examples. The answer omits key permission constraints.

#### Q12: While traveling, what does the handbook advise about public WiFi, and may I use a hotel public computer to sign into company accounts?

- When traveling, avoid connecting to public Wi‑Fi networks; if you must use them, employ a personal VPN and verify the network’s authenticity. [c028fce10a4be977]

- Do not sign in to any GitLab‑related accounts on public computers, including hotel kiosks. [c2421a3c4afd01f4]

Retrieved: c028fce10a4be977, c2421a3c4afd01f4, c4dfed1100b43657, c9eecfaf260438c4. Time: 1.91s. Error: none.

Review hash: `0ddf4b730f6ee7600cca3fd8dca18ce2814e1000c012d1377888c5fb58e79542`.

Combines the public-WiFi/VPN travel guidance and the explicit public-computer sign-in prohibition; both required source pages are present.

#### Q13: Can I do that under the policy?

I couldn't find enough verified evidence in this handbook snapshot to answer that question. Try a more specific question or check the linked handbook pages.

Retrieved: c6fd6d8f803baa88, cda209a1712a21a5, cd7ac89f41bbd919, c170d277056d31ff. Time: 0.67s. Error: none.

Review hash: `0c3b90926f8f01d99a9310ab2cc43397910fc018f5333d20db991da1c90d06fa`.

Failure: the action and policy are unspecified, so the assistant should ask for clarification. Generic insufficient-evidence fallback does not resolve that ambiguity.

#### Q14: What is GitLab's stock price right now?

I couldn't find enough verified evidence in this handbook snapshot to answer that question. Try a more specific question or check the linked handbook pages.

Retrieved: c22543c9ab6131bc, ca6e9bf58cb966e3, ce4d80a82aae0dde, caa815026f9867d8. Time: 0.52s. Error: none.

Review hash: `7e100c2ea3b5566c8ba5c0b2fc818c8269b3ac5833e81c542b963b7baf6f7a88`.

Appropriate refusal: a bounded static policy snapshot cannot supply a live stock quote.

#### Q15: What is the exact home office stipend amount for a new hire in Canada?

I couldn't find enough verified evidence in this handbook snapshot to answer that question. Try a more specific question or check the linked handbook pages.

Retrieved: ce643b246c310be6, c6159f78c3435187, caa91fb56b0493f5, c9eecfaf260438c4. Time: 0.84s. Error: none.

Review hash: `170f1a9b37448a9526fb46167dfc1629c53fb6a28756329295cec47f4743b0ce`.

Appropriate refusal: the public equipment page links to internal details but does not establish an exact Canadian stipend.

## Hybrid results

| Metric | Value |
| --- | --- |
| queries | 15 |
| errors | 0 |
| recall_at_4 | 0.958 |
| precision_at_4 | 0.375 |
| answer_coverage | 0.733 |
| answerable_coverage | 0.917 |
| expected_status_rate | 0.867 |
| edge_status_rate | 0.667 |
| citation_id_validity | 1.000 |
| reviewed_answers | 11 |
| substantive_answers | 11 |
| supported_claims | 18 |
| total_claims | 22 |
| faithfulness | 0.818 |
| correct_answer_rate | 0.636 |
| reviewed_citation_support_rate | 0.727 |
| median_warm_seconds | 2.160 |

Targets: recall ≥0.80: True; faithfulness ≥0.95: False; median warm latency <10s: True. Errors: 0.

| Case | Expected / actual | Recall@4 | Precision@4 | Required sources present |
| --- | --- | --- | --- | --- |
| Q01 | answer / answer | 1.00 | 0.50 | True |
| Q02 | answer / answer | 1.00 | 0.25 | True |
| Q03 | answer / answer | 1.00 | 0.25 | True |
| Q04 | answer / answer | 1.00 | 0.25 | True |
| Q05 | answer / answer | 1.00 | 0.25 | True |
| Q06 | answer / answer | 1.00 | 0.25 | True |
| Q07 | answer / answer | 1.00 | 0.50 | True |
| Q08 | answer / insufficient | 1.00 | 0.25 | True |
| Q09 | answer / answer | 1.00 | 0.50 | True |
| Q10 | answer / answer | 1.00 | 0.75 | True |
| Q11 | answer / answer | 0.50 | 0.25 | False |
| Q12 | answer / answer | 1.00 | 0.50 | True |
| Q13 | clarify / insufficient | 0.00 | 0.00 | True |
| Q14 | insufficient / insufficient | 0.00 | 0.00 | True |
| Q15 | insufficient / insufficient | 0.00 | 0.00 | True |

### Per-question evidence and analysis

#### Q01: How old can an expense claim be before manager approval is needed for reimbursement?

Expense claims that are more than 90 days old from the purchase date will not be reimbursed unless they receive approval from the employee's manager. [c2844c845e1f0735][c22543c9ab6131bc]

Retrieved: c2844c845e1f0735, c22543c9ab6131bc, c1418d63d8a6da5c, ce643b246c310be6. Time: 2.39s. Error: none.

Review hash: `3038ae83ced1026621072929e3f4a09541c94e756d02db3df4bfa9254aa40528`.

Correct 90-day threshold and manager-approval exception; cited Guidelines passages support it.

#### Q02: What does the handbook say about knowingly expensing personal purchases that the expense policy does not cover?

Knowingly submitting expense claims for personal purchases that are not covered by the expense policy is a violation of GitLab's Code of Business Conduct & Ethics. [c2844c845e1f0735]

Retrieved: c2844c845e1f0735, c22543c9ab6131bc, c1418d63d8a6da5c, ce643b246c310be6. Time: 2.11s. Error: none.

Review hash: `cff300fa55ffeb229a07ddde84e0a390b239d58b42e6042c69ea29018694bac0`.

Correctly identifies knowingly expensing uncovered personal purchases as a Code of Business Conduct & Ethics violation.

#### Q03: Who can help with home office expense questions or a new-hire virtual card?

For additional questions about home office expenses or using a virtual card as a new hire, contact the team via Compass or email expenses@gitlab.com. [c6159f78c3435187]

Retrieved: c6159f78c3435187, c1418d63d8a6da5c, ce643b246c310be6, ce57173a40c887f4. Time: 1.96s. Error: none.

Review hash: `c69dc7fabaeaeb06fae0e5f7da189f3e910603063700d5588f1fb2efdad51fa6`.

Compass and expenses@gitlab.com are both present in the cited equipment contact passage. The new-hire qualifier is preserved.

#### Q04: What device evidence must I provide to IT Ops before finishing onboarding?

- You must provide evidence that your device is encrypted to IT Ops before completing the onboarding period. [ca17f2d61c1584a3]

- You must provide the device serial number to IT Ops before completing the onboarding period. [ca17f2d61c1584a3]

Retrieved: ca17f2d61c1584a3, ce88a501f62960ce, c30a16bf912ad1d1, c3832195b6905a63. Time: 2.23s. Error: none.

Review hash: `09ddea16ccf1d2ed32b371495076481cb63832dc7d6474688ca82507c86ba857`.

Both device-encryption evidence and the serial number are required before onboarding is complete; both points are supported.

#### Q05: Are USB flash drives allowed on company-managed devices, and how can a business exception be requested?

- USB flash drives are not allowed on company-managed devices. [c46b02bc32b4b7f4]

- A business exception can be requested by opening an exception request at the provided USB exception issue tracker link. [c46b02bc32b4b7f4]

Retrieved: c46b02bc32b4b7f4, cad744e91646f0cc, c2421a3c4afd01f4, cd246bda265f91f7. Time: 2.33s. Error: none.

Review hash: `948b6e054db6849b54df32293f7aae8473ae83ef3e6263fd1268b3361b3450ea`.

Incomplete: correctly states the prohibition and request route but omits business-need qualification and Corporate Security coordination of an encryption-enabled device.

#### Q06: May I back up company files to a file-sharing service other than the company Google Drive?

Backing up company files to a file‑sharing service other than GitLab’s Google Drive is prohibited; an exception must be obtained before doing so. [ca2b9f75d54524b0][cf288ec6bd8a38e1]

Retrieved: ca2b9f75d54524b0, cf288ec6bd8a38e1, c46b02bc32b4b7f4, c739799599525b66. Time: 2.05s. Error: none.

Review hash: `8d40eb60b2f69e0aafe63d5b03bf5aa072d2da7a1f6b5f4891d459116274936f`.

Failure: the answer invents an exception to the backup prohibition. The cited source prohibits backup/redundancy on other services; the access-request exception is specifically for external sharing. The continuation chunk also does not support the claimed exception.

#### Q07: I found a receipt from more than three months ago. Can I still get it paid back without asking my boss?

Expense claims that are more than 90 days old are not reimbursed unless the employee’s manager approves the claim. [c2844c845e1f0735][c22543c9ab6131bc]

Retrieved: c2844c845e1f0735, c5ef5044ae21289d, c22543c9ab6131bc, ce9a5bec114e218f. Time: 2.37s. Error: none.

Review hash: `8b1d52e9d3107b2d80cc3d5072dd7f49e7bdc5c417a854a5dbe5599296b1c883`.

Preserves the exact 90-day threshold and manager approval rather than converting three calendar months into a rule.

#### Q08: How can I avoid losing connectivity when my mobile carrier has no signal on a work trip?

I couldn't find enough verified evidence in this handbook snapshot to answer that question. Try a more specific question or check the linked handbook pages.

Retrieved: cf7fe83ce177b570, c37f3b16c56074e3, cd9bf2f7fa437158, c028fce10a4be977. Time: 2.81s. Error: verification_failed.

Review hash: `d189f750757ca8865a74a1c1790272008bd38036ee1a817b4e1d881fac69b710`.

Failure: relevant redundancy evidence was retrieved, but the runtime verifier rejected the generated answer. The run did not retain the per-case generation/verifier trace, so the precise rejected claim or malformed verdict cannot be reconstructed from this artifact. Do not assume retrieval failure.

#### Q09: What is Jamf used for on company Mac laptops?

Jamf is used as the endpoint management solution for macOS laptops, and all Mac laptops procured by GitLab are configured with Jamf as part of the day‑1 security tasks. [c3832195b6905a63][ca17f2d61c1584a3]

Retrieved: c3832195b6905a63, ca17f2d61c1584a3, cad744e91646f0cc, c46b02bc32b4b7f4. Time: 2.54s. Error: none.

Review hash: `1e79fa7d651ca6d3d9ea8316cbbce4cbc35f78c3452b0f0e061df557ee715b7c`.

Endpoint-management purpose is supported. The answer blurs preconfigured company-procured Macs with the Day-1 Jamf installation requirement for team members procuring/expensing Macs. It does not clearly preserve that distinction.

#### Q10: Where should I ask about a home office purchase, and what general deadline applies when I submit the expense claim?

- For questions about home office purchases, you should reach out via Compass or email expenses@gitlab.com. [c6159f78c3435187]

- Expense claims must be submitted within 90 days of the purchase date, otherwise they will not be reimbursed unless approved by your manager. [c2844c845e1f0735]

Retrieved: c2844c845e1f0735, c6159f78c3435187, c22543c9ab6131bc, ce57173a40c887f4. Time: 2.35s. Error: none.

Review hash: `a7e83cd6265d2b19e3f62726d058ca5ae71e604f525db221d7a09f4831822639`.

Correctly combines the equipment contact route with the spending-page 90-day/manager-approval rule. Both required source pages are retrieved.

#### Q11: May I use the company laptop for personal email or a movie, and is that use exempt from security monitoring?

- Company‑provided laptops may be used for limited personal activities such as checking personal email or watching movies, but all personal use is subject to security monitoring and protection. [ccdd874a2cdfb713]

- Forwarding confidential business emails or documents to personal external email addresses is prohibited. [ce9a5bec114e218f]

Retrieved: c2421a3c4afd01f4, cad744e91646f0cc, ccdd874a2cdfb713, ce9a5bec114e218f. Time: 2.16s. Error: none.

Review hash: `bf6d42853066229d5c104a86307eea301b4e8b4c1cec834e19cdf681533fa128`.

Failure: retrieval missed the Spending Company Money permission passage and its conditions. The cited monitoring passage allows consideration of limited personal use subject to employment agreements, but does not itself establish the email/movie examples. The answer omits key permission constraints. Additionally it omits the local-law exception to monitoring and adds an unrelated forwarding prohibition. That last prohibition is supported but does not complete the requested answer.

#### Q12: While traveling, what does the handbook advise about public WiFi, and may I use a hotel public computer to sign into company accounts?

- When traveling, avoid connecting to public Wi‑Fi networks; if you must use them, employ a personal VPN and verify the network’s authenticity. [c028fce10a4be977]

- Do not sign in to any GitLab‑related accounts on public computers such as hotel kiosks. [c2421a3c4afd01f4]

Retrieved: c028fce10a4be977, c2421a3c4afd01f4, c4dfed1100b43657, c22543c9ab6131bc. Time: 2.14s. Error: none.

Review hash: `6b037a9cc62dc3fcc1aeca1cfb6719bea07acbaecc9a87be3454ab96b600d69e`.

Combines the public-WiFi/VPN travel guidance and the explicit public-computer sign-in prohibition; both required source pages are present.

#### Q13: Can I do that under the policy?

I couldn't find enough verified evidence in this handbook snapshot to answer that question. Try a more specific question or check the linked handbook pages.

Retrieved: c7b2d57d5b454e6e, c2421a3c4afd01f4, c6fd6d8f803baa88, ce9a5bec114e218f. Time: 1.28s. Error: none.

Review hash: `00149894121abfc95674461be0373383dcb209478e12386d02620ed48ff2d10c`.

Failure: the action and policy are unspecified, so the assistant should ask for clarification. Generic insufficient-evidence fallback does not resolve that ambiguity.

#### Q14: What is GitLab's stock price right now?

I couldn't find enough verified evidence in this handbook snapshot to answer that question. Try a more specific question or check the linked handbook pages.

Retrieved: c22543c9ab6131bc, ceda9d15262472d4, ce4d80a82aae0dde, c5ef5044ae21289d. Time: 2.14s. Error: none.

Review hash: `e01e92fd20fe2857296d6bdcb85190ebc171a44e6f87e2f869b68be7b6303824`.

Appropriate refusal: a bounded static policy snapshot cannot supply a live stock quote.

#### Q15: What is the exact home office stipend amount for a new hire in Canada?

I couldn't find enough verified evidence in this handbook snapshot to answer that question. Try a more specific question or check the linked handbook pages.

Retrieved: c6159f78c3435187, c028fce10a4be977, cc295b3bc0f85518, c3dac9dacf426b21. Time: 1.27s. Error: none.

Review hash: `77dd7527a1f52a747d9e13acddb6734176de90164d3fcaa8281c4f70a0ea99de`.

Appropriate refusal: the public equipment page links to internal details but does not establish an exact Canadian stipend.

## Interpretation

Compare dense and hybrid rows on the same questions. Missed gold chunks indicate retrieval failure; present evidence with a wrong answer indicates generation or verification failure. Review extraction and chunk boundaries before blaming the generator. Record concrete causes and regressions in the human review notes.

Cold initialization seconds: 8.63. Warm-up request seconds: 2.00. Errors are retained in coverage and status metrics; latency excludes errors and must be interpreted alongside the error count.
