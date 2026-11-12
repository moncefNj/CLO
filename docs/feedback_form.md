# CLO Studio: visitor feedback (ICSOC 2026 demo)

Use this sheet at the booth, on paper or as a form. It takes 5 minutes. Answers are anonymous: do not record
names or employers. Ask for consent before starting. Visitors who have used tag or cloud-governance tooling
(FinOps, security, platform or cloud engineering) answer every part; others answer only Part B.

## Part A: three tasks on the company example

Start from the page as it opens. Give no hints. For each task, note whether it was answered correctly and the
time to answer (under 1 min, 1 to 3 min, over 3 min, gave up).

| # | Task | Correct answer |
|---|---|---|
| T1 | `pay-receipts` has no `cost-center`. Which role needs it, and through which policy does that requirement reach the bucket? | FinOps; the shared labelling standard, through the account and the company (C-4) |
| T2 | Is `data-classification` missing on `vol-scratch`? | It cannot be concluded: the listing does not return tags, so the record has no verdict and is re-read |
| T3 | CLO proposes `cost-center=CC-1001` for `pay-receipts`. Why that value, and why does it propose nothing for `data-classification`? | The key declares the team's value as a source and Payments uses CC-1001 on both resources that carry the key; `data-classification` declares no value source |

## Part B: statements (1 = strongly disagree … 5 = strongly agree)

| # | Statement | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| S1 | I understood why each required key is required. | | | | | |
| S2 | I could tell a missing tag from a tag the inventory did not return. | | | | | |
| S3 | I would trust a proposed value more because the page shows its source. | | | | | |
| S4 | The explanation would change what my team does with a finding (fix, ask the owner, ignore). | | | | | |
| S5 | Writing our roles and keys in `organisation.yaml` looks feasible for my team. | | | | | |

## Part C: open questions

1. Which tool do you use today to check tags, and what does it not tell you?
2. Which explanation on the page was the most useful, and which was unclear?
3. What would stop you from running this on your own inventory?

## Reporting

Report the following, and nothing that identifies a visitor:

- the number of visitors and their background;
- the share of correct answers and the time spent on each task;
- the median score of each statement;
- the open answers grouped by theme.
