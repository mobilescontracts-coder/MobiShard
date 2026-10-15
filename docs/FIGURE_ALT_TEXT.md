# Figure descriptions for accessibility review

These descriptions do not certify PDF tagging or accessibility conformity.

## Figure 1

A participant sends a request to the edge gateway. The design-time CPN supplies
rules, not a runtime service. The gateway checks eligibility, reserves allowance,
and debits the deposit before dispatch to four workers. Workers ask the gateway
for candidates and charges and construct symbolic proofs. The root service checks
evidence and records local commitment after a delay. Root checking and commitment
share a process. Gateway state stores balances, aggregate and per-request holds,
stage status and candidate state. Denied and handled blocked requests go directly
to settlement; committed requests go there after acceptance. Settlement releases
unused holds without refunding charges or deposits, and returns status. There is
no consensus committee. This editable layout was prepared with AI assistance.

## Figure 2

Four stacked bars each represent 256 requests. Stagewise and Precheck admit all,
committing 72.40 and 72.35 on average and blocking the remainder. Reservation and
Serial commit 80 and deny 176, with no blocked admissions. Early denial is not
counted as successful completion.

## Figure 3

Completions are plotted against per-owner caps 1, 2, 4, 8 and 16. Stagewise falls
from 80 to 77.15, 75.00, 73.15 and 72.40; Precheck shows a similar decline.
Reservation and Serial remain at 80. Error bars are trial-mean 95% intervals;
cap-16 data reuse the main study. Equal counts do not establish equal runtime.
